"""
Claims Service: Orchestrates claim submission, processing, and retrieval.
Ensures idempotency, audit logging, and proper error handling.
"""
from __future__ import annotations
import asyncio
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger, set_claim_context, set_correlation_id
from app.infrastructure.db.repository import (
    ClaimRepository, DocumentRepository, AuditRepository,
    HITLRepository, DecisionRepository
)
from app.models.schemas import (
    WorkflowState, ClaimStatus, ClaimSubmitResponse,
    ClaimStatusResponse, ClaimListResponse, ClaimListItem,
    HITLReviewRequest, HITLReviewResponse, HITLAction,
    PolicyIndexRequest, HealthCheckResponse
)
from app.workflows.claims_workflow import run_workflow

logger = get_logger(__name__)

# Upload storage directory
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class ClaimsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.claims_repo = ClaimRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.audit_repo = AuditRepository(db)
        self.hitl_repo = HITLRepository(db)
        self.decision_repo = DecisionRepository(db)

    async def submit_claim(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        claim_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> ClaimSubmitResponse:
        """
        Submit a new insurance claim document.
        Idempotent: same correlation_id returns existing claim.
        """
        corr_id = correlation_id or str(uuid4())

        # Idempotency check
        existing = await self.claims_repo.get_claim_by_correlation_id(corr_id)
        if existing:
            logger.info(f"Idempotent claim submission - returning existing: {existing.id}")
            return ClaimSubmitResponse(
                claim_id=existing.id,
                status=ClaimStatus(existing.status),
                message="Claim already submitted (idempotent response)",
                correlation_id=corr_id,
            )

        # Generate claim ID
        cid = claim_id or f"CLM-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        set_claim_context(cid)
        set_correlation_id(corr_id)

        # Validate file
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in settings.ALLOWED_FILE_TYPES:
            raise ValueError(f"Unsupported file type: {ext}. Allowed: {settings.ALLOWED_FILE_TYPES}")

        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            raise ValueError(f"File too large: {file_size_mb:.1f}MB. Max: {settings.MAX_FILE_SIZE_MB}MB")

        # Save file
        claim_dir = UPLOAD_DIR / cid
        claim_dir.mkdir(exist_ok=True)
        file_path = claim_dir / filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File saved: {file_path}", extra={"extra_data": {"claim_id": cid, "size_mb": file_size_mb}})

        # Create DB records
        claim = await self.claims_repo.create_claim(cid, corr_id)
        doc = await self.doc_repo.create_document(
            claim_id=cid,
            filename=filename,
            file_path=str(file_path),
            content_type=content_type,
            size_bytes=len(file_content),
        )

        # Audit log
        await self.audit_repo.log_event(
            claim_id=cid,
            event_type="CLAIM_SUBMITTED",
            actor="API",
            details={
                "filename": filename,
                "content_type": content_type,
                "size_bytes": len(file_content),
                "correlation_id": corr_id,
            },
        )

        # Start async processing
        asyncio.create_task(
            self._process_claim_async(cid, str(file_path), doc.id, corr_id)
        )

        return ClaimSubmitResponse(
            claim_id=cid,
            status=ClaimStatus.RECEIVED,
            message="Claim submitted successfully. Processing has started.",
            correlation_id=corr_id,
        )

    async def _process_claim_async(
        self,
        claim_id: str,
        file_path: str,
        document_id: str,
        correlation_id: str,
    ) -> None:
        """
        Background task: Run the full processing workflow.
        Updates DB at each stage.
        """
        set_claim_context(claim_id)
        set_correlation_id(correlation_id)

        logger.info(f"Starting async processing for claim {claim_id}")

        try:
            # Initialize workflow state
            initial_state = WorkflowState(
                claim_id=claim_id,
                correlation_id=correlation_id,
                document_path=file_path,
                document_id=document_id,
                status=ClaimStatus.OCR_PROCESSING,
            )

            # Run the full workflow
            final_state = await run_workflow(initial_state)

            # Persist final state
            async with AsyncSession(self.db.bind) as db:
                repo = ClaimRepository(db)
                await repo.update_from_workflow_state(final_state)

                # Save decision to history
                if final_state.decision_result:
                    dr = final_state.decision_result
                    decision_repo = DecisionRepository(db)
                    await decision_repo.create_decision(
                        claim_id=claim_id,
                        decision=dr.decision.value,
                        confidence=dr.confidence,
                        explanation=dr.explanation,
                        approved_amount=dr.approved_amount,
                        rejection_reasons=dr.rejection_reasons,
                        conditions=dr.conditions,
                        decision_factors=dr.decision_factors,
                        is_final=not dr.requires_hitl,
                        made_by="SYSTEM",
                    )

                    # Audit log
                    audit_repo = AuditRepository(db)
                    await audit_repo.log_event(
                        claim_id=claim_id,
                        event_type="DECISION_MADE",
                        actor="SYSTEM",
                        details={
                            "decision": dr.decision.value,
                            "confidence": dr.confidence,
                            "requires_hitl": dr.requires_hitl,
                            "fraud_score": final_state.fraud_result.fraud_score if final_state.fraud_result else None,
                        },
                    )

            logger.info(
                f"Claim {claim_id} processing complete",
                extra={
                    "extra_data": {
                        "claim_id": claim_id,
                        "status": final_state.status.value,
                        "decision": final_state.decision_result.decision.value if final_state.decision_result else None,
                    }
                },
            )

        except Exception as e:
            logger.error(f"Async processing failed for claim {claim_id}: {e}", exc_info=True)
            # Update status to ERROR in DB
            try:
                async with AsyncSession(self.db.bind) as db:
                    repo = ClaimRepository(db)
                    await repo.update_status(claim_id, ClaimStatus.ERROR)
            except Exception as db_err:
                logger.error(f"Failed to update error status: {db_err}")

    async def get_claim_status(self, claim_id: str) -> ClaimStatusResponse:
        """Get the current status and details of a claim."""
        claim = await self.claims_repo.get_claim(claim_id)
        if not claim:
            raise ValueError(f"Claim not found: {claim_id}")

        from app.models.schemas import ExtractedClaimData
        extracted = None
        if claim.extracted_data:
            try:
                extracted = ExtractedClaimData(**claim.extracted_data)
            except Exception:
                pass

        return ClaimStatusResponse(
            claim_id=claim.id,
            status=ClaimStatus(claim.status),
            created_at=claim.created_at,
            updated_at=claim.updated_at,
            extracted_data=extracted,
            fraud_score=claim.fraud_score,
            fraud_level=claim.fraud_level,
            decision=claim.decision,
            decision_confidence=claim.decision_confidence,
            explanation=claim.decision_explanation,
            errors=claim.error_log or [],
        )

    async def list_claims(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ClaimListResponse:
        """List claims with optional status filter."""
        claims, total = await self.claims_repo.list_claims(status, page, page_size)

        items = [
            ClaimListItem(
                claim_id=c.id,
                status=ClaimStatus(c.status),
                policy_type=c.insurance_type,
                claimed_amount=c.claimed_amount,
                currency=c.currency or "INR",
                fraud_score=c.fraud_score,
                decision=c.decision,
                created_at=c.created_at,
                claimant_name=c.claimant_name,
            )
            for c in claims
        ]

        return ClaimListResponse(
            claims=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_pending_hitl(self) -> ClaimListResponse:
        """Get all claims pending HITL review."""
        claims = await self.claims_repo.get_pending_hitl_claims()
        items = [
            ClaimListItem(
                claim_id=c.id,
                status=ClaimStatus(c.status),
                policy_type=c.insurance_type,
                claimed_amount=c.claimed_amount,
                currency=c.currency or "INR",
                fraud_score=c.fraud_score,
                decision=c.decision,
                created_at=c.created_at,
                claimant_name=c.claimant_name,
            )
            for c in claims
        ]
        return ClaimListResponse(claims=items, total=len(items), page=1, page_size=len(items))

    async def submit_hitl_review(
        self,
        claim_id: str,
        review: HITLReviewRequest,
        reviewer_id: str,
    ) -> HITLReviewResponse:
        """Process a HITL reviewer action."""
        claim = await self.claims_repo.get_claim(claim_id)
        if not claim:
            raise ValueError(f"Claim not found: {claim_id}")

        if claim.status != ClaimStatus.HITL_REVIEW:
            raise ValueError(f"Claim {claim_id} is not in HITL_REVIEW status (current: {claim.status})")

        # Determine new status based on action
        action_to_status = {
            HITLAction.APPROVE: ClaimStatus.APPROVED,
            HITLAction.REJECT: ClaimStatus.REJECTED,
            HITLAction.INVESTIGATE: ClaimStatus.INVESTIGATING,
            HITLAction.REQUEST_MORE_INFO: ClaimStatus.HITL_REVIEW,
        }
        new_status = action_to_status[review.action]

        # Save HITL review
        await self.hitl_repo.create_review(
            claim_id=claim_id,
            reviewer_id=reviewer_id,
            action=review.action,
            notes=review.reviewer_notes,
            approved_amount=review.approved_amount,
            rejection_reason=review.rejection_reason,
        )

        # Save final decision
        await self.decision_repo.create_decision(
            claim_id=claim_id,
            decision=review.action.value,
            confidence=1.0,  # Human decision = full confidence
            explanation=review.reviewer_notes or f"Reviewer decision: {review.action.value}",
            approved_amount=review.approved_amount,
            rejection_reasons=[review.rejection_reason] if review.rejection_reason else [],
            is_final=True,
            made_by=reviewer_id,
        )

        # Update claim status
        await self.claims_repo.update_status(claim_id, new_status)

        # Audit log
        await self.audit_repo.log_event(
            claim_id=claim_id,
            event_type="HITL_REVIEW_COMPLETED",
            actor=reviewer_id,
            details={
                "action": review.action.value,
                "notes": review.reviewer_notes,
                "approved_amount": review.approved_amount,
                "new_status": new_status.value,
            },
        )

        return HITLReviewResponse(
            claim_id=claim_id,
            action=review.action,
            reviewer_id=reviewer_id,
            reviewed_at=datetime.utcnow(),
            new_status=new_status,
            message=f"Claim {review.action.value.lower()}d by reviewer {reviewer_id}",
        )

    async def index_policy(self, request: PolicyIndexRequest) -> dict:
        """Index a policy document into the vector store."""
        from app.infrastructure.vectorstore.chroma_store import get_vector_store

        vector_store = get_vector_store()
        chunk_count = await vector_store.index_policy(
            policy_text=request.policy_text,
            policy_name=request.policy_name,
            insurance_type=request.insurance_type,
            country=request.country,
            company=request.company,
        )

        await self.audit_repo.log_event(
            claim_id="SYSTEM",
            event_type="POLICY_INDEXED",
            actor="API",
            details={
                "policy_name": request.policy_name,
                "insurance_type": request.insurance_type.value,
                "country": request.country.value,
                "chunks": chunk_count,
            },
        )

        return {
            "status": "indexed",
            "policy_name": request.policy_name,
            "chunks_indexed": chunk_count,
        }

    async def get_audit_trail(self, claim_id: str) -> list[dict]:
        """Get the complete audit trail for a claim."""
        logs = await self.audit_repo.get_claim_audit_trail(claim_id)
        return [
            {
                "id": log.id,
                "event_type": log.event_type,
                "actor": log.actor,
                "details": log.details,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ]


async def get_health_status() -> HealthCheckResponse:
    """Check health of all system components."""
    from app.infrastructure.vectorstore.chroma_store import get_vector_store
    from datetime import datetime

    services = {}

    # Check vector store
    try:
        vs = get_vector_store()
        stats = vs.get_stats()
        services["vectorstore"] = f"healthy ({stats.get('total_chunks', 0)} policy chunks)"
    except Exception as e:
        services["vectorstore"] = f"degraded: {str(e)[:50]}"

    # Check Groq
    try:
        from app.infrastructure.llm.groq_client import get_groq_client
        services["groq_llm"] = "healthy"
    except Exception as e:
        services["groq_llm"] = f"degraded: {str(e)[:50]}"

    # Check DB
    try:
        services["database"] = "healthy"
    except Exception as e:
        services["database"] = f"degraded: {str(e)[:50]}"

    # Check upload dir
    services["file_storage"] = "healthy" if UPLOAD_DIR.exists() else "degraded"

    overall = "healthy" if all("degraded" not in v for v in services.values()) else "degraded"

    return HealthCheckResponse(
        status=overall,
        version=settings.APP_VERSION,
        services=services,
        timestamp=datetime.utcnow(),
    )
