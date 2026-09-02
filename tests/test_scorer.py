import pytest
from datetime import datetime, timedelta
from app.models.domain import BankRecord, MerchantRecord, TransactionSource
from app.pipeline.scorer import calculate_score

def create_mock_bank_record(**kwargs):
    default = {
        "record_id": "B1",
        "amount": 100.0,
        "transaction_date": datetime(2026, 9, 2),
        "description": "Amazon Retail",
        "source": TransactionSource.BANK
    }
    default.update(kwargs)
    return BankRecord(**default)

def create_mock_merchant_record(**kwargs):
    default = {
        "record_id": "M1",
        "amount": 100.0,
        "transaction_date": datetime(2026, 9, 2),
        "description": "Amazon",
        "source": TransactionSource.MERCHANT
    }
    default.update(kwargs)
    return MerchantRecord(**default)

def test_calculate_score_exact_match():
    bank = create_mock_bank_record(reference_id="REF123", customer_id="CUST1")
    merchant = create_mock_merchant_record(reference_id="REF-123", customer_id="CUST-1", description="Amazon Retail")
    
    score, rules = calculate_score(bank, merchant)
    
    assert score == 100.0  # Cap at 100 (50 ref + 30 amt + 15 date + 10 cust + 10 desc = 115)
    assert any("Reference ID Exact Match" in r for r in rules)
    assert any("Amount Exact Match" in r for r in rules)
    assert any("Date Exact Match" in r for r in rules)
    assert any("Customer ID Match" in r for r in rules)
    assert any("Normalized Description Exact Match" in r for r in rules)

def test_calculate_score_no_reference_but_others_match():
    bank = create_mock_bank_record(reference_id=None)
    merchant = create_mock_merchant_record(reference_id=None)
    
    score, rules = calculate_score(bank, merchant)
    
    # Amount (35) + Date (15) + Substring Desc (10) = 60
    assert score == 60.0
    assert not any("Reference ID" in r for r in rules)
    
def test_calculate_score_amount_tolerance():
    bank = create_mock_bank_record(amount=100.0)
    merchant = create_mock_merchant_record(amount=100.4) # within 0.5% tolerance
    
    score, rules = calculate_score(bank, merchant)
    assert any("Amount Within 0.5% Tolerance" in r for r in rules)

def test_calculate_score_date_tolerance():
    bank = create_mock_bank_record(transaction_date=datetime(2026, 9, 2))
    merchant = create_mock_merchant_record(transaction_date=datetime(2026, 9, 4))
    
    score, rules = calculate_score(bank, merchant)
    assert any("Date Within 2 Days" in r for r in rules)
    
def test_calculate_score_no_match():
    bank = create_mock_bank_record(amount=100.0, transaction_date=datetime(2026, 9, 2), description="Apple")
    merchant = create_mock_merchant_record(amount=200.0, transaction_date=datetime(2026, 9, 10), description="Banana")
    
    score, rules = calculate_score(bank, merchant)
    assert score == 0.0
    assert len(rules) == 0
