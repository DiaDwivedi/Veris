from fastapi import APIRouter, HTTPException
from typing import List
import logging
from app.models.api import SingleReconcileRequest, BatchReconcileRequest
from app.models.domain import ReconciliationResult
# Import engine for mocking in tests
from app.pipeline import engine

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/reconcile/single", response_model=ReconciliationResult)
def reconcile_single(request: SingleReconcileRequest):
    try:
        result = engine.reconcile(request.transaction, request.orders)
        return result
    except Exception as e:
        logger.error(f"Error in reconcile_single: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during reconciliation.")

@router.post("/reconcile/batch", response_model=List[ReconciliationResult])
def reconcile_batch(request: BatchReconcileRequest):
    try:
        results = []
        for txn in request.transactions:
            result = engine.reconcile(txn, request.orders)
            results.append(result)
        return results
    except Exception as e:
        logger.error(f"Error in reconcile_batch: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during reconciliation.")

from app.models.api import BatchReconcileResponseV2, WrappedReconciliationResult, OverrideRecord
from app.db.session import get_db
import json
from datetime import datetime, timezone

router_v2 = APIRouter()

@router_v2.post("/reconcile/batch", response_model=BatchReconcileResponseV2)
def reconcile_batch_v2(request: BatchReconcileRequest):
    try:
        wrapped_results = []
        
        # 1. Run deterministic engine
        for txn in request.transactions:
            result = engine.reconcile(txn, request.orders)
            
            wrapped = WrappedReconciliationResult(
                deterministic_result=result,
                manual_override=None
            )
            wrapped_results.append((txn.record_id, wrapped))
            
        # 2. Persist snapshots and fetch overrides
        with get_db() as conn:
            cursor = conn.cursor()
            now_str = datetime.now(timezone.utc).isoformat()
            
            final_results = []
            for txn_id, wrapped in wrapped_results:
                # Upsert snapshot (SQLite syntax)
                snapshot_json = wrapped.deterministic_result.model_dump_json()
                cursor.execute("""
                    INSERT INTO reconciliation_snapshots (transaction_id, deterministic_result_json, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(transaction_id) DO UPDATE SET 
                        deterministic_result_json=excluded.deterministic_result_json,
                        created_at=excluded.created_at
                """, (txn_id, snapshot_json, now_str))
                
                # Fetch overrides
                cursor.execute("SELECT action, timestamp, candidate_id FROM overrides WHERE transaction_id = ?", (txn_id,))
                row = cursor.fetchone()
                if row:
                    current_candidate_id = None
                    if wrapped.deterministic_result.candidate and wrapped.deterministic_result.candidate.merchant_record:
                        current_candidate_id = wrapped.deterministic_result.candidate.merchant_record.record_id
                        
                    if current_candidate_id and row["candidate_id"] == current_candidate_id:
                        wrapped.manual_override = OverrideRecord(action=row["action"], timestamp=row["timestamp"])
                    
                final_results.append(wrapped)
                
            conn.commit()
            
        return BatchReconcileResponseV2(results=final_results)
    except Exception as e:
        logger.error(f"Error in reconcile_batch_v2: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during reconciliation.")
