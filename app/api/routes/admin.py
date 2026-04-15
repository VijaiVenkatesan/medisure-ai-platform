"""
Admin API routes — Full CRUD for claims, policies, and system management.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import update, delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import get_db, ClaimDB, PolicyDocumentDB, AuditLogDB
from app.infrastructure.db.repository import ClaimRepository, AuditRepository
from app.models.schemas import ClaimStatus
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ── CLAIM ADMIN ──────────────────────────────────────────────────

class ClaimUpdateRequest(BaseModel):
    status: Optional[str] = None
    fraud_score: Optional[float] = None
    decision: Optional[str] = None
    decision_explanation: Optional[str] = None
    approved_amount: Optional[float] = None
    claimant_name: Optional[str] = None


@router.get("/admin/claims",
            tags=["Admin"],
            summary="Admin: list all claims with full details")
async def admin_list_claims(
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Admin view of all claims with extended filters and full data."""
    query = select(ClaimDB).order_by(ClaimDB.created_at.desc())
    count_q = select(func.count(ClaimDB.id))

    if status:
        query = query.where(ClaimDB.status == status)
        count_q = count_q.where(ClaimDB.status == status)
    if search:
        like = f"%{search}%"
        query = query.where(
            (ClaimDB.claimant_name.ilike(like)) |
            (ClaimDB.policy_number.ilike(like)) |
            (ClaimDB.id.ilike(like))
        )

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    count_result = await db.execute(count_q)
    claims = result.scalars().all()
    total = count_result.scalar_one()

    return {
        "claims": [_claim_to_dict(c) for c in claims],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.patch("/admin/claims/{claim_id}",
              tags=["Admin"],
              summary="Admin: update claim fields")
async def admin_update_claim(
    claim_id: str,
    update_data: ClaimUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update claim status, fraud score, decision, or other fields."""
    result = await db.execute(select(ClaimDB).where(ClaimDB.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")

    updates = {k: v for k, v in update_data.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.utcnow()

    await db.execute(update(ClaimDB).where(ClaimDB.id == claim_id).values(**updates))
    await db.commit()

    # Audit log
    repo = AuditRepository(db)
    await repo.log_event(claim_id, "ADMIN_UPDATE", "ADMIN", updates)

    logger.info(f"Admin updated claim {claim_id}", extra={"extra_data": updates})
    return {"status": "updated", "claim_id": claim_id, "updates": updates}


@router.delete("/admin/claims/{claim_id}",
               tags=["Admin"],
               summary="Admin: delete a claim")
async def admin_delete_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a claim and all related data (cascade)."""
    result = await db.execute(select(ClaimDB).where(ClaimDB.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")

    await db.execute(delete(ClaimDB).where(ClaimDB.id == claim_id))
    await db.commit()

    logger.info(f"Admin deleted claim {claim_id}")
    return {"status": "deleted", "claim_id": claim_id}


@router.post("/admin/claims/{claim_id}/reprocess",
             tags=["Admin"],
             summary="Admin: reprocess a failed claim")
async def admin_reprocess_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Reset claim status to RECEIVED and trigger reprocessing."""
    result = await db.execute(select(ClaimDB).where(ClaimDB.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")

    if not claim.documents:
        raise HTTPException(422, "No document found to reprocess")

    await db.execute(
        update(ClaimDB).where(ClaimDB.id == claim_id).values(
            status=ClaimStatus.RECEIVED.value,
            decision=None,
            fraud_score=None,
            error_log=[],
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()

    # Trigger reprocessing
    import asyncio
    from app.infrastructure.db.models import AsyncSessionLocal
    from app.services.claims_service import ClaimsService

    async def _reprocess():
        async with AsyncSessionLocal() as new_db:
            svc = ClaimsService(new_db)
            doc = claim.documents[0] if claim.documents else None
            if doc:
                await svc._process_claim_async(
                    claim_id, doc.file_path, doc.id, claim.correlation_id
                )

    asyncio.create_task(_reprocess())
    return {"status": "reprocessing_started", "claim_id": claim_id}


# ── AUDIT LOGS ──────────────────────────────────────────────────

@router.get("/admin/logs",
            tags=["Admin"],
            summary="Admin: get system audit logs")
async def admin_get_logs(
    page: int = 1,
    page_size: int = 100,
    event_type: Optional[str] = None,
    actor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all system audit logs with filtering."""
    query = select(AuditLogDB).order_by(AuditLogDB.timestamp.desc())
    count_q = select(func.count(AuditLogDB.id))

    if event_type:
        query = query.where(AuditLogDB.event_type == event_type)
        count_q = count_q.where(AuditLogDB.event_type == event_type)
    if actor:
        query = query.where(AuditLogDB.actor == actor)
        count_q = count_q.where(AuditLogDB.actor == actor)

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    count_result = await db.execute(count_q)
    logs = result.scalars().all()
    total = count_result.scalar_one()

    return {
        "logs": [
            {
                "id": log.id,
                "claim_id": log.claim_id,
                "event_type": log.event_type,
                "actor": log.actor,
                "details": log.details,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ── STATS ──────────────────────────────────────────────────────

@router.get("/admin/stats",
            tags=["Admin"],
            summary="Admin: full system statistics")
async def admin_stats(db: AsyncSession = Depends(get_db)):
    """Comprehensive system statistics for admin dashboard."""
    from sqlalchemy import text

    total_claims = (await db.execute(select(func.count(ClaimDB.id)))).scalar()
    avg_fraud = (await db.execute(
        select(func.avg(ClaimDB.fraud_score)).where(ClaimDB.fraud_score.isnot(None))
    )).scalar()
    total_amount = (await db.execute(
        select(func.sum(ClaimDB.claimed_amount)).where(ClaimDB.claimed_amount.isnot(None))
    )).scalar()
    approved_amount = (await db.execute(
        select(func.sum(ClaimDB.approved_amount)).where(ClaimDB.approved_amount.isnot(None))
    )).scalar()
    total_logs = (await db.execute(select(func.count(AuditLogDB.id)))).scalar()

    by_status_result = await db.execute(
        select(ClaimDB.status, func.count(ClaimDB.id)).group_by(ClaimDB.status)
    )
    by_status = {row[0]: row[1] for row in by_status_result.all()}

    by_type_result = await db.execute(
        select(ClaimDB.insurance_type, func.count(ClaimDB.id))
        .where(ClaimDB.insurance_type.isnot(None))
        .group_by(ClaimDB.insurance_type)
    )
    by_type = {row[0]: row[1] for row in by_type_result.all()}

    return {
        "claims": {
            "total": total_claims or 0,
            "by_status": by_status,
            "by_type": by_type,
            "avg_fraud_score": round(avg_fraud or 0, 3),
            "total_claimed_inr": round(total_amount or 0, 2),
            "total_approved_inr": round(approved_amount or 0, 2),
        },
        "logs": {"total": total_logs or 0},
        "system": {"status": "healthy", "version": "1.0.0"},
    }


def _claim_to_dict(c: ClaimDB) -> dict:
    return {
        "id": c.id, "status": c.status, "claimant_name": c.claimant_name,
        "policy_number": c.policy_number, "insurance_type": c.insurance_type,
        "claimed_amount": c.claimed_amount, "currency": c.currency,
        "fraud_score": c.fraud_score, "fraud_level": c.fraud_level,
        "decision": c.decision, "decision_confidence": c.decision_confidence,
        "approved_amount": c.approved_amount,
        "decision_explanation": c.decision_explanation,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
        "retry_count": c.retry_count,
        "error_log": c.error_log or [],
    }
