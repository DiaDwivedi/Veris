from fastapi.testclient import TestClient
from app.main import app
from app.db.session import init_db, get_db
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM overrides")
        cursor.execute("DELETE FROM reconciliation_snapshots")
        cursor.execute("DELETE FROM runs")
        conn.commit()

def test_legacy_override_ambiguity():
    payload = {
        "transactions": [{"record_id": "TXN_1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "ORD_1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    
    # Run 1
    client.post("/api/v2/reconcile/batch", json=payload)
    
    # Run 2
    client.post("/api/v2/reconcile/batch", json=payload)
    
    # Try legacy override - should fail due to ambiguity
    resp = client.post("/api/v1/overrides/approve", json={"transaction_id": "TXN_1", "candidate_id": "ORD_1"})
    assert resp.status_code == 400
    assert "Ambiguous transaction_id" in resp.json()["detail"]

def test_legacy_override_single_run_success():
    payload = {
        "transactions": [{"record_id": "TXN_2", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "ORD_2", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    
    # Run 1
    client.post("/api/v2/reconcile/batch", json=payload)
    
    resp = client.post("/api/v1/overrides/approve", json={"transaction_id": "TXN_2", "candidate_id": "ORD_2"})
    assert resp.status_code == 200
    assert resp.json()["action"] == "approve"

def test_v2_override_candidate_validation():
    payload = {
        "transactions": [{"record_id": "TXN_3", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "ORD_3", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    
    res = client.post("/api/v2/runs", json=payload)
    run_id = res.json()["run_id"]
    
    # Valid candidate
    resp = client.post(f"/api/v2/runs/{run_id}/records/TXN_3/override", json={"action": "approve", "candidate_id": "ORD_3"})
    assert resp.status_code == 200
    
    # Invalid candidate
    resp_bad = client.post(f"/api/v2/runs/{run_id}/records/TXN_3/override", json={"action": "approve", "candidate_id": "ORD_INVALID"})
    assert resp_bad.status_code == 422
    assert "Candidate integrity validation failed" in resp_bad.json()["detail"]

def test_v2_override_append_only():
    payload = {
        "transactions": [{"record_id": "TXN_4", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "ORD_4", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    
    res = client.post("/api/v2/runs", json=payload)
    run_id = res.json()["run_id"]
    
    # Approve
    client.post(f"/api/v2/runs/{run_id}/records/TXN_4/override", json={"action": "approve", "candidate_id": "ORD_4"})
    # Reject later
    client.post(f"/api/v2/runs/{run_id}/records/TXN_4/override", json={"action": "reject"})
    
    res_rec = client.get(f"/api/v2/runs/{run_id}/records/TXN_4")
    data = res_rec.json()
    assert len(data["override_history"]) == 2
    assert data["override_history"][0]["action"] == "approve"
    assert data["override_history"][1]["action"] == "reject"
