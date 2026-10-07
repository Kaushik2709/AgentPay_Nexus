import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.audit.ledger import AuditLedgerEngine
from app.schemas.agent_schemas import AuditVerificationResponse

router = APIRouter(prefix="/audit", tags=["Cryptographic Audit Ledger"])

@router.get("/trail")
async def get_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves chronological cryptographic audit ledger entries."""
    entries = await AuditLedgerEngine.get_audit_trail(db, limit=limit)
    return [
        {
            "id": e.id,
            "sequence_number": e.sequence_number,
            "timestamp": e.timestamp,
            "actor": e.actor,
            "action": e.action,
            "payload": json.loads(e.payload_json or "{}"),
            "prev_hash": e.prev_hash,
            "entry_hash": e.entry_hash,
            "verified": e.verified
        }
        for e in entries
    ]

@router.get("/verify", response_model=AuditVerificationResponse)
async def verify_audit_ledger(db: AsyncSession = Depends(get_db)):
    """
    Cryptographically verifies the entire SHA-256 hash chain from Genesis block.
    Ensures zero tampering and non-repudiation.
    """
    result = await AuditLedgerEngine.verify_chain_integrity(db)
    return AuditVerificationResponse(**result)
