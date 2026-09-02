from datetime import timedelta
from app.models.domain import BankRecord, MerchantRecord
from app.pipeline.normalizer import normalize_string

def calculate_score(bank_record: BankRecord, merchant_record: MerchantRecord) -> tuple[float, list[str]]:
    """
    Calculates a deterministic confidence score (0-100) and an audit trail of matched rules
    between a BankRecord and a MerchantRecord.
    """
    score = 0.0
    matched_rules = []
    
    # 1. Reference ID
    b_ref = normalize_string(bank_record.reference_id, is_reference=True)
    m_ref = normalize_string(merchant_record.reference_id, is_reference=True)
    if b_ref and m_ref and b_ref == m_ref:
        score += 50
        matched_rules.append("Reference ID Exact Match (+50)")
        
    # 2. Amount
    if bank_record.amount == merchant_record.amount:
        score += 35
        matched_rules.append("Amount Exact Match (+35)")
    else:
        # Check within 0.5% tolerance
        diff = abs(bank_record.amount - merchant_record.amount)
        if diff <= (bank_record.amount * 0.005):
            score += 10
            matched_rules.append("Amount Within 0.5% Tolerance (+10)")
            
    # 3. Date Proximity
    date_diff = abs((bank_record.transaction_date - merchant_record.transaction_date).days)
    if date_diff == 0:
        score += 15
        matched_rules.append("Date Exact Match (+15)")
    elif date_diff <= 2:
        score += 5
        matched_rules.append(f"Date Within 2 Days (diff: {date_diff} days) (+5)")
        
    # 4. Customer ID
    b_cust = normalize_string(bank_record.customer_id, is_reference=True)
    m_cust = normalize_string(merchant_record.customer_id, is_reference=True)
    if b_cust and m_cust and b_cust == m_cust:
        score += 10
        matched_rules.append("Customer ID Match (+10)")
        
    # 5. Normalized Description
    b_desc = normalize_string(bank_record.description)
    m_desc = normalize_string(merchant_record.description)
    if b_desc and m_desc:
        if b_desc == m_desc:
            score += 10
            matched_rules.append("Normalized Description Exact Match (+10)")
        elif b_desc in m_desc or m_desc in b_desc:
            score += 10
            matched_rules.append("Normalized Description Substring Match (+10)")
            
    # Cap score at 100
    if score > 100:
        score = 100.0
        
    return score, matched_rules
