import pytest
from datetime import datetime
from app.models.domain import BankRecord, MerchantRecord, TransactionSource, MatchStatus
from app.pipeline.engine import reconcile

def test_reconcile_unmatched():
    bank = BankRecord(
        record_id="B1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.BANK
    )
    merch = MerchantRecord(
        record_id="M1", amount=500.0, transaction_date=datetime(2026, 12, 1),
        description="Totally Different", source=TransactionSource.MERCHANT
    )
    
    result = reconcile(bank, [merch])
    assert result.status == MatchStatus.UNMATCHED
    assert result.candidate is None
    assert "No plausible candidates found" in result.audit_trail[0]

def test_reconcile_auto_success():
    bank = BankRecord(
        record_id="B1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon Retail", source=TransactionSource.BANK, reference_id="REF1"
    )
    merch1 = MerchantRecord(
        record_id="M1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon Retail", source=TransactionSource.MERCHANT, reference_id="REF1"
    )
    merch2 = MerchantRecord(
        record_id="M2", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Other", source=TransactionSource.MERCHANT, reference_id="OTHER"
    )
    
    result = reconcile(bank, [merch1, merch2])
    assert result.status == MatchStatus.AUTO
    assert result.candidate.merchant_record.record_id == "M1"
    assert any("All AUTO Safety Gates Passed" in a for a in result.audit_trail)

def test_reconcile_review_separation_gate():
    bank = BankRecord(
        record_id="B1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.BANK, reference_id="REF1"
    )
    # Both match well enough to hit 90+ but are close
    merch1 = MerchantRecord(
        record_id="M1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Different1", source=TransactionSource.MERCHANT, reference_id="REF1"
    )
    merch2 = MerchantRecord(
        record_id="M2", amount=100.0, transaction_date=datetime(2026, 9, 3),
        description="Different2", source=TransactionSource.MERCHANT, reference_id="REF1"
    )
    
    result = reconcile(bank, [merch1, merch2])
    assert result.status == MatchStatus.REVIEW
    assert any("Insufficient separation from runner-up" in a for a in result.audit_trail)

def test_reconcile_review_contradictory_amount():
    bank = BankRecord(
        record_id="B1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.BANK, reference_id="REF1"
    )
    # Strong score due to reference ID, but amount differs significantly
    merch = MerchantRecord(
        record_id="M1", amount=120.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.MERCHANT, reference_id="REF1"
    )
    
    result = reconcile(bank, [merch])
    assert result.status == MatchStatus.REVIEW
    assert any("Contradictory evidence (amount differs by > 10.0%)" in a for a in result.audit_trail)

def test_reconcile_unmatched_score_below_70():
    bank = BankRecord(
        record_id="B1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.BANK, reference_id=None
    )
    # Date, Amount, Description match -> score = 15+35+10 = 60 (Plausible)
    merch = MerchantRecord(
        record_id="M1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.MERCHANT, reference_id=None
    )
    
    result = reconcile(bank, [merch])
    assert result.status == MatchStatus.UNMATCHED
    assert result.candidate is None
    assert any("Score 60.0 < 70.0. Routed to UNMATCHED." in a for a in result.audit_trail)

def test_reconcile_review_contradictory_date():
    bank = BankRecord(
        record_id="B1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.BANK, reference_id="REF1"
    )
    # Strong score due to reference ID, but date differs by 8 days (> 7 days)
    merch = MerchantRecord(
        record_id="M1", amount=100.0, transaction_date=datetime(2026, 9, 11),
        description="Amazon", source=TransactionSource.MERCHANT, reference_id="REF1"
    )
    
    result = reconcile(bank, [merch])
    assert result.status == MatchStatus.REVIEW
    assert any("Contradictory evidence (date differs by > 7 days)" in a for a in result.audit_trail)

def test_reconcile_review_identical_scores():
    bank = BankRecord(
        record_id="B1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.BANK, reference_id="REF1"
    )
    # Both identical matches
    merch1 = MerchantRecord(
        record_id="M1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.MERCHANT, reference_id="REF1"
    )
    merch2 = MerchantRecord(
        record_id="M2", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.MERCHANT, reference_id="REF1"
    )
    
    result = reconcile(bank, [merch1, merch2])
    assert result.status == MatchStatus.REVIEW
    assert any("Multiple candidates with the identical highest score" in a for a in result.audit_trail)

def test_reconcile_review_clean():
    bank = BankRecord(
        record_id="B1", amount=100.0, transaction_date=datetime(2026, 9, 2),
        description="Amazon", source=TransactionSource.BANK, reference_id="REF1", customer_id="C1"
    )
    merch = MerchantRecord(
        record_id="M1", amount=105.0, transaction_date=datetime(2026, 9, 5),
        description="Amazon Web Services", source=TransactionSource.MERCHANT, reference_id="REF1", customer_id="C1"
    )
    # Ref (+50), Cust (+10), Desc substring (+10) -> Total 70.
    # Amt diff = 5 <= 10, Date diff = 3 <= 7. No contradictions.
    
    result = reconcile(bank, [merch])
    assert result.status == MatchStatus.REVIEW
    assert result.candidate.merchant_record.record_id == "M1"
    assert any("Score 70.0 < 90.0. Routed to REVIEW." in a for a in result.audit_trail)
