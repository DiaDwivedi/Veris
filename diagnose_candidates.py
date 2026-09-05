import csv
import json
import statistics
from app.pipeline.engine import reconcile
from app.pipeline.evaluate import load_transactions, load_orders

def run_diagnostics():
    txns = load_transactions('data/dev_transactions.csv')
    orders = load_orders('data/dev_orders.csv')
    
    print(f"Transaction count: {len(txns)}")
    print(f"Order count: {len(orders)}")
    
    results = []
    for t in txns:
        results.append(reconcile(t, orders))
    
    cand_counts = []
    more_than_one = 0
    multi_cand_lists = []
    
    for r in results:
        count = 0
        if r.candidate:
            count += 1
        count += len(r.competing_candidates)
        cand_counts.append(count)
        if count > 1:
            more_than_one += 1
            if len(multi_cand_lists) < 3:
                c_ids = [r.candidate.merchant_record.record_id] if r.candidate else []
                c_ids.extend([c.merchant_record.record_id for c in r.competing_candidates])
                multi_cand_lists.append((r.bank_record.record_id, c_ids))
    
    print(f"Candidate count per transaction: min={min(cand_counts)}, max={max(cand_counts)}, mean={statistics.mean(cand_counts):.2f}")
    print(f"Transactions with >1 candidate: {more_than_one}")
    
    if multi_cand_lists:
        for t_id, c_list in multi_cand_lists:
            print(f"  {t_id}: {c_list}")
    else:
        print("  None have more than one candidate.")
        
    with open('data/dev_transactions.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        print(f"\nTransactions CSV Headers: {headers}")
        
    with open('data/dev_orders.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers_ord = next(reader)
        print(f"Orders CSV Headers: {headers_ord}")
        
    if 'scenario' in headers:
        with open('data/dev_transactions.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            scenarios = {}
            for row in reader:
                s = row.get('scenario', '')
                scenarios[s] = scenarios.get(s, 0) + 1
            print(f"Scenario values: {scenarios}")
    else:
        print("No 'scenario' column in dev_transactions.csv")
        
    print("\nFirst five raw lines of data/dev_transactions.csv:")
    with open('data/dev_transactions.csv', 'r', encoding='utf-8') as f:
        for i in range(5):
            print(f.readline().strip())

if __name__ == '__main__':
    run_diagnostics()
