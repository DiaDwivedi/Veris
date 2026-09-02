from pydantic import BaseModel
from typing import List, Optional
from app.models.domain import BankRecord, MerchantRecord, ReconciliationResult

class SingleReconcileRequest(BaseModel):
    transaction: BankRecord
    orders: List[MerchantRecord]

class BatchReconcileRequest(BaseModel):
    transactions: List[BankRecord]
    orders: List[MerchantRecord]

class OverrideRecord(BaseModel):
    action: str
    timestamp: str

class WrappedReconciliationResult(BaseModel):
    deterministic_result: ReconciliationResult
    manual_override: Optional[OverrideRecord] = None

class BatchReconcileResponseV2(BaseModel):
    results: List[WrappedReconciliationResult]

class OverrideRequest(BaseModel):
    transaction_id: str
    candidate_id: Optional[str] = None
