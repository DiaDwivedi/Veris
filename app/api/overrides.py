from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import json
from app.models.api import OverrideRequest, OverrideRecord
from app.db.session import get_db

router = APIRouter()

def process_override(request: OverrideRequest, action: str):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Check if snapshot exists
        cursor.execute("SELECT deterministic_result_json FROM reconciliation_snapshots WHERE transaction_id = ?", (request.transaction_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transaction not found in deterministic snapshots.")
            
        # 2. Deserialize snapshot to validate stale candidates
        snapshot = json.loads(row["deterministic_result_json"])
        
        # We enforce that the client must only approve a deterministic candidate that currently exists
        snapshot_candidate_id = None
        if snapshot.get("candidate") and snapshot["candidate"].get("merchant_record"):
            snapshot_candidate_id = snapshot["candidate"]["merchant_record"].get("record_id")
            
        if not snapshot_candidate_id:
            raise HTTPException(status_code=422, detail="Overrides are not permitted for deterministic results with no candidate.")
            
        if request.candidate_id != snapshot_candidate_id:
            raise HTTPException(status_code=409, detail="Stale candidate validation failed. The provided candidate_id does not match the deterministic snapshot.")
            
        # 3. Check for existing override
        cursor.execute("SELECT action FROM overrides WHERE transaction_id = ?", (request.transaction_id,))
        override_row = cursor.fetchone()
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if override_row:
            existing_action = override_row["action"]
            if existing_action == action:
                # Idempotent repeat
                return OverrideRecord(action=action, timestamp=timestamp)
            else:
                # Conflicting action -> 409
                raise HTTPException(status_code=409, detail=f"Conflict: transaction already overridden with action '{existing_action}'.")
                
        # 4. Insert new override
        cursor.execute(
            "INSERT INTO overrides (transaction_id, action, candidate_id, timestamp) VALUES (?, ?, ?, ?)",
            (request.transaction_id, action, request.candidate_id, timestamp)
        )
        conn.commit()
        
        return OverrideRecord(action=action, timestamp=timestamp)


@router.post("/approve", response_model=OverrideRecord)
def approve_match(request: OverrideRequest):
    return process_override(request, "approve")


@router.post("/reject", response_model=OverrideRecord)
def reject_match(request: OverrideRequest):
    return process_override(request, "reject")
