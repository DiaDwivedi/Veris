import os
import json
import time
import argparse
from typing import List, Dict, Any
# Load env vars manually
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val

from google import genai
from google.genai.errors import APIError
from app.pipeline.evaluate import load_transactions, load_orders, load_ground_truth
from app.pipeline.matcher import find_candidates
from collections import defaultdict
from datetime import datetime

MODEL = "models/gemini-3.5-flash-lite"
TEMPERATURE = 0
PROMPT_VERSION = "v1"

SYSTEM = """You are reconciling a bank transaction against candidate orders.

Return ONLY a valid JSON object. No markdown. No explanation.

{
  "order_id": "<ORD_xxxx or null>",
  "decision": "<AUTO|REVIEW|UNMATCHED>"
}

Definitions:
AUTO = confident single match.
REVIEW = a plausible match exists but confidence is insufficient, or multiple
candidates are plausibly correct.
UNMATCHED = no candidate is the correct match.
"""

def format_record(label: str, r: Any) -> str:
    ref = r.reference_id if r.reference_id else "ABSENT"
    # Convert date to string if it's a datetime
    d_str = r.transaction_date.strftime("%Y-%m-%d") if hasattr(r.transaction_date, 'strftime') else str(r.transaction_date)
    return f"{label}:\nID: {r.record_id}\nAmount: {r.amount}\nDate: {d_str}\nCustomer: {r.customer_id or 'ABSENT'}\nReference: {ref}\nDescription: {r.description}\n"

def call_gemini(client, prompt: str, cache_key: str, cache: dict, use_cache: bool):
    if use_cache and cache_key in cache:
        return cache[cache_key], False
    
    # 429 backoff
    retries = 3
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=SYSTEM + "\n\n" + prompt,
                config={'temperature': TEMPERATURE}
            )
            time.sleep(4.0) # Rate limiting for 15 RPM
            return response.text, False
        except Exception as e:
            if "429" in str(e) or getattr(e, 'code', None) == 429:
                if attempt < retries - 1:
                    time.sleep(10 * (attempt + 1))
                    continue
            return str(e), True
    return "Provider error after retries", True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--out", type=str, required=True)
    args = parser.parse_args()

    transactions = load_transactions('data/dev_transactions.csv')
    orders = load_orders('data/dev_orders.csv')
    ground_truth = load_ground_truth('data/dev_ground_truth.csv')

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    cache_file = 'evaluation/llm_cache.json'
    cache = {}
    if not args.no_cache and os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache = json.load(f)

    results = []
    
    parse_errors = 0
    provider_errors = 0
    
    # Metrics vars
    total_records = len(transactions)
    records_with_match = 0
    routed_auto = 0
    routed_review = 0
    routed_unmatched = 0
    correct_auto = 0
    correct_candidates_generated = 0

    print(f"Starting run. Output: {args.out}")
    for i, txn in enumerate(transactions):
        print(f"[{i+1}/{total_records}] {txn.record_id}")
        
        gt = ground_truth.get(txn.record_id)
        if not gt:
            continue
            
        true_order_id = gt['true_order_id']
        has_gt_match = (true_order_id is not None and true_order_id != "")
        if has_gt_match:
            records_with_match += 1
            
        candidates = find_candidates(txn, orders, min_score=20.0)
        candidates = candidates[:10] # limit to top 10
        candidate_ids = [c.merchant_record.record_id for c in candidates]
        was_candidate_generated = true_order_id in candidate_ids if has_gt_match else None

        prompt = format_record("Transaction", txn) + "\n"
        for idx, c in enumerate(candidates):
            prompt += format_record(f"Candidate {idx+1}", c.merchant_record) + "\n"

        cache_key = f"{txn.record_id}_{','.join(candidate_ids)}_{MODEL}_{PROMPT_VERSION}"
        
        raw_text, is_provider_error = call_gemini(client, prompt, cache_key, cache, not args.no_cache)
        
        if not is_provider_error and not args.no_cache:
            cache[cache_key] = raw_text
            with open(cache_file, 'w') as f:
                json.dump(cache, f)

        decision = "UNMATCHED"
        order_id = None
        is_parse_error = False

        if is_provider_error:
            provider_errors += 1
            is_parse_error = True
        else:
            try:
                text = raw_text.strip()
                if text.startswith("```json"):
                    text = text.split("```json")[1].split("```")[0].strip()
                elif text.startswith("```"):
                    text = text.split("```")[1].split("```")[0].strip()
                data = json.loads(text)
                
                decision = data.get("decision", "INVALID")
                order_id = data.get("order_id", None)
                
                if order_id == "null": order_id = None
                
                if decision not in ["AUTO", "REVIEW", "UNMATCHED"]:
                    is_parse_error = True
                elif order_id is not None and order_id not in candidate_ids:
                    is_parse_error = True
                    
            except Exception:
                is_parse_error = True
                
        if is_parse_error:
            parse_errors += 1

        if decision == "AUTO":
            routed_auto += 1
        elif decision == "REVIEW":
            routed_review += 1
        elif decision == "UNMATCHED":
            routed_unmatched += 1
            
        is_pair_correct = (order_id == true_order_id) if has_gt_match else (order_id is None)
        
        if has_gt_match:
            if decision in ("AUTO", "REVIEW") and was_candidate_generated:
                correct_candidates_generated += 1
            if decision == "AUTO" and is_pair_correct:
                correct_auto += 1

        results.append({
            "transaction_id": txn.record_id,
            "order_id": order_id,
            "decision": decision,
            "parse_error": is_parse_error,
            "provider_error": is_provider_error,
            "raw_response": raw_text if is_parse_error else None
        })

    auto_precision = (correct_auto / routed_auto) if routed_auto > 0 else None
    auto_match_recall = (correct_auto / records_with_match) if records_with_match > 0 else None
    candidate_recall = (correct_candidates_generated / records_with_match) if records_with_match > 0 else None
    auto_rate = (routed_auto / total_records) if total_records > 0 else 0.0
    review_rate = (routed_review / total_records) if total_records > 0 else 0.0
    unmatched_rate = (routed_unmatched / total_records) if total_records > 0 else 0.0

    out_data = {
        "metadata": {
            "model_id": MODEL,
            "temperature": TEMPERATURE,
            "prompt_version": PROMPT_VERSION,
            "transaction_count": total_records,
            "parse_failure_count": parse_errors,
            "provider_error_count": provider_errors,
            "cache_enabled": not args.no_cache
        },
        "metrics": {
            "auto_precision": auto_precision,
            "auto_match_recall": auto_match_recall,
            "candidate_recall": candidate_recall,
            "auto_rate": auto_rate,
            "review_rate": review_rate,
            "unmatched_rate": unmatched_rate
        },
        "records": results
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump(out_data, f, indent=2)

if __name__ == "__main__":
    main()
