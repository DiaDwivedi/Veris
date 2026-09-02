from app.models.domain import BankRecord, MerchantRecord, MatchCandidate
from app.pipeline.scorer import calculate_score

def find_candidates(bank_record: BankRecord, merchant_records: list[MerchantRecord], min_score: float = 20.0) -> list[MatchCandidate]:
    """
    Finds all plausible candidates for a given BankRecord from a list of MerchantRecords.
    Returns a list of MatchCandidate sorted by confidence_score descending.
    """
    candidates = []
    
    for merchant in merchant_records:
        score, rules = calculate_score(bank_record, merchant)
        
        if score >= min_score:
            candidate = MatchCandidate(
                merchant_record=merchant,
                bank_record=bank_record,
                confidence_score=score,
                matched_rules=rules
            )
            candidates.append(candidate)
            
    # Sort descending by score
    candidates.sort(key=lambda x: x.confidence_score, reverse=True)
    return candidates
