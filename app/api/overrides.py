from fastapi import APIRouter, HTTPException, Path
from datetime import datetime, timezone
import json
import uuid
from typing import Optional
from app.models.api import OverrideRequest, OverrideRecord, OverrideRequestV2, OverrideRecordV2
from app.db.session import get_db

router = APIRouter()

# --- V1 Endpoints (Legacy Resolution) ---

def process_legacy_override(request: OverrideRequest, action: str):
    """
    Resolves legacy override requests that only provide transaction_id.
    It prevents silent cross-run corruption by checking if multiple runs exist.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if transaction_id exists in multiple runs
        cursor.execute("SELECT run_id FROM reconciliation_snapshots WHERE transaction_id = ?", (request.transaction_id,))
        rows = cursor.fetchall()
        
        if not rows:
            raise HTTPException(status_code=404, detail="Transaction not found in any deterministic snapshots.")
            
        if len(rows) > 1:
            raise HTTPException(status_code=400, detail="Ambiguous transaction_id: exists in multiple runs. Please provide a run_id using the v2 API.")
            
        run_id = rows[0]["run_id"]
        
        # Forward to v2 logic
        req_v2 = OverrideRequestV2(action=action, candidate_id=request.candidate_id, reviewer_note=None)
        return _insert_override(conn, run_id, request.transaction_id, req_v2)

@router.post("/approve", response_model=OverrideRecord)
def approve_match(request: OverrideRequest):
    res_v2 = process_legacy_override(request, "approve")
    return OverrideRecord(action=res_v2.action, timestamp=res_v2.created_at)

@router.post("/reject", response_model=OverrideRecord)
def reject_match(request: OverrideRequest):
    res_v2 = process_legacy_override(request, "reject")
    return OverrideRecord(action=res_v2.action, timestamp=res_v2.created_at)

# --- V2 Endpoints (Run-scoped append-only) ---

router_v2 = APIRouter()

def _insert_override(conn, run_id: str, transaction_id: str, request: OverrideRequestV2) -> OverrideRecordV2:
    cursor = conn.cursor()
    
    # 1. Fetch snapshot to validate candidate integrity
    cursor.execute("""
        SELECT deterministic_result_json 
        FROM reconciliation_snapshots 
        WHERE run_id = ? AND transaction_id = ?
    """, (run_id, transaction_id))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Snapshot not found for the specified run and transaction.")
        
    snapshot = json.loads(row["deterministic_result_json"])
    
    # 2. Candidate Integrity Validation
    if request.candidate_id:
        valid_candidates = []
        if snapshot.get("candidate") and snapshot["candidate"].get("merchant_record"):
            valid_candidates.append(snapshot["candidate"]["merchant_record"].get("record_id"))
            
        for comp_c in snapshot.get("competing_candidates", []):
            if comp_c.get("merchant_record"):
                valid_candidates.append(comp_c["merchant_record"].get("record_id"))
                
        if request.candidate_id not in valid_candidates:
            raise HTTPException(status_code=422, detail="Candidate integrity validation failed. The provided candidate_id does not belong to the deterministic snapshot candidates for this run.")

    # 3. Insert into append-only overrides table
    override_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    
    cursor.execute("""
        INSERT INTO overrides (override_id, run_id, transaction_id, action, candidate_id, reviewer_note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (override_id, run_id, transaction_id, request.action, request.candidate_id, request.reviewer_note, created_at))
    
    conn.commit()
    
    return OverrideRecordV2(
        override_id=override_id,
        action=request.action,
        candidate_id=request.candidate_id,
        reviewer_note=request.reviewer_note,
        created_at=created_at
    )

@router_v2.post("/{run_id}/records/{transaction_id}/override", response_model=OverrideRecordV2)
def create_override(request: OverrideRequestV2, run_id: str = Path(...), transaction_id: str = Path(...)):
    """Creates a run-scoped override event in the append-only history."""
    try:
        with get_db() as conn:
            return _insert_override(conn, run_id, transaction_id, request)
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error creating override: {e}")
        raise HTTPException(status_code=500, detail="Failed to create override.")
