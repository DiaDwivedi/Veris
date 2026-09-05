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

class OverrideRecordV2(BaseModel):
    override_id: str
    action: str
    candidate_id: Optional[str] = None
    reviewer_note: Optional[str] = None
    created_at: str

class OverrideRequestV2(BaseModel):
    action: str
    candidate_id: Optional[str] = None
    reviewer_note: Optional[str] = None

class RecordDetail(BaseModel):
    transaction_id: str
    deterministic_result: ReconciliationResult
    override_history: List[OverrideRecordV2]

class RunSummary(BaseModel):
    run_id: str
    status: str
    created_at: str
    config_version: str
    batch_size: int

class RunDetailResponse(BaseModel):
    run: RunSummary
    records: List[RecordDetail]

