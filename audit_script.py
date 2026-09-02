import pandas as pd
import json

def audit():
    report = {}
    
    dev_orders = pd.read_csv("data/dev_orders.csv")
    dev_tx = pd.read_csv("data/dev_transactions.csv")
    dev_gt = pd.read_csv("data/dev_ground_truth.csv")
    
    test_orders = pd.read_csv("data/test_orders.csv")
    test_tx = pd.read_csv("data/test_transactions.csv")
    test_gt = pd.read_csv("data/test_ground_truth.csv")
    
    report['counts'] = {
        'dev': {'orders': int(len(dev_orders)), 'transactions': int(len(dev_tx)), 'gt': int(len(dev_gt))},
        'test': {'orders': int(len(test_orders)), 'transactions': int(len(test_tx)), 'gt': int(len(test_gt))}
    }
    
    report['columns'] = {
        'orders': list(dev_orders.columns),
        'transactions': list(dev_tx.columns),
        'gt': list(dev_gt.columns)
    }
    
    report['dev_scenarios'] = {k: int(v) for k, v in dev_gt['scenario'].value_counts().items()}
    report['test_scenarios'] = {k: int(v) for k, v in test_gt['scenario'].value_counts().items()}
    
    if 'decision_ground_truth' in dev_gt.columns:
        report['dev_decisions'] = {k: int(v) for k, v in dev_gt['decision_ground_truth'].value_counts().items()}
    if 'decision_ground_truth' in test_gt.columns:
        report['test_decisions'] = {k: int(v) for k, v in test_gt['decision_ground_truth'].value_counts().items()}
        
    report['dev_tx_duplicates'] = int(dev_tx.duplicated(subset=['amount', 'date']).sum())
    report['dev_order_duplicates'] = int(dev_orders.duplicated(subset=['amount', 'date']).sum())
    
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    audit()
