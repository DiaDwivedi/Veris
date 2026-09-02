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
        conn.commit()

def test_v2_batch_persists_snapshot():
    # Submit batch to v2
    payload = {
        "transactions": [{
            "record_id": "TXN_OVERRIDE_TEST",
            "reference_id": "REF1",
            "amount": 100.0,
            "currency": "USD",
            "transaction_date": "2026-09-02T00:00:00Z",
            "description": "Override Test",
            "source": "bank"
        }],
        "orders": [{
            "record_id": "ORD_OVERRIDE_TEST",
            "reference_id": "REF1",
            "amount": 100.0,
            "currency": "USD",
            "transaction_date": "2026-09-02T00:00:00Z",
            "description": "Override Test",
            "source": "merchant"
        }]
    }
    
    response = client.post("/api/v2/reconcile/batch", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["manual_override"] is None
    
    # Verify snapshot in DB
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT deterministic_result_json FROM reconciliation_snapshots WHERE transaction_id = 'TXN_OVERRIDE_TEST'")
        row = cursor.fetchone()
        assert row is not None

def test_approve_override_success_and_idempotency():
    # 1. Generate snapshot via v2
    payload = {
        "transactions": [{
            "record_id": "TXN_APPROVE",
            "reference_id": "REF1",
            "amount": 100.0,
            "transaction_date": "2026-09-02T00:00:00Z",
            "description": "Test",
            "source": "bank"
        }],
        "orders": [{
            "record_id": "ORD_APPROVE",
            "reference_id": "REF1",
            "amount": 100.0,
            "transaction_date": "2026-09-02T00:00:00Z",
            "description": "Test",
            "source": "merchant"
        }]
    }
    client.post("/api/v2/reconcile/batch", json=payload)
    
    # 2. Submit approve
    override_payload = {
        "transaction_id": "TXN_APPROVE",
        "candidate_id": "ORD_APPROVE"
    }
    resp = client.post("/api/v1/overrides/approve", json=override_payload)
    assert resp.status_code == 200
    assert resp.json()["action"] == "approve"
    
    # 3. Test idempotency
    resp2 = client.post("/api/v1/overrides/approve", json=override_payload)
    assert resp2.status_code == 200
    assert resp2.json()["action"] == "approve"
    
    # 4. Check v2 response has override attached
    v2_resp = client.post("/api/v2/reconcile/batch", json=payload)
    data = v2_resp.json()
    assert data["results"][0]["manual_override"]["action"] == "approve"

def test_conflicting_override_returns_409():
    payload = {
        "transactions": [{"record_id": "TXN_CONFLICT", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "ORD_CONFLICT", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    client.post("/api/v2/reconcile/batch", json=payload)
    
    override_payload = {"transaction_id": "TXN_CONFLICT", "candidate_id": "ORD_CONFLICT"}
    client.post("/api/v1/overrides/approve", json=override_payload)
    
    # Attempt reject
    resp = client.post("/api/v1/overrides/reject", json=override_payload)
    assert resp.status_code == 409

def test_stale_candidate_returns_409():
    payload = {
        "transactions": [{"record_id": "TXN_STALE", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "ORD_STALE", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    client.post("/api/v2/reconcile/batch", json=payload)
    
    # Wrong candidate
    override_payload = {"transaction_id": "TXN_STALE", "candidate_id": "ORD_WRONG"}
    resp = client.post("/api/v1/overrides/approve", json=override_payload)
    assert resp.status_code == 409

def test_override_without_candidate_returns_422():
    # amount mismatch so no candidate is generated
    payload = {
        "transactions": [{"record_id": "TXN_NO_CAND", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "ORD_NO_CAND", "amount": 999.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    client.post("/api/v2/reconcile/batch", json=payload)
    
    override_payload = {"transaction_id": "TXN_NO_CAND", "candidate_id": None}
    resp = client.post("/api/v1/overrides/approve", json=override_payload)
    assert resp.status_code == 422


def test_consistency_candidate_unchanged():
    # 1. Generate snapshot for CAND_A
    payload = {
        "transactions": [{"record_id": "TXN_CONSISTENCY", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "CAND_A", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    client.post("/api/v2/reconcile/batch", json=payload)
    
    # 2. Approve CAND_A
    override_payload = {"transaction_id": "TXN_CONSISTENCY", "candidate_id": "CAND_A"}
    resp_approve = client.post("/api/v1/overrides/approve", json=override_payload)
    assert resp_approve.status_code == 200
    
    # 3. Reprocess same candidate
    resp = client.post("/api/v2/reconcile/batch", json=payload)
    data = resp.json()
    assert data["results"][0]["manual_override"] is not None
    assert data["results"][0]["manual_override"]["action"] == "approve"


def test_consistency_candidate_changed():
    # 1. Generate snapshot for CAND_A
    payload_a = {
        "transactions": [{"record_id": "TXN_CONSISTENCY_CHANGE", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "CAND_A", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    client.post("/api/v2/reconcile/batch", json=payload_a)
    
    # 2. Approve CAND_A
    override_payload = {"transaction_id": "TXN_CONSISTENCY_CHANGE", "candidate_id": "CAND_A"}
    resp_approve = client.post("/api/v1/overrides/approve", json=override_payload)
    assert resp_approve.status_code == 200
    
    # 3. Reprocess with CAND_B
    payload_b = {
        "transactions": [{"record_id": "TXN_CONSISTENCY_CHANGE", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "CAND_B", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    resp = client.post("/api/v2/reconcile/batch", json=payload_b)
    data = resp.json()
    # Expected: manual_override = null because current candidate is CAND_B but override is for CAND_A
    assert data["results"][0]["manual_override"] is None
    

def test_consistency_candidate_disappears():
    # 1. Generate snapshot for CAND_A
    payload_a = {
        "transactions": [{"record_id": "TXN_CONSISTENCY_DISAPPEAR", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "CAND_A", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    client.post("/api/v2/reconcile/batch", json=payload_a)
    
    # 2. Approve CAND_A
    override_payload = {"transaction_id": "TXN_CONSISTENCY_DISAPPEAR", "candidate_id": "CAND_A"}
    resp_approve = client.post("/api/v1/overrides/approve", json=override_payload)
    assert resp_approve.status_code == 200
    
    # 3. Reprocess with no matching orders -> candidate disappears
    payload_none = {
        "transactions": [{"record_id": "TXN_CONSISTENCY_DISAPPEAR", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "CAND_NO_MATCH", "reference_id": "REF2", "amount": 999.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    resp = client.post("/api/v2/reconcile/batch", json=payload_none)
    data = resp.json()
    # Expected: manual_override = null because current candidate is null
    assert data["results"][0]["manual_override"] is None


def test_consistency_historical_persistence():
    # 1. Generate snapshot for CAND_A
    payload_a = {
        "transactions": [{"record_id": "TXN_CONSISTENCY_HIST", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "CAND_A", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    client.post("/api/v2/reconcile/batch", json=payload_a)
    
    # 2. Approve CAND_A
    override_payload = {"transaction_id": "TXN_CONSISTENCY_HIST", "candidate_id": "CAND_A"}
    resp_approve = client.post("/api/v1/overrides/approve", json=override_payload)
    assert resp_approve.status_code == 200
    
    # 3. Reprocess with CAND_B
    payload_b = {
        "transactions": [{"record_id": "TXN_CONSISTENCY_HIST", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "bank"}],
        "orders": [{"record_id": "CAND_B", "reference_id": "REF1", "amount": 100.0, "transaction_date": "2026-09-02T00:00:00Z", "description": "Test", "source": "merchant"}]
    }
    client.post("/api/v2/reconcile/batch", json=payload_b)

    # Verify that the override for CAND_A is still in the DB after candidate changed
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT action, candidate_id FROM overrides WHERE transaction_id = 'TXN_CONSISTENCY_HIST'")
        row = cursor.fetchone()
        assert row is not None
        assert row["action"] == "approve"
        assert row["candidate_id"] == "CAND_A"
