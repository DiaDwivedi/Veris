import pytest
import copy
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

def get_valid_payload():
    return {
        "transaction": {
            "record_id": "TXN_1",
            "amount": 100.0,
            "currency": "USD",
            "transaction_date": "2026-09-02T00:00:00Z",
            "description": "Amazon Retail",
            "reference_id": "REF_123"
        },
        "orders": [
            {
                "record_id": "ORD_1",
                "amount": 100.0,
                "currency": "USD",
                "transaction_date": "2026-09-02T00:00:00Z",
                "description": "Amazon Retail",
                "reference_id": "REF_123"
            }
        ]
    }

def test_single_reconcile_success():
    response = client.post("/api/v1/reconcile/single", json=get_valid_payload())
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "auto"
    assert data["candidate"]["merchant_record"]["record_id"] == "ORD_1"

def test_single_reconcile_unmatched():
    payload = get_valid_payload()
    payload["orders"] = [] # No orders
    response = client.post("/api/v1/reconcile/single", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unmatched"
    assert data["candidate"] is None

def test_batch_reconcile_success():
    payload = get_valid_payload()
    batch_payload = {
        "transactions": [payload["transaction"], payload["transaction"]],
        "orders": payload["orders"]
    }
    response = client.post("/api/v1/reconcile/batch", json=batch_payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["status"] == "auto"
    assert data[1]["status"] == "auto"

def test_validation_error():
    payload = get_valid_payload()
    del payload["transaction"]["amount"]
    response = client.post("/api/v1/reconcile/single", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["loc"] == ["body", "transaction", "amount"]

def test_internal_server_error():
    # Patch the exact module and method called in endpoints.py
    with patch("app.api.endpoints.engine.reconcile", side_effect=Exception("Simulated error")):
        response = client.post("/api/v1/reconcile/single", json=get_valid_payload())
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "An unexpected error occurred during reconciliation."

def test_immutability():
    payload = get_valid_payload()
    original_payload = copy.deepcopy(payload)
    
    response = client.post("/api/v1/reconcile/single", json=payload)
    assert response.status_code == 200
    
    # Assert payload was not mutated during request processing
    assert payload == original_payload
