import json
import uuid
import httpx
from collections import defaultdict

# Need to run the FastAPI app in background, but the system says it is already running.
# Let's hit the endpoint to create a run using the dev dataset.

# First, construct the dev dataset payload
from app.pipeline.evaluate import load_transactions, load_orders
import asyncio

async def main():
    txns = load_transactions('data/dev_transactions.csv')
    orders = load_orders('data/dev_orders.csv')
    
    payload = {
        "transactions": [json.loads(t.model_dump_json()) for t in txns],
        "orders": [json.loads(o.model_dump_json()) for o in orders]
    }
    
    # 1. Post to create run
    async with httpx.AsyncClient() as client:
        # FastAPI might be on port 8000
        res = await client.post("http://127.0.0.1:8000/api/v2/runs", json=payload, timeout=60.0)
        if res.status_code != 200:
            print("Run creation failed", res.text)
            return
            
        run_id = res.json()["run_id"]
        print(f"Created run {run_id}")
        
        # 2. Get run details
        res = await client.get(f"http://127.0.0.1:8000/api/v2/runs/{run_id}")
        run_data = res.json()
        
        records = run_data["records"]
        
        auto = sum(1 for r in records if r['deterministic_result']['status'] == 'auto')
        review = sum(1 for r in records if r['deterministic_result']['status'] == 'review')
        unmatched = sum(1 for r in records if r['deterministic_result']['status'] == 'unmatched')
        print(f"TOTAL={len(records)} AUTO={auto} REVIEW={review} UNMATCHED={unmatched}")
        
        auto_record = None
        review_record = None
        unmatched_record = None
        
        for r in records:
            status = r["deterministic_result"]["status"]
            if status == "auto" and not auto_record:
                auto_record = r
            elif status == "review" and not review_record:
                review_record = r
            elif status == "unmatched" and not unmatched_record:
                unmatched_record = r
                
        print("\n--- AUTO RECORD ---")
        if auto_record:
            print(json.dumps(auto_record["deterministic_result"]["signal_scores"], indent=2))
            
        print("\n--- REVIEW RECORD ---")
        if review_record:
            print(json.dumps(review_record["deterministic_result"]["signal_scores"], indent=2))
            
        print("\n--- UNMATCHED RECORD ---")
        if unmatched_record:
            print(json.dumps(unmatched_record["deterministic_result"]["signal_scores"], indent=2))
            
        # Let's also print the exact structure of a signal_score to see if the mapping is correct
        
if __name__ == "__main__":
    asyncio.run(main())
