from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class TransactionSource(str, Enum):
    MERCHANT = "merchant"
    BANK = "bank"

class MatchStatus(str, Enum):
    AUTO = "auto"
    REVIEW = "review"
    UNMATCHED = "unmatched"

class RoutingReason(str, Enum):
    AUTO_THRESHOLD_MET = "auto_threshold_met"
    NEAR_TIE = "near_tie"
    CONTRADICTION = "contradiction"
    BELOW_AUTO_THRESHOLD = "below_auto_threshold"
    NO_CANDIDATE_ABOVE_FLOOR = "no_candidate_above_floor"

class SignalScore(BaseModel):
    earned: float = Field(description="Score earned for this signal")
    max: float = Field(description="Maximum possible score for this signal")
    outcome: str = Field(description="Deterministic outcome or reason for this signal score")

class TransactionRecord(BaseModel):
    record_id: str
    amount: float
    currency: str = "USD"
    transaction_date: datetime
    description: str
    
    # Optional reconciliation evidence fields
    reference_id: Optional[str] = None
    customer_id: Optional[str] = None
    order_id: Optional[str] = None
    invoice_id: Optional[str] = None

class MerchantRecord(TransactionRecord):
    source: TransactionSource = TransactionSource.MERCHANT

class BankRecord(TransactionRecord):
    source: TransactionSource = TransactionSource.BANK

class MatchCandidate(BaseModel):
    merchant_record: MerchantRecord
    bank_record: BankRecord
    confidence_score: float = Field(0.0, description="Deterministic confidence score, not a probability.")
    matched_rules: list[str] = Field(default_factory=list, description="Rules that contributed to the match score.")
    signal_scores: dict[str, SignalScore] = Field(default_factory=dict, description="Deterministic per-signal score breakdown")

class ReconciliationResult(BaseModel):
    bank_record: BankRecord
    candidate: Optional[MatchCandidate] = None
    status: MatchStatus
    audit_trail: list[str] = Field(default_factory=list, description="Deterministic steps taken to reach this result.")
    
    # Optional provenance fields
    competing_candidates: list[MatchCandidate] = Field(default_factory=list, description="Ranked alternative candidates considered")
    signal_scores: dict[str, SignalScore] = Field(default_factory=dict, description="Deterministic per-signal score breakdown for the top candidate")
    routing_reason: Optional[RoutingReason] = Field(None, description="Structured reason for the routing decision")
    why: Optional[str] = Field(None, description="Concise one-line explanation of the decision")
    explanation: Optional[str] = Field(None, description="Human-readable explanation of the decision")
    explanation_source: Optional[str] = Field(None, description="Provenance of the explanation (e.g., 'template')")
