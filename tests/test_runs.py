import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    import os
    # Ensure fresh DB for tests or let init_db handle it.
    # In tests, DB_PATH might point to a real DB, so ideally we should mock it or use an in-memory DB.
    # For now, we assume the test suite cleans up or uses a separate test DB.
    # We just run init_db to ensure schema is fresh.
    init_db()

def test_create_run_and_override():
    # 1. Create a run via POST /api/v2/runs
    batch_payload = {
        "transactions": [
            {
                "record_id": "txn_run_1",
                "amount": 100.0,
                "transaction_date": "2023-01-01T00:00:00Z",
                "description": "Test TXN"
            }
        ],
        "orders": [
            {
                "record_id": "ord_run_1",
                "amount": 100.0,
                "transaction_date": "2023-01-01T00:00:00Z",
                "description": "Test ORD"
            },
            {
                "record_id": "ord_run_2",
                "amount": 100.0,
                "transaction_date": "2023-01-01T00:00:00Z",
                "description": "Test ORD 2"
            }
        ]
    }
    
    res = client.post("/api/v2/runs", json=batch_payload)
    assert res.status_code == 200
    run_id = res.json()["run_id"]
    
    # 2. Get the run details
    res_run = client.get(f"/api/v2/runs/{run_id}")
    assert res_run.status_code == 200
    run_data = res_run.json()
    assert run_data["run"]["status"] == "completed"
    assert len(run_data["records"]) == 1
    
    # 3. Create an override (append-only)
    override_payload = {
        "action": "approve",
        "candidate_id": "ord_run_1",
        "reviewer_note": "Looks good"
    }
    res_ov = client.post(f"/api/v2/runs/{run_id}/records/txn_run_1/override", json=override_payload)
    assert res_ov.status_code == 200
    override_id = res_ov.json()["override_id"]
    
    # 4. Create another override
    override_payload2 = {
        "action": "reject",
        "reviewer_note": "Wait, no"
    }
    res_ov2 = client.post(f"/api/v2/runs/{run_id}/records/txn_run_1/override", json=override_payload2)
    assert res_ov2.status_code == 200
    
    # 5. Get record detail and verify immutability + append-only history
    res_rec = client.get(f"/api/v2/runs/{run_id}/records/txn_run_1")
    assert res_rec.status_code == 200
    rec_data = res_rec.json()
    
    # Deterministic result is untouched
    assert rec_data["deterministic_result"]["status"] == "unmatched"
    
    assert len(rec_data["override_history"]) == 2
    assert rec_data["override_history"][0]["action"] == "approve"
    assert rec_data["override_history"][0]["reviewer_note"] == "Looks good"
    assert rec_data["override_history"][1]["action"] == "reject"

def test_candidate_integrity_validation():
    batch_payload = {
        "transactions": [
            {
                "record_id": "txn_val_1",
                "amount": 100.0,
                "transaction_date": "2023-01-01T00:00:00Z",
                "description": "Test TXN"
            }
        ],
        "orders": [
            {
                "record_id": "ord_valid_1",
                "amount": 100.0,
                "transaction_date": "2023-01-01T00:00:00Z",
                "description": "Test ORD"
            }
        ]
    }
    
    res = client.post("/api/v2/runs", json=batch_payload)
    run_id = res.json()["run_id"]
    
    # Valid candidate
    res_ov = client.post(f"/api/v2/runs/{run_id}/records/txn_val_1/override", json={
        "action": "approve",
        "candidate_id": "ord_valid_1"
    })
    assert res_ov.status_code == 200
    
    # Invalid candidate (not in deterministic snapshot)
    res_ov_bad = client.post(f"/api/v2/runs/{run_id}/records/txn_val_1/override", json={
        "action": "approve",
        "candidate_id": "ord_invalid_999"
    })
    assert res_ov_bad.status_code == 422
    assert "Candidate integrity validation failed" in res_ov_bad.json()["detail"]

def test_legacy_override_ambiguity():
    txn_id = "txn_ambiguous"
    batch_payload = {
        "transactions": [
            {
                "record_id": txn_id,
                "amount": 100.0,
                "transaction_date": "2023-01-01T00:00:00Z",
                "description": "Test TXN"
            }
        ],
        "orders": [
            {
                "record_id": "ord_1",
                "amount": 100.0,
                "transaction_date": "2023-01-01T00:00:00Z",
                "description": "Test ORD"
            }
        ]
    }
    
    # First run
    res1 = client.post("/api/v2/runs", json=batch_payload)
    run1 = res1.json()["run_id"]
    
    # Second run with same transaction_id
    res2 = client.post("/api/v2/runs", json=batch_payload)
    run2 = res2.json()["run_id"]
    
    # Legacy override should fail due to ambiguity
    res_legacy = client.post("/api/v1/overrides/approve", json={
        "transaction_id": txn_id,
        "candidate_id": "ord_1"
    })
    assert res_legacy.status_code == 400
    assert "Ambiguous transaction_id" in res_legacy.json()["detail"]
    
    # But explicitly via V2 works
    res_v2 = client.post(f"/api/v2/runs/{run1}/records/{txn_id}/override", json={
        "action": "approve",
        "candidate_id": "ord_1"
    })
    assert res_v2.status_code == 200

def test_snapshot_immutability_with_multiple_overrides():
    batch_payload = {
        "transactions": [
            {
                "record_id": "txn_immutability_1",
                "amount": 250.0,
                "transaction_date": "2023-01-01T00:00:00Z",
                "description": "Test Immutability"
            }
        ],
        "orders": [
            {
                "record_id": "ord_immutability_1",
                "amount": 250.0,
                "transaction_date": "2023-01-01T00:00:00Z",
                "description": "Test Immutability"
            }
        ]
    }
    
    # 1. Create a run with an original deterministic result
    res = client.post("/api/v2/runs", json=batch_payload)
    run_id = res.json()["run_id"]
    
    # Fetch original deterministic result structure immediately after creation
    initial_res = client.get(f"/api/v2/runs/{run_id}/records/txn_immutability_1")
    assert initial_res.status_code == 200
    original_deterministic_result = initial_res.json()["deterministic_result"]
    assert len(initial_res.json()["override_history"]) == 0
    
    # 2. Add multiple overrides, including conflicting actions
    client.post(f"/api/v2/runs/{run_id}/records/txn_immutability_1/override", json={
        "action": "approve",
        "candidate_id": "ord_immutability_1",
        "reviewer_note": "Initial approval"
    })
    
    client.post(f"/api/v2/runs/{run_id}/records/txn_immutability_1/override", json={
        "action": "reject",
        "reviewer_note": "Conflicting rejection"
    })
    
    # 3. Retrieve final state
    final_res = client.get(f"/api/v2/runs/{run_id}/records/txn_immutability_1")
    assert final_res.status_code == 200
    final_data = final_res.json()
    
    # 4. The override history contains all events in order
    assert len(final_data["override_history"]) == 2
    assert final_data["override_history"][0]["action"] == "approve"
    assert final_data["override_history"][1]["action"] == "reject"
    
    # 5. The persisted original deterministic snapshot remains structurally unchanged
    # and is returned separately from the complete override history
    assert final_data["deterministic_result"] == original_deterministic_result
