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

class ReconciliationResult(BaseModel):
    bank_record: BankRecord
    candidate: Optional[MatchCandidate] = None
    status: MatchStatus
    audit_trail: list[str] = Field(default_factory=list, description="Deterministic steps taken to reach this result.")
