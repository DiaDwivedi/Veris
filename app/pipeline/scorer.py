from datetime import timedelta
from app.models.domain import BankRecord, MerchantRecord, SignalScore
from app.pipeline.normalizer import normalize_string
from app import config

def calculate_score(bank_record: BankRecord, merchant_record: MerchantRecord) -> tuple[float, list[str], dict[str, SignalScore]]:
    """
    Calculates a deterministic confidence score (0-100), an audit trail of matched rules,
    and structured signal scores between a BankRecord and a MerchantRecord.
    """
    score = 0.0
    matched_rules = []
    signal_scores: dict[str, SignalScore] = {}
    
    # 1. Reference ID
    b_ref = normalize_string(bank_record.reference_id, is_reference=True)
    m_ref = normalize_string(merchant_record.reference_id, is_reference=True)
    
    ref_earned = 0.0
    ref_outcome = "Reference ID Absent or Mismatched"
    if b_ref and m_ref and b_ref == m_ref:
        ref_earned = config.WEIGHT_REFERENCE_ID
        ref_outcome = f"Reference ID Exact Match (+{config.WEIGHT_REFERENCE_ID})"
        score += ref_earned
        matched_rules.append(ref_outcome)
    signal_scores["reference_id"] = SignalScore(earned=ref_earned, max=config.WEIGHT_REFERENCE_ID, outcome=ref_outcome)
        
    # 2. Amount
    amt_earned = 0.0
    amt_outcome = "Amount differs beyond tolerance"
    if bank_record.amount == merchant_record.amount:
        amt_earned = config.WEIGHT_AMOUNT_EXACT
        amt_outcome = f"Amount Exact Match (+{config.WEIGHT_AMOUNT_EXACT})"
        score += amt_earned
        matched_rules.append(amt_outcome)
    else:
        # Check within tolerance
        diff = abs(bank_record.amount - merchant_record.amount)
        if diff <= (abs(bank_record.amount) * config.TOLERANCE_AMOUNT_PERCENT):
            amt_earned = config.WEIGHT_AMOUNT_TOLERANCE
            amt_outcome = f"Amount Within {config.TOLERANCE_AMOUNT_PERCENT*100}% Tolerance (+{config.WEIGHT_AMOUNT_TOLERANCE})"
            score += amt_earned
            matched_rules.append(amt_outcome)
    signal_scores["amount"] = SignalScore(earned=amt_earned, max=config.WEIGHT_AMOUNT_EXACT, outcome=amt_outcome)
            
    # 3. Date Proximity
    date_earned = 0.0
    date_outcome = "Date differs beyond tolerance"
    date_diff = abs((bank_record.transaction_date - merchant_record.transaction_date).days)
    if date_diff == 0:
        date_earned = config.WEIGHT_DATE_EXACT
        date_outcome = f"Date Exact Match (+{config.WEIGHT_DATE_EXACT})"
        score += date_earned
        matched_rules.append(date_outcome)
    elif date_diff <= config.TOLERANCE_DATE_DAYS:
        date_earned = config.WEIGHT_DATE_PROXIMITY
        date_outcome = f"Date Within {config.TOLERANCE_DATE_DAYS} Days (diff: {date_diff} days) (+{config.WEIGHT_DATE_PROXIMITY})"
        score += date_earned
        matched_rules.append(date_outcome)
    signal_scores["date"] = SignalScore(earned=date_earned, max=config.WEIGHT_DATE_EXACT, outcome=date_outcome)
        
    # 4. Customer ID
    cust_earned = 0.0
    cust_outcome = "Customer ID Absent or Mismatched"
    b_cust = normalize_string(bank_record.customer_id, is_reference=True)
    m_cust = normalize_string(merchant_record.customer_id, is_reference=True)
    if b_cust and m_cust and b_cust == m_cust:
        cust_earned = config.WEIGHT_CUSTOMER_ID
        cust_outcome = f"Customer ID Match (+{config.WEIGHT_CUSTOMER_ID})"
        score += cust_earned
        matched_rules.append(cust_outcome)
    signal_scores["customer_id"] = SignalScore(earned=cust_earned, max=config.WEIGHT_CUSTOMER_ID, outcome=cust_outcome)
        
    # 5. Normalized Description
    desc_earned = 0.0
    desc_outcome = "Description Mismatched"
    b_desc = normalize_string(bank_record.description)
    m_desc = normalize_string(merchant_record.description)
    if b_desc and m_desc:
        if b_desc == m_desc:
            desc_earned = config.WEIGHT_DESC_MATCH
            desc_outcome = f"Normalized Description Exact Match (+{config.WEIGHT_DESC_MATCH})"
            score += desc_earned
            matched_rules.append(desc_outcome)
        elif b_desc in m_desc or m_desc in b_desc:
            desc_earned = config.WEIGHT_DESC_MATCH
            desc_outcome = f"Normalized Description Substring Match (+{config.WEIGHT_DESC_MATCH})"
            score += desc_earned
            matched_rules.append(desc_outcome)
    signal_scores["description"] = SignalScore(earned=desc_earned, max=config.WEIGHT_DESC_MATCH, outcome=desc_outcome)
            
    # Cap score at 100
    if score > 100:
        score = 100.0
        
    return score, matched_rules, signal_scores
