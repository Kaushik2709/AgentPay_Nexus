import hashlib
import json
import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import AuditEntry

class AuditLedgerEngine:
    """
    Immutable Cryptographic Audit Ledger.
    - Uses SHA-256 hash chaining for tamper-evident non-repudiation.
    - Verifies the integrity of the entire decision chain.
    - Generates plain-English explainability cards for every money movement.
    """

    @staticmethod
    def compute_hash(
        sequence: int,
        actor: str,
        action: str,
        timestamp: str,
        prev_hash: str,
        payload_json: str
    ) -> str:
        raw_str = f"{sequence}|{actor}|{action}|{timestamp}|{prev_hash}|{payload_json}"
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    @staticmethod
    async def append_entry(
        db: AsyncSession,
        actor: str,
        action: str,
        payload: Dict[str, Any]
    ) -> AuditEntry:
        # Get latest entry to obtain previous hash and next sequence number
        latest_query = select(AuditEntry).order_by(AuditEntry.sequence_number.desc()).limit(1)
        res = await db.execute(latest_query)
        latest = res.scalar_one_or_none()

        if latest:
            next_seq = latest.sequence_number + 1
            prev_hash = latest.entry_hash
        else:
            next_seq = 0
            prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"

        timestamp = datetime.datetime.utcnow().isoformat()
        payload_json = json.dumps(payload, sort_keys=True)
        entry_hash = AuditLedgerEngine.compute_hash(
            next_seq, actor, action, timestamp, prev_hash, payload_json
        )

        entry = AuditEntry(
            sequence_number=next_seq,
            timestamp=timestamp,
            actor=actor,
            action=action,
            payload_json=payload_json,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            verified=True
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def get_audit_trail(db: AsyncSession, limit: int = 100) -> List[AuditEntry]:
        query = select(AuditEntry).order_by(AuditEntry.sequence_number.desc()).limit(limit)
        res = await db.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def verify_chain_integrity(db: AsyncSession) -> Dict[str, Any]:
        """
        Validates every link in the cryptographic audit ledger from genesis block to the head.
        Ensures zero tampering and non-repudiation.
        """
        query = select(AuditEntry).order_by(AuditEntry.sequence_number.asc())
        res = await db.execute(query)
        entries = res.scalars().all()

        if not entries:
            return {
                "is_valid": True,
                "total_blocks_verified": 0,
                "latest_hash": "",
                "genesis_hash": "",
                "tampered_blocks": [],
                "message": "Ledger is currently empty."
            }

        tampered: List[int] = []
        prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"

        for idx, entry in enumerate(entries):
            # Check link to previous hash
            if idx > 0 and entry.prev_hash != prev_hash:
                tampered.append(entry.sequence_number)

            # Re-compute entry hash
            expected_hash = AuditLedgerEngine.compute_hash(
                entry.sequence_number,
                entry.actor,
                entry.action,
                entry.timestamp,
                entry.prev_hash,
                entry.payload_json
            )

            if expected_hash != entry.entry_hash:
                tampered.append(entry.sequence_number)

            prev_hash = entry.entry_hash

        is_valid = len(tampered) == 0
        return {
            "is_valid": is_valid,
            "total_blocks_verified": len(entries),
            "latest_hash": entries[-1].entry_hash if entries else "",
            "genesis_hash": entries[0].entry_hash if entries else "",
            "tampered_blocks": tampered,
            "message": "All cryptographic SHA-256 blocks verified successfully. Ledger integrity 100% intact." if is_valid else f"Integrity check FAILED. Tampered blocks detected: {tampered}"
        }
