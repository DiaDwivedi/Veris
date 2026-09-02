from app.models.domain import BankRecord, MerchantRecord, ReconciliationResult, MatchStatus
from app.pipeline.matcher import find_candidates

def reconcile(bank_record: BankRecord, merchant_records: list[MerchantRecord]) -> ReconciliationResult:
    """
    Main entry point for reconciling a single bank record against all merchant records.
    Applies score thresholds and hard safety gates to route to AUTO, REVIEW, or UNMATCHED.
    """
    candidates = find_candidates(bank_record, merchant_records, min_score=20.0)
    
    if not candidates:
        return ReconciliationResult(
            status=MatchStatus.UNMATCHED,
            audit_trail=["No plausible candidates found (all scores < 20)."]
        )
        
    top_candidate = candidates[0]
    audit = top_candidate.matched_rules.copy()
    
    # 3. No contradictory evidence (amount > 10% diff, date > 7 days diff)
    bank = top_candidate.bank_record
    merch = top_candidate.merchant_record
    
    amt_diff = abs(bank.amount - merch.amount)
    has_contradiction = False
    if amt_diff > (bank.amount * 0.10):
        has_contradiction = True
        audit.append("Contradictory evidence (amount differs by > 10%).")
        
    date_diff = abs((bank.transaction_date - merch.transaction_date).days)
    if date_diff > 7:
        has_contradiction = True
        audit.append("Contradictory evidence (date differs by > 7 days).")
    
    if top_candidate.confidence_score >= 90 and not has_contradiction:
        is_safe = True
        
        # 1. Unique highest candidate
        if len(candidates) > 1 and candidates[0].confidence_score == candidates[1].confidence_score:
            is_safe = False
            audit.append("Safety Gate Failed: Multiple candidates with the identical highest score.")
            
        # 2. Sufficient separation
        if len(candidates) > 1 and is_safe:
            separation = candidates[0].confidence_score - candidates[1].confidence_score
            if separation < 15:
                is_safe = False
                audit.append(f"Safety Gate Failed: Insufficient separation from runner-up ({separation} pts < 15).")
                
        if is_safe:
            audit.append("All AUTO Safety Gates Passed.")
            return ReconciliationResult(candidate=top_candidate, status=MatchStatus.AUTO, audit_trail=audit)
        else:
            audit.append("Downgraded to REVIEW due to safety gates.")
            return ReconciliationResult(candidate=top_candidate, status=MatchStatus.REVIEW, audit_trail=audit)
            
    if top_candidate.confidence_score < 70:
        audit.append(f"Score {top_candidate.confidence_score} < 70. Routed to UNMATCHED.")
        return ReconciliationResult(candidate=None, status=MatchStatus.UNMATCHED, audit_trail=audit)
        
    # Plausible candidate >= 70 but failed to hit AUTO (or failed safety gates)
    if has_contradiction:
        audit.append("Candidate >= 70 but contradictory evidence found. Routed to REVIEW.")
    else:
        audit.append(f"Score {top_candidate.confidence_score} < 90. Routed to REVIEW.")
        
    return ReconciliationResult(candidate=top_candidate, status=MatchStatus.REVIEW, audit_trail=audit)
