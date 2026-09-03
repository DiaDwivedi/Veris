import pytest
from datetime import datetime, timezone
from app.models.domain import MerchantRecord, BankRecord, TransactionSource, MatchStatus, ReconciliationResult

def test_merchant_record_creation():
    record = MerchantRecord(
        record_id="tx_123",
        amount=100.50,
        transaction_date=datetime.now(timezone.utc),
        description="Stripe Payment",
        order_id="order_456"
    )
    assert record.source == TransactionSource.MERCHANT
    assert record.amount == 100.50
    assert record.order_id == "order_456"

def test_bank_record_creation():
    record = BankRecord(
        record_id="bank_001",
        amount=100.50,
        transaction_date=datetime.now(timezone.utc),
        description="STRIPE - tx_123",
    )
    assert record.source == TransactionSource.BANK
    assert record.amount == 100.50

def test_reconciliation_result():
    bank = BankRecord(
        record_id="bank_001", amount=100.0, transaction_date=datetime.now(timezone.utc), description="Test"
    )
    result = ReconciliationResult(
        bank_record=bank,
        status=MatchStatus.UNMATCHED,
        audit_trail=["No candidate found matching amount and date"]
    )
    assert result.status == MatchStatus.UNMATCHED
    assert len(result.audit_trail) == 1
