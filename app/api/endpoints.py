from fastapi import APIRouter, HTTPException, Path
from typing import List, Dict, Any
import logging
import uuid
import json
import os
from datetime import datetime, timezone
from pydantic import BaseModel

from app.models.api import (
    SingleReconcileRequest, BatchReconcileRequest, BatchReconcileResponseV2,
    WrappedReconciliationResult, OverrideRecord, OverrideRecordV2,
    RunSummary, RecordDetail, RunDetailResponse
)
from app.models.domain import ReconciliationResult
from app.pipeline import engine
from app.db.session import get_db
from app.config import get_config_hash

router = APIRouter()
logger = logging.getLogger(__name__)

# --- V1 Endpoints (Preserved for backwards compatibility) ---

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

# --- V2 Endpoints ---

router_v2 = APIRouter()

def _execute_run_and_persist(request: BatchReconcileRequest) -> tuple[str, List[WrappedReconciliationResult]]:
    """Core logic to generate a run_id, run the engine, and persist immutable snapshots."""
    run_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    config_hash = get_config_hash()
    
    wrapped_results = []
    
    # 1. Run deterministic engine
    for txn in request.transactions:
        result = engine.reconcile(txn, request.orders)
        wrapped = WrappedReconciliationResult(
            deterministic_result=result,
            manual_override=None # New run, no overrides yet
        )
        wrapped_results.append((txn.record_id, wrapped))
        
    # 2. Persist Run and Snapshots
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO runs (run_id, created_at, config_version, batch_size) VALUES (?, ?, ?, ?)",
            (run_id, now_str, config_hash, len(request.transactions))
        )
        
        for txn_id, wrapped in wrapped_results:
            snapshot_json = wrapped.deterministic_result.model_dump_json()
            cursor.execute("""
                INSERT INTO reconciliation_snapshots (run_id, transaction_id, deterministic_result_json, created_at)
                VALUES (?, ?, ?, ?)
            """, (run_id, txn_id, snapshot_json, now_str))
            
        conn.commit()
        
    final_wrapped = [w for _, w in wrapped_results]
    return run_id, final_wrapped

@router_v2.post("/reconcile/batch", response_model=BatchReconcileResponseV2)
def reconcile_batch_v2(request: BatchReconcileRequest):
    """Legacy V2 batch endpoint, updated to create a run_id internally but return legacy format."""
    try:
        run_id, final_results = _execute_run_and_persist(request)
        return BatchReconcileResponseV2(results=final_results)
    except Exception as e:
        logger.error(f"Error in reconcile_batch_v2: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during reconciliation.")

@router_v2.post("/runs")
def create_run(request: BatchReconcileRequest):
    """Creates a run, processes batch, and returns run summary."""
    try:
        run_id, final_results = _execute_run_and_persist(request)
        return {
            "run_id": run_id,
            "status": "completed",
            "summary": {
                "total_processed": len(final_results)
            }
        }
    except Exception as e:
        logger.error(f"Error creating run: {e}")
        raise HTTPException(status_code=500, detail="Failed to create run.")

@router_v2.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run(run_id: str = Path(...)):
    """Returns run metadata and summarized records."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Fetch run metadata
            cursor.execute("SELECT created_at, config_version, batch_size FROM runs WHERE run_id = ?", (run_id,))
            run_row = cursor.fetchone()
            if not run_row:
                raise HTTPException(status_code=404, detail="Run not found.")
                
            run_summary = RunSummary(
                run_id=run_id,
                status="completed",
                created_at=run_row["created_at"],
                config_version=run_row["config_version"],
                batch_size=run_row["batch_size"]
            )
            
            # Fetch records and their override history
            cursor.execute("""
                SELECT transaction_id, deterministic_result_json 
                FROM reconciliation_snapshots 
                WHERE run_id = ?
            """, (run_id,))
            snapshot_rows = cursor.fetchall()
            
            records = []
            for row in snapshot_rows:
                txn_id = row["transaction_id"]
                det_result = ReconciliationResult.model_validate_json(row["deterministic_result_json"])
                
                # Fetch overrides
                cursor.execute("""
                    SELECT override_id, action, candidate_id, reviewer_note, created_at
                    FROM overrides
                    WHERE run_id = ? AND transaction_id = ?
                    ORDER BY created_at ASC
                """, (run_id, txn_id))
                ov_rows = cursor.fetchall()
                
                overrides = []
                for ov in ov_rows:
                    overrides.append(OverrideRecordV2(
                        override_id=ov["override_id"],
                        action=ov["action"],
                        candidate_id=ov["candidate_id"],
                        reviewer_note=ov["reviewer_note"],
                        created_at=ov["created_at"]
                    ))
                    
                records.append(RecordDetail(
                    transaction_id=txn_id,
                    deterministic_result=det_result,
                    override_history=overrides
                ))
                
            return RunDetailResponse(run=run_summary, records=records)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching run: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch run.")

@router_v2.get("/runs/{run_id}/records/{transaction_id}", response_model=RecordDetail)
def get_run_record(run_id: str = Path(...), transaction_id: str = Path(...)):
    """Returns the full detailed record side-by-side with its override history."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT deterministic_result_json 
                FROM reconciliation_snapshots 
                WHERE run_id = ? AND transaction_id = ?
            """, (run_id, transaction_id))
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Record not found in the specified run.")
                
            det_result = ReconciliationResult.model_validate_json(row["deterministic_result_json"])
            
            cursor.execute("""
                SELECT override_id, action, candidate_id, reviewer_note, created_at
                FROM overrides
                WHERE run_id = ? AND transaction_id = ?
                ORDER BY created_at ASC
            """, (run_id, transaction_id))
            ov_rows = cursor.fetchall()
            
            overrides = []
            for ov in ov_rows:
                overrides.append(OverrideRecordV2(
                    override_id=ov["override_id"],
                    action=ov["action"],
                    candidate_id=ov["candidate_id"],
                    reviewer_note=ov["reviewer_note"],
                    created_at=ov["created_at"]
                ))
                
            return RecordDetail(
                transaction_id=transaction_id,
                deterministic_result=det_result,
                override_history=overrides
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching run record: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch record.")

@router_v2.get("/evaluation")
def get_evaluation_artifacts():
    """Reads structured JSON artifacts produced by Phase 2 evaluation."""
    try:
        results_dir = "evaluation/results"
        if not os.path.exists(results_dir):
            return {"artifacts": []}
            
        artifacts = []
        for filename in sorted(os.listdir(results_dir), reverse=True):
            if filename.endswith(".json"):
                with open(os.path.join(results_dir, filename), "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        # We might not want to return the full detailed list here for size reasons,
                        # but returning the metadata and metrics is safe.
                        artifacts.append({
                            "filename": filename,
                            "metadata": data.get("metadata"),
                            "metrics": data.get("metrics"),
                            "scenario_breakdown": data.get("scenario_breakdown")
                        })
                    except json.JSONDecodeError:
                        continue
        return {"artifacts": artifacts}
    except Exception as e:
        logger.error(f"Error fetching evaluation artifacts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch evaluation artifacts.")
