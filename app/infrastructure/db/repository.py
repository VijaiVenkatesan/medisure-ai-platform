"""
Repository pattern for all database operations.
Provides clean abstraction over SQLAlchemy for the service layer.
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import (
    ClaimDB, ClaimDocumentDB, DecisionDB, AuditLogDB, HITLReviewDB, PolicyDocumentDB
)
from app.models.schemas import (
    WorkflowState, ClaimListItem, ClaimStatus, HITLAction
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ClaimRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_claim(self, claim_id: str, correlation_id: str) -> ClaimDB:
        claim = ClaimDB(
            id=claim_id,
            correlation_id=correlation_id,
            status=ClaimStatus.RECEIVED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(claim)
        await self.db.commit()
        await self.db.refresh(claim)
        logger.info(f"Created claim record", extra={"extra_data": {"claim_id": claim_id}})
        return claim

    async def get_claim(self, claim_id: str) -> Optional[ClaimDB]:
        result = await self.db.execute(
            select(ClaimDB)
            .options(selectinload(ClaimDB.documents))
            .where(ClaimDB.id == claim_id)
        )
        return result.scalar_one_or_none()

    async def get_claim_by_correlation_id(self, correlation_id: str) -> Optional[ClaimDB]:
        result = await self.db.execute(
            select(ClaimDB).where(ClaimDB.correlation_id == correlation_id)
        )
        return result.scalar_one_or_none()

    async def update_from_workflow_state(self, state: WorkflowState) -> ClaimDB:
        """Persist the full workflow state to the database."""
        claim = await self.get_claim(state.claim_id)
        if not claim:
            raise ValueError(f"Claim {state.claim_id} not found")

        claim.status = state.status
        claim.updated_at = datetime.utcnow()
        claim.retry_count = state.retry_count
        claim.error_log = state.errors

        if state.ocr_result:
            claim.ocr_raw_text = state.ocr_result.raw_text[:10000] if state.ocr_result.raw_text else None
            claim.ocr_confidence = state.ocr_result.confidence

        if state.extracted_data:
            ed = state.extracted_data
            claim.extracted_data = ed.model_dump()
            claim.claimant_name = ed.claimant.name
            claim.policy_number = ed.policy.policy_number
            claim.insurance_type = ed.policy.policy_type
            claim.claimed_amount = ed.amounts.claimed_amount
            claim.currency = ed.amounts.currency or "INR"

        if state.fraud_result:
            claim.fraud_score = state.fraud_result.fraud_score
            claim.fraud_level = state.fraud_result.fraud_level
            claim.fraud_indicators = [i.model_dump() for i in state.fraud_result.indicators]

        if state.decision_result:
            claim.decision = state.decision_result.decision
            claim.decision_confidence = state.decision_result.confidence
            claim.decision_explanation = state.decision_result.explanation
            claim.approved_amount = state.decision_result.approved_amount
            claim.processed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(claim)
        return claim

    async def update_status(self, claim_id: str, status: ClaimStatus) -> None:
        await self.db.execute(
            update(ClaimDB)
            .where(ClaimDB.id == claim_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        await self.db.commit()

    async def list_claims(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ClaimDB], int]:
        query = select(ClaimDB).order_by(ClaimDB.created_at.desc())
        count_query = select(func.count(ClaimDB.id))

        if status:
            query = query.where(ClaimDB.status == status)
            count_query = count_query.where(ClaimDB.status == status)

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        claims = result.scalars().all()
        total = count_result.scalar_one()
        return list(claims), total

    async def get_pending_hitl_claims(self) -> list[ClaimDB]:
        result = await self.db.execute(
            select(ClaimDB)
            .where(ClaimDB.status == ClaimStatus.HITL_REVIEW)
            .order_by(ClaimDB.created_at.asc())
        )
        return list(result.scalars().all())


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(
        self,
        claim_id: str,
        filename: str,
        file_path: str,
        content_type: str,
        size_bytes: int,
    ) -> ClaimDocumentDB:
        doc = ClaimDocumentDB(
            id=str(uuid4()),
            claim_id=claim_id,
            filename=filename,
            file_path=file_path,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def update_ocr_status(self, doc_id: str, status: str, confidence: Optional[float] = None) -> None:
        await self.db.execute(
            update(ClaimDocumentDB)
            .where(ClaimDocumentDB.id == doc_id)
            .values(ocr_status=status, ocr_confidence=confidence)
        )
        await self.db.commit()


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        claim_id: str,
        event_type: str,
        actor: str,
        details: dict,
        ip_address: Optional[str] = None,
    ) -> AuditLogDB:
        entry = AuditLogDB(
            id=str(uuid4()),
            claim_id=claim_id,
            event_type=event_type,
            actor=actor,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
        )
        self.db.add(entry)
        await self.db.commit()
        return entry

    async def get_claim_audit_trail(self, claim_id: str) -> list[AuditLogDB]:
        result = await self.db.execute(
            select(AuditLogDB)
            .where(AuditLogDB.claim_id == claim_id)
            .order_by(AuditLogDB.timestamp.asc())
        )
        return list(result.scalars().all())


class HITLRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_review(
        self,
        claim_id: str,
        reviewer_id: str,
        action: HITLAction,
        notes: str = "",
        approved_amount: Optional[float] = None,
        rejection_reason: Optional[str] = None,
    ) -> HITLReviewDB:
        review = HITLReviewDB(
            id=str(uuid4()),
            claim_id=claim_id,
            reviewer_id=reviewer_id,
            action=action,
            notes=notes,
            approved_amount=approved_amount,
            rejection_reason=rejection_reason,
            reviewed_at=datetime.utcnow(),
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review


class DecisionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_decision(
        self,
        claim_id: str,
        decision: str,
        confidence: float,
        explanation: str,
        approved_amount: Optional[float] = None,
        rejection_reasons: Optional[list] = None,
        conditions: Optional[list] = None,
        decision_factors: Optional[dict] = None,
        is_final: bool = False,
        made_by: str = "SYSTEM",
    ) -> DecisionDB:
        dec = DecisionDB(
            id=str(uuid4()),
            claim_id=claim_id,
            decision=decision,
            confidence=confidence,
            explanation=explanation,
            approved_amount=approved_amount,
            rejection_reasons=rejection_reasons or [],
            conditions=conditions or [],
            decision_factors=decision_factors or {},
            is_final=is_final,
            made_by=made_by,
            made_at=datetime.utcnow(),
        )
        self.db.add(dec)
        await self.db.commit()
        await self.db.refresh(dec)
        return dec
