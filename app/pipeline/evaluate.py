import csv
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
    
    # Confusion Matrix: {pred_status: {gt_status: count}}
    confusion = {
        MatchStatus.AUTO: defaultdict(int),
        MatchStatus.REVIEW: defaultdict(int),
        MatchStatus.UNMATCHED: defaultdict(int),
    }
    
    scenario_stats = defaultdict(lambda: {
        'total': 0, 'with_match': 0,
        'routed_auto': 0, 'correct_auto': 0, 'correct_candidates_generated': 0
    })
    
    incorrect_autos = []
    incorrect_reviews = []
    expected_unmatched = []
    
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
        confusion[pred_status][gt_status] += 1
        
        if pred_status == MatchStatus.AUTO:
            routed_auto += 1
            scenario_stats[scenario]['routed_auto'] += 1
        elif pred_status == MatchStatus.REVIEW:
            routed_review += 1
        else:
            routed_unmatched += 1
            
        # Correctness logic (only applies if ground truth has a match)
        if has_gt_match:
            candidate_ids = [c.merchant_record.record_id for c in candidates]
            was_candidate_generated = true_order_id in candidate_ids
            
            selected_candidate_id = result.candidate.merchant_record.record_id if result.candidate else None
            is_selected_correct = (selected_candidate_id == true_order_id)
            
            if pred_status in (MatchStatus.AUTO, MatchStatus.REVIEW) and was_candidate_generated:
                correct_candidates_generated += 1
                scenario_stats[scenario]['correct_candidates_generated'] += 1
                
            if pred_status == MatchStatus.AUTO:
                if is_selected_correct:
                    correct_auto += 1
                    scenario_stats[scenario]['correct_auto'] += 1
                else:
                    incorrect_autos.append({
                        'txn': txn.record_id,
                        'true_id': true_order_id,
                        'pred_id': selected_candidate_id,
                        'audit': result.audit_trail
                    })
                    
            if pred_status == MatchStatus.REVIEW and not is_selected_correct:
                incorrect_reviews.append({
                    'txn': txn.record_id,
                    'true_id': true_order_id,
                    'pred_id': selected_candidate_id,
                    'audit': result.audit_trail
                })
                
            if pred_status == MatchStatus.UNMATCHED:
                expected_unmatched.append({
                    'txn': txn.record_id,
                    'true_id': true_order_id,
                    'audit': result.audit_trail
                })
                
    # Calculate Final Metrics
    auto_precision = (correct_auto / routed_auto) if routed_auto > 0 else None
    auto_match_recall = (correct_auto / records_with_match) if records_with_match > 0 else None
    candidate_recall = (correct_candidates_generated / records_with_match) if records_with_match > 0 else None
    
    auto_rate = routed_auto / total_records
    review_rate = routed_review / total_records
    unmatched_rate = routed_unmatched / total_records
    
    print("\n" + "="*50)
    print("MATCHING ENGINE EVALUATION RESULTS")
    print("="*50)
    
    print(f"\n1. AUTO Precision: {auto_precision*100:.1f}%" if auto_precision is not None else "\n1. AUTO Precision: N/A")
    print(f"2. Overall Candidate Recall: {candidate_recall*100:.1f}%")
    print(f"3. AUTO-match Recall: {auto_match_recall*100:.1f}%")
    print(f"4. AUTO Rate: {auto_rate*100:.1f}%")
    print(f"5. REVIEW Rate: {review_rate*100:.1f}%")
    print(f"6. UNMATCHED Rate: {unmatched_rate*100:.1f}%")
    
    print("\n--- Confusion Matrix (Predicted vs Ground Truth) ---")
    print(f"{'Predicted':<15} | {'GT_AUTO':<10} | {'GT_REVIEW':<10} | {'GT_UNMATCHED':<12}")
    print("-" * 55)
    for pred in [MatchStatus.AUTO, MatchStatus.REVIEW, MatchStatus.UNMATCHED]:
        c = confusion[pred]
        print(f"{pred.value.upper():<15} | {c['AUTO']:<10} | {c['REVIEW']:<10} | {c['UNMATCHED']:<12}")
        
    print("\n--- Scenario-level Performance ---")
    for sc, stats in scenario_stats.items():
        if stats['with_match'] > 0:
            rec = stats['correct_candidates_generated'] / stats['with_match']
            auto_rec = stats['correct_auto'] / stats['with_match']
        else:
            rec = 0.0
            auto_rec = 0.0
        print(f"Scenario: {sc} (Total: {stats['total']}, With Match: {stats['with_match']})")
        print(f"  Candidate Recall: {rec*100:.1f}%")
        print(f"  AUTO-match Recall: {auto_rec*100:.1f}%")
        
    if incorrect_autos:
        print(f"\n[CRITICAL] {len(incorrect_autos)} INCORRECT AUTO MATCHES FOUND:")
        for err in incorrect_autos:
            print(f"  TXN: {err['txn']} | Predicted: {err['pred_id']} | True: {err['true_id']}")
            print("  Audit Trail:")
            for a in err['audit']:
                print(f"    - {a}")
                
    if incorrect_reviews:
        print(f"\n[WARNING] {len(incorrect_reviews)} Incorrect REVIEW selections found:")
        for err in incorrect_reviews[:5]: # Show first 5
            print(f"  TXN: {err['txn']} | Predicted: {err['pred_id']} | True: {err['true_id']}")
            
    if expected_unmatched:
        print(f"\n[WARNING] {len(expected_unmatched)} Expected matches became UNMATCHED:")
        for err in expected_unmatched[:5]: # Show first 5
            print(f"  TXN: {err['txn']} | True: {err['true_id']}")
            print("  Audit Trail:")
            for a in err['audit']:
                print(f"    - {a}")
                
if __name__ == "__main__":
    evaluate()
