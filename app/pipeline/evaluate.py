import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from app.models.domain import BankRecord, MerchantRecord, MatchStatus
from app.pipeline.engine import reconcile
from app.pipeline.matcher import find_candidates

def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")

def load_transactions(path: str) -> list[BankRecord]:
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(BankRecord(
                record_id=row['id'],
                amount=float(row['amount']),
                transaction_date=parse_date(row['date']),
                description=row['description'],
                customer_id=row.get('customer_id') or None,
                reference_id=row.get('reference') or None
            ))
    return records

def load_orders(path: str) -> list[MerchantRecord]:
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(MerchantRecord(
                record_id=row['id'],
                amount=float(row['amount']),
                transaction_date=parse_date(row['date']),
                description=row['description'],
                customer_id=row.get('customer_id') or None,
                reference_id=row.get('reference') or None
            ))
    return records

def load_ground_truth(path: str) -> dict:
    gt = {}
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            gt[row['transaction_id']] = {
                'true_order_id': row['true_order_id'].strip() if row['true_order_id'] else None,
                'scenario': row['scenario'],
                'decision_ground_truth': row['decision_ground_truth']
            }
    return gt

def evaluate():
    print("Loading data...")
    transactions = load_transactions('data/dev_transactions.csv')
    orders = load_orders('data/dev_orders.csv')
    ground_truth = load_ground_truth('data/dev_ground_truth.csv')
    
    total_records = len(transactions)
    records_with_match = 0
    
    # Metrics
    routed_auto = 0
    routed_review = 0
    routed_unmatched = 0
    
    correct_auto = 0
    correct_candidates_generated = 0
    
    scenario_stats = defaultdict(lambda: {
        'total': 0, 'with_match': 0,
        'routed_auto': 0, 'correct_auto': 0, 'correct_candidates_generated': 0
    })
    
    # To store detailed evaluation per transaction
    eval_details = []
    
    print(f"Evaluating {total_records} transactions...")
    for txn in transactions:
        gt = ground_truth.get(txn.record_id)
        if not gt:
            continue
            
        true_order_id = gt['true_order_id']
        scenario = gt['scenario']
        gt_status = gt['decision_ground_truth']
        
        has_gt_match = (true_order_id is not None and true_order_id != "")
        if has_gt_match:
            records_with_match += 1
            scenario_stats[scenario]['with_match'] += 1
            
        scenario_stats[scenario]['total'] += 1
            
        # Get raw candidates and final routing result
        candidates = find_candidates(txn, orders, min_score=20.0)
        result = reconcile(txn, orders)
        
        pred_status = result.status
        
        if pred_status == MatchStatus.AUTO:
            routed_auto += 1
            scenario_stats[scenario]['routed_auto'] += 1
        elif pred_status == MatchStatus.REVIEW:
            routed_review += 1
        else:
            routed_unmatched += 1
            
        # Pair correctness and Decision correctness logic
        candidate_ids = [c.merchant_record.record_id for c in candidates]
        was_candidate_generated = true_order_id in candidate_ids if has_gt_match else None
        
        selected_candidate_id = result.candidate.merchant_record.record_id if result.candidate else None
        
        # Pair correctness: did the proposed order match true_order_id?
        is_pair_correct = (selected_candidate_id == true_order_id) if has_gt_match else (selected_candidate_id is None)
        
        # Decision correctness: did AUTO/REVIEW/UNMATCHED match decision_ground_truth?
        is_decision_correct = (pred_status.value == gt_status)
        
        if has_gt_match:
            if pred_status in (MatchStatus.AUTO, MatchStatus.REVIEW) and was_candidate_generated:
                correct_candidates_generated += 1
                scenario_stats[scenario]['correct_candidates_generated'] += 1
                
            if pred_status == MatchStatus.AUTO:
                if is_pair_correct:
                    correct_auto += 1
                    scenario_stats[scenario]['correct_auto'] += 1

        eval_details.append({
            "transaction_id": txn.record_id,
            "scenario": scenario,
            "true_order_id": true_order_id,
            "predicted_order_id": selected_candidate_id,
            "true_decision": gt_status,
            "predicted_decision": pred_status.value,
            "is_pair_correct": is_pair_correct,
            "is_decision_correct": is_decision_correct,
            "was_candidate_generated": was_candidate_generated,
            "routing_reason": result.routing_reason.value if result.routing_reason else None,
            "why": result.why,
            "explanation": result.explanation
        })
                
    # Calculate Final Metrics
    auto_precision = (correct_auto / routed_auto) if routed_auto > 0 else None
    auto_match_recall = (correct_auto / records_with_match) if records_with_match > 0 else None
    candidate_recall = (correct_candidates_generated / records_with_match) if records_with_match > 0 else None
    
    auto_rate = (routed_auto / total_records) if total_records > 0 else 0.0
    review_rate = (routed_review / total_records) if total_records > 0 else 0.0
    unmatched_rate = (routed_unmatched / total_records) if total_records > 0 else 0.0
    
    print("\n" + "="*50)
    print("MATCHING ENGINE EVALUATION RESULTS")
    print("="*50)
    
    if auto_precision is not None:
        print(f"\n1. AUTO Precision: {auto_precision*100:.1f}% ({correct_auto} of {routed_auto} correct)")
    else:
        print("\n1. AUTO Precision: N/A")
        
    print(f"2. Overall Candidate Recall: {(candidate_recall or 0.0)*100:.1f}%")
    print(f"3. AUTO-match Recall: {(auto_match_recall or 0.0)*100:.1f}%")
    print(f"4. AUTO Rate: {auto_rate*100:.1f}%")
    print(f"5. REVIEW Rate: {review_rate*100:.1f}%")
    print(f"6. UNMATCHED Rate: {unmatched_rate*100:.1f}%")
        
    # Write JSON Artifact
    os.makedirs("evaluation/results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact_path = f"evaluation/results/evaluation_run_{timestamp}.json"
    
    artifact = {
        "metadata": {
            "split": "dev",
            "timestamp": datetime.now().isoformat(),
            "dataset_size": total_records,
            "records_with_match": records_with_match
        },
        "metrics": {
            "auto_precision_percentage": auto_precision * 100 if auto_precision is not None else None,
            "auto_precision_correct": correct_auto,
            "auto_precision_total": routed_auto,
            "auto_match_recall": auto_match_recall,
            "candidate_recall": candidate_recall,
            "auto_rate": auto_rate,
            "review_rate": review_rate,
            "unmatched_rate": unmatched_rate
        },
        "scenario_breakdown": dict(scenario_stats),
        "details": eval_details
    }
    
    with open(artifact_path, 'w', encoding='utf-8') as f:
        json.dump(artifact, f, indent=2)
        
    print(f"\nEvaluation completed. JSON artifact saved to {artifact_path}")
                
if __name__ == "__main__":
    evaluate()
