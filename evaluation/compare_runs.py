import json
import sys

def load_run(path):
    with open(path, 'r') as f:
        return json.load(f)

def main():
    if len(sys.argv) < 3:
        path_a = "evaluation/run_a.json"
        path_b = "evaluation/run_b.json"
    else:
        path_a = sys.argv[1]
        path_b = sys.argv[2]
        
    run_a = load_run(path_a)
    run_b = load_run(path_b)
    
    records_a = {r['transaction_id']: r for r in run_a['records']}
    records_b = {r['transaction_id']: r for r in run_b['records']}
    
    order_diffs = 0
    decision_diffs = 0
    total_diffs = 0
    differing_txns = []
    
    for txn_id in records_a.keys():
        ra = records_a[txn_id]
        rb = records_b.get(txn_id)
        if not rb:
            continue
            
        diff_order = ra['order_id'] != rb['order_id']
        diff_decision = ra['decision'] != rb['decision']
        
        if diff_order:
            order_diffs += 1
        if diff_decision:
            decision_diffs += 1
            
        if diff_order or diff_decision:
            total_diffs += 1
            differing_txns.append({
                'transaction_id': txn_id,
                'run_a': {'order_id': ra['order_id'], 'decision': ra['decision']},
                'run_b': {'order_id': rb['order_id'], 'decision': rb['decision']}
            })
            
    print(f"{total_diffs} of {len(records_a)} decisions differed across identical uncached runs\n")
    print(f"Order ID differences: {order_diffs}")
    print(f"Decision differences: {decision_diffs}")
    print(f"Parse failures - Run A: {run_a['metadata']['parse_failure_count']}, Run B: {run_b['metadata']['parse_failure_count']}")
    print(f"Provider errors - Run A: {run_a['metadata']['provider_error_count']}, Run B: {run_b['metadata']['provider_error_count']}")
    
    if differing_txns:
        print("\nDiffering Transactions:")
        for t in differing_txns:
            print(f"  {t['transaction_id']}:")
            print(f"    Run A: Order={t['run_a']['order_id']}, Decision={t['run_a']['decision']}")
            print(f"    Run B: Order={t['run_b']['order_id']}, Decision={t['run_b']['decision']}")

if __name__ == "__main__":
    main()
