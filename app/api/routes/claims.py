"""
FastAPI routes for the claims processing API.
All routes follow REST conventions with proper error handling.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import get_db
from app.models.schemas import (
    ClaimSubmitResponse, ClaimStatusResponse, ClaimListResponse,
    HITLReviewRequest, HITLReviewResponse, PolicyIndexRequest,
    HealthCheckResponse, AuditLogEntry
)
from app.services.claims_service import ClaimsService, get_health_status
from app.core.logging import get_logger, set_correlation_id

logger = get_logger(__name__)

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_db)) -> ClaimsService:
    return ClaimsService(db)


# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────

@router.get("/health", response_model=HealthCheckResponse, tags=["System"])
async def health_check():
    """System health check endpoint."""
    return await get_health_status()


# ─────────────────────────────────────────────
# CLAIM SUBMISSION
# ─────────────────────────────────────────────

@router.post(
    "/claims/submit",
    response_model=ClaimSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Claims"],
    summary="Submit a new insurance claim document",
)
async def submit_claim(
    request: Request,
    file: UploadFile = File(..., description="Insurance claim document (PDF, PNG, JPG, TIFF)"),
    correlation_id: Optional[str] = Form(None, description="Optional idempotency key"),
    service: ClaimsService = Depends(get_service),
):
    """
    Upload and process an insurance claim document.
    
    - Supports PDF, PNG, JPG, JPEG, TIFF formats
    - Max file size: 10MB
    - Returns immediately with claim_id; processing happens asynchronously
    - Use correlation_id for idempotent resubmission
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Empty file provided")

    try:
        result = await service.submit_claim(
            file_content=content,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            correlation_id=correlation_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Claim submission failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal processing error")


# ─────────────────────────────────────────────
# CLAIM STATUS & RETRIEVAL
# ─────────────────────────────────────────────

@router.get(
    "/claims/{claim_id}",
    response_model=ClaimStatusResponse,
    tags=["Claims"],
    summary="Get claim status and details",
)
async def get_claim(
    claim_id: str,
    service: ClaimsService = Depends(get_service),
):
    """Get the current status, extracted data, fraud score, and decision for a claim."""
    try:
        return await service.get_claim_status(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/claims",
    response_model=ClaimListResponse,
    tags=["Claims"],
    summary="List all claims",
)
async def list_claims(
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    service: ClaimsService = Depends(get_service),
):
    """
    List claims with optional filtering.
    
    Status values: RECEIVED, OCR_PROCESSING, EXTRACTING, VALIDATING, 
    POLICY_CHECK, FRAUD_ANALYSIS, DECISION_PENDING, HITL_REVIEW, 
    APPROVED, REJECTED, INVESTIGATING, ERROR
    """
    if page < 1:
        raise HTTPException(status_code=422, detail="Page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=422, detail="Page size must be 1-100")

    return await service.list_claims(status_filter, page, page_size)


@router.get(
    "/claims/{claim_id}/audit",
    tags=["Claims"],
    summary="Get audit trail for a claim",
)
async def get_audit_trail(
    claim_id: str,
    service: ClaimsService = Depends(get_service),
):
    """Get the complete audit trail showing all events for a claim."""
    try:
        return await service.get_audit_trail(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─────────────────────────────────────────────
# HUMAN-IN-THE-LOOP (HITL)
# ─────────────────────────────────────────────

@router.get(
    "/hitl/pending",
    response_model=ClaimListResponse,
    tags=["HITL Review"],
    summary="Get all claims pending human review",
)
async def get_pending_hitl(service: ClaimsService = Depends(get_service)):
    """Get all claims currently waiting for human review."""
    return await service.get_pending_hitl()


@router.post(
    "/hitl/{claim_id}/review",
    response_model=HITLReviewResponse,
    tags=["HITL Review"],
    summary="Submit a human review decision for a claim",
)
async def submit_hitl_review(
    claim_id: str,
    review: HITLReviewRequest,
    service: ClaimsService = Depends(get_service),
):
    """
    Submit a human reviewer's decision on a claim.
    
    Actions:
    - APPROVE: Approve the claim (optionally with modified amount)
    - REJECT: Reject with required reason
    - INVESTIGATE: Route to investigation team
    - REQUEST_MORE_INFO: Keep in HITL queue, request more info
    """
    try:
        return await service.submit_hitl_review(
            claim_id=claim_id,
            review=review,
            reviewer_id=review.reviewer_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"HITL review failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process review")


# ─────────────────────────────────────────────
# POLICY MANAGEMENT
# ─────────────────────────────────────────────

@router.post(
    "/policies/index",
    tags=["Policy Management"],
    summary="Index a policy document for RAG",
)
async def index_policy(
    request: PolicyIndexRequest,
    service: ClaimsService = Depends(get_service),
):
    """
    Index an insurance policy document into the vector store for RAG.
    
    The indexed policy will be used by the Policy Agent to check claim eligibility.
    Idempotent - same policy content will be deduplicated.
    """
    try:
        return await service.index_policy(request)
    except Exception as e:
        logger.error(f"Policy indexing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Policy indexing failed: {str(e)}")


# ─────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────

@router.get(
    "/analytics/summary",
    tags=["Analytics"],
    summary="Get claims processing analytics",
)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
):
    """Get high-level analytics on claim processing."""
    from sqlalchemy import select, func
    from app.infrastructure.db.models import ClaimDB

    result = await db.execute(
        select(
            ClaimDB.status,
            func.count(ClaimDB.id).label("count"),
            func.avg(ClaimDB.fraud_score).label("avg_fraud_score"),
            func.avg(ClaimDB.claimed_amount).label("avg_claimed_amount"),
        ).group_by(ClaimDB.status)
    )
    rows = result.all()

    return {
        "by_status": [
            {
                "status": row.status,
                "count": row.count,
                "avg_fraud_score": round(row.avg_fraud_score or 0, 3),
                "avg_claimed_amount": round(row.avg_claimed_amount or 0, 2),
            }
            for row in rows
        ]
    }
