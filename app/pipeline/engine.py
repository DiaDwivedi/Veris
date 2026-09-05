from app.models.domain import BankRecord, MerchantRecord, ReconciliationResult, MatchStatus, RoutingReason
from app.pipeline.matcher import find_candidates
from app.pipeline.explain import explain_decision
from app import config

def _finalize_result(result: ReconciliationResult) -> ReconciliationResult:
    why, explanation = explain_decision(result)
    result.why = why
    result.explanation = explanation
    result.explanation_source = "template"
    return result

def reconcile(bank_record: BankRecord, merchant_records: list[MerchantRecord]) -> ReconciliationResult:
    """
    Main entry point for reconciling a single bank record against all merchant records.
    Applies score thresholds and hard safety gates to route to AUTO, REVIEW, or UNMATCHED.
    """
    candidates = find_candidates(bank_record, merchant_records, min_score=config.THRESHOLD_MIN_SCORE)
    
    if not candidates:
        return _finalize_result(ReconciliationResult(
            bank_record=bank_record,
            status=MatchStatus.UNMATCHED,
            audit_trail=[f"No plausible candidates found (all scores < {config.THRESHOLD_MIN_SCORE})."],
            routing_reason=RoutingReason.NO_CANDIDATE_ABOVE_FLOOR
        ))
        
    top_candidate = candidates[0]
    audit = top_candidate.matched_rules.copy()
    
    competing_candidates = candidates[1:]
    signal_scores = top_candidate.signal_scores
    
    # 3. No contradictory evidence (amount > 10% diff, date > 7 days diff)
    bank = top_candidate.bank_record
    merch = top_candidate.merchant_record
    
    amt_diff = abs(bank.amount - merch.amount)
    has_contradiction = False
    if amt_diff > (abs(bank.amount) * config.CONTRADICTION_AMOUNT_PERCENT):
        has_contradiction = True
        audit.append(f"Contradictory evidence (amount differs by > {config.CONTRADICTION_AMOUNT_PERCENT*100}%).")
        
    date_diff = abs((bank.transaction_date - merch.transaction_date).days)
    if date_diff > config.CONTRADICTION_DATE_DAYS:
        has_contradiction = True
        audit.append(f"Contradictory evidence (date differs by > {config.CONTRADICTION_DATE_DAYS} days).")
    
    if top_candidate.confidence_score >= config.THRESHOLD_AUTO and not has_contradiction:
        is_safe = True
        
        # 1. Unique highest candidate
        if len(candidates) > 1 and candidates[0].confidence_score == candidates[1].confidence_score:
            is_safe = False
            audit.append("Safety Gate Failed: Multiple candidates with the identical highest score.")
            
        # 2. Sufficient separation
        if len(candidates) > 1 and is_safe:
            separation = candidates[0].confidence_score - candidates[1].confidence_score
            if separation < config.MARGIN_SEPARATION:
                is_safe = False
                audit.append(f"Safety Gate Failed: Insufficient separation from runner-up ({separation} pts < {config.MARGIN_SEPARATION}).")
                
        if is_safe:
            audit.append("All AUTO Safety Gates Passed.")
            return _finalize_result(ReconciliationResult(
                bank_record=bank_record, 
                candidate=top_candidate, 
                status=MatchStatus.AUTO, 
                audit_trail=audit,
                competing_candidates=competing_candidates,
                signal_scores=signal_scores,
                routing_reason=RoutingReason.AUTO_THRESHOLD_MET
            ))
        else:
            audit.append("Downgraded to REVIEW due to safety gates.")
            return _finalize_result(ReconciliationResult(
                bank_record=bank_record, 
                candidate=top_candidate, 
                status=MatchStatus.REVIEW, 
                audit_trail=audit,
                competing_candidates=competing_candidates,
                signal_scores=signal_scores,
                routing_reason=RoutingReason.NEAR_TIE
            ))
            
    if top_candidate.confidence_score < config.THRESHOLD_REVIEW:
        audit.append(f"Score {top_candidate.confidence_score} < {config.THRESHOLD_REVIEW}. Routed to UNMATCHED.")
        return _finalize_result(ReconciliationResult(
            bank_record=bank_record, 
            candidate=None, 
            status=MatchStatus.UNMATCHED, 
            audit_trail=audit,
            competing_candidates=candidates, # all candidates are competing/considered, but none selected
            signal_scores={},
            routing_reason=RoutingReason.NO_CANDIDATE_ABOVE_FLOOR
        ))
        
    # Plausible candidate >= THRESHOLD_REVIEW but failed to hit AUTO (or failed safety gates)
    if has_contradiction:
        audit.append(f"Candidate >= {config.THRESHOLD_REVIEW} but contradictory evidence found. Routed to REVIEW.")
        reason = RoutingReason.CONTRADICTION
    else:
        audit.append(f"Score {top_candidate.confidence_score} < {config.THRESHOLD_AUTO}. Routed to REVIEW.")
        reason = RoutingReason.BELOW_AUTO_THRESHOLD
        
    return _finalize_result(ReconciliationResult(
        bank_record=bank_record, 
        candidate=top_candidate, 
        status=MatchStatus.REVIEW, 
        audit_trail=audit,
        competing_candidates=competing_candidates,
        signal_scores=signal_scores,
        routing_reason=reason
    ))
