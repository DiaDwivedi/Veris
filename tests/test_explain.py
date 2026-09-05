from datetime import datetime, timedelta
import pytest

from app.models.domain import BankRecord, MerchantRecord, MatchStatus
from app.pipeline.engine import reconcile
from app.pipeline.explain import explain_decision
from app import config

@pytest.fixture
def bank_record():
    return BankRecord(
        record_id="b1",
        amount=100.0,
        transaction_date=datetime(2023, 1, 10),
        description="MERCHANT A",
        reference_id="REF123"
    )

def test_auto_explanation(bank_record):
    merchant_records = [
        MerchantRecord(
            record_id="m1",
            amount=100.0,
            transaction_date=datetime(2023, 1, 10),
            description="MERCHANT A",
            reference_id="REF123"
        )
    ]
    
    result = reconcile(bank_record, merchant_records)
    assert result.status == MatchStatus.AUTO
    assert result.explanation_source == "template"
    assert result.why == "Exact reference and amount match with no safety conflicts."
    assert "automatically matched" in result.explanation
    assert "exact reference match" in result.explanation
    assert "exact amount match" in result.explanation

def test_unmatched_explanation(bank_record):
    merchant_records = [
        MerchantRecord(
            record_id="m1",
            amount=50.0,
            transaction_date=datetime(2023, 2, 10),
            description="TOTALLY DIFFERENT",
            reference_id="REF999"
        )
    ]
    
    result = reconcile(bank_record, merchant_records)
    assert result.status == MatchStatus.UNMATCHED
    assert result.explanation_source == "template"
    assert result.why == "No candidate cleared the minimum confidence floor."
    assert "None of the available candidates met the minimum required confidence score" in result.explanation

def test_review_near_tie_explanation(bank_record):
    merchant_records = [
        MerchantRecord(
            record_id="m1",
            amount=100.0,
            transaction_date=datetime(2023, 1, 10),
            description="MERCHANT A",
            reference_id="REF123"
        ),
        MerchantRecord(
            record_id="m2",
            amount=100.0,
            transaction_date=datetime(2023, 1, 10),
            description="MERCHANT A",
            reference_id="REF123"
        )
    ]
    
    result = reconcile(bank_record, merchant_records)
    assert result.status == MatchStatus.REVIEW
    assert result.why == "Two high-scoring candidates are too close to safely automate."
    assert "another candidate scored very similarly" in result.explanation
    assert "ambiguity" in result.explanation

def test_review_contradiction_explanation(bank_record):
    # Match above review threshold but with a date contradiction (> 7 days)
    # E.g. date differs by 10 days, but reference and amount match exactly.
    merchant_records = [
        MerchantRecord(
            record_id="m1",
            amount=100.0,
            transaction_date=datetime(2023, 1, 25), # 15 days later, contradiction
            description="MERCHANT A",
            reference_id="REF123"
        )
    ]
    
    result = reconcile(bank_record, merchant_records)
    assert result.status == MatchStatus.REVIEW
    assert result.why == "Strong match found, but conflicting evidence requires manual review."
    assert "contradictory evidence" in result.explanation

def test_review_below_auto_explanation():
    bank = BankRecord(
        record_id="b1",
        amount=100.0,
        transaction_date=datetime(2023, 1, 10),
        description="MERCHANT A",
        reference_id=None
    )
    # Score < 90 but > 70. 
    # Amount exact (35), date exact (15), desc match (10) => 60, not enough.
    # Wait, need score >= 70. Amount (35), Date (15), Customer ID (10), Desc (10) => 70
    bank.customer_id = "CUST1"
    merchant_records = [
        MerchantRecord(
            record_id="m1",
            amount=100.0,
            transaction_date=datetime(2023, 1, 10),
            description="MERCHANT A",
            reference_id=None,
            customer_id="CUST1"
        )
    ]
    
    result = reconcile(bank, merchant_records)
    assert result.status == MatchStatus.REVIEW
    assert result.why == "Candidate evidence is insufficient for automatic matching."
    assert "below the automatic matching threshold" in result.explanation

def test_determinism_and_no_side_effects(bank_record):
    merchant_records = [
        MerchantRecord(
            record_id="m1",
            amount=100.0,
            transaction_date=datetime(2023, 1, 10),
            description="MERCHANT A",
            reference_id="REF123"
        )
    ]
    
    # First run
    res1 = reconcile(bank_record, merchant_records)
    
    # Second run
    res2 = reconcile(bank_record, merchant_records)
    
    # Assert identical results
    assert res1.why == res2.why
    assert res1.explanation == res2.explanation
    assert res1.status == res2.status
    assert res1.candidate.confidence_score == res2.candidate.confidence_score
