from app.models.domain import ReconciliationResult, RoutingReason, MatchStatus

def explain_decision(result: ReconciliationResult) -> tuple[str, str]:
    """
    Generates a deterministic (why, explanation) tuple based on the routing reason
    and signal scores.
    """
    status = result.status
    reason = result.routing_reason
    candidate = result.candidate
    scores = result.signal_scores

    if status == MatchStatus.UNMATCHED or not candidate:
        why = "No candidate cleared the minimum confidence floor."
        explanation = "None of the available candidates met the minimum required confidence score to be considered a match."
        return why, explanation

    # Extract score details for explanation
    ref_score = scores.get("reference_id")
    amt_score = scores.get("amount")
    
    strong_signals = []
    if ref_score and ref_score.earned > 0:
        if ref_score.earned == ref_score.max:
            strong_signals.append("an exact reference match")
    if amt_score and amt_score.earned > 0:
        if amt_score.earned == amt_score.max:
            strong_signals.append("an exact amount match")
        else:
            strong_signals.append("an amount match within tolerance")

    signals_text = " and ".join(strong_signals) if strong_signals else "partial evidence"

    if reason == RoutingReason.AUTO_THRESHOLD_MET:
        why = "High confidence match with no safety conflicts."
        if ref_score and amt_score and ref_score.earned == ref_score.max and amt_score.earned == amt_score.max:
            why = "Exact reference and amount match with no safety conflicts."
        
        explanation = f"This record was automatically matched because it presented {signals_text}. The overall confidence score exceeded the automatic threshold without any contradictions."
        
    elif reason == RoutingReason.NEAR_TIE:
        why = "Two high-scoring candidates are too close to safely automate."
        explanation = f"Although there is a high-scoring candidate with {signals_text}, another candidate scored very similarly. Manual review is required to resolve the ambiguity."

    elif reason == RoutingReason.CONTRADICTION:
        why = "Strong match found, but conflicting evidence requires manual review."
        explanation = f"A candidate was found with {signals_text}, but there is contradictory evidence (e.g., date or amount discrepancies) that prevents safe automation. Manual review is required."

    elif reason == RoutingReason.BELOW_AUTO_THRESHOLD:
        why = "Candidate evidence is insufficient for automatic matching."
        explanation = f"A candidate was identified with {signals_text}, but its total confidence score is below the automatic matching threshold. It requires manual review."

    else:
        # Fallback for unexpected states
        why = "Review required based on scoring."
        explanation = "The candidate score did not meet the criteria for automatic matching."

    return why, explanation
