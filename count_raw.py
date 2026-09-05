import json
from app.pipeline.evaluate import load_transactions, load_orders
from app.pipeline.engine import reconcile

def main():
    txns = load_transactions('data/dev_transactions.csv')
    orders = load_orders('data/dev_orders.csv')
    
    count = 0
    for t in txns:
        r = reconcile(t, orders)
        if r.candidate:
            raw_sum = sum(s.earned for s in r.signal_scores.values())
            if raw_sum > 100:
                count += 1
                
    print(f"Records above 100 raw: {count}")

if __name__ == '__main__':
    main()
