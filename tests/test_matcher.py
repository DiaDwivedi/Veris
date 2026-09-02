import pytest
from datetime import datetime
from app.models.domain import BankRecord, MerchantRecord, TransactionSource
from app.pipeline.matcher import find_candidates

def test_find_candidates_sorts_by_score():
    bank = BankRecord(
        record_id="B1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon Retail", source=TransactionSource.BANK, reference_id="REF1"
    )
    
    merchant_high = MerchantRecord(
        record_id="M1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon Retail", source=TransactionSource.MERCHANT, reference_id="REF1"
    )
    
    merchant_low = MerchantRecord(
        record_id="M2", amount=100.4, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.MERCHANT, reference_id="OTHER"
    )
    
    candidates = find_candidates(bank, [merchant_low, merchant_high])
    
    assert len(candidates) == 2
    assert candidates[0].merchant_record.record_id == "M1"
    assert candidates[1].merchant_record.record_id == "M2"
    assert candidates[0].confidence_score > candidates[1].confidence_score

def test_find_candidates_filters_low_score():
    bank = BankRecord(
        record_id="B1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.BANK
    )
    
    merchant_none = MerchantRecord(
        record_id="M3", amount=500.0, transaction_date=datetime(2026, 12, 1),
        description="Totally Different", source=TransactionSource.MERCHANT
    )
    
    candidates = find_candidates(bank, [merchant_none])
    assert len(candidates) == 0
