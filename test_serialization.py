import json
from app.models.domain import ReconciliationResult

def test_serialization():
    # Let's get the run we created earlier
    from app.db.session import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT deterministic_result_json FROM reconciliation_snapshots LIMIT 1")
        row = cursor.fetchone()
        if row:
            data = row[0]
            res = ReconciliationResult.model_validate_json(data)
            print(f"Candidates in DB for 1 record: 1 (top) + {len(res.competing_candidates)} (competing)")
            
if __name__ == '__main__':
    test_serialization()
