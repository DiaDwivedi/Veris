from app.models.domain import BankRecord, MerchantRecord, MatchCandidate
from app.pipeline.scorer import calculate_score
from app import config

def find_candidates(bank_record: BankRecord, merchant_records: list[MerchantRecord], min_score: float = None) -> list[MatchCandidate]:
    """
    Finds all plausible candidates for a given BankRecord from a list of MerchantRecords.
    Returns a list of MatchCandidate sorted by confidence_score descending.
    """
    if min_score is None:
        min_score = config.THRESHOLD_MIN_SCORE
        
    candidates = []
    
    for merchant in merchant_records:
        score, rules, signal_scores = calculate_score(bank_record, merchant)
        
        if score >= min_score:
            candidate = MatchCandidate(
                merchant_record=merchant,
                bank_record=bank_record,
                confidence_score=score,
                matched_rules=rules,
                signal_scores=signal_scores
            )
            candidates.append(candidate)
            
    # Sort descending by score
    candidates.sort(key=lambda x: x.confidence_score, reverse=True)
    return candidates
