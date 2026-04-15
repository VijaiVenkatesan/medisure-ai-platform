"""
Pydantic models for the entire claims processing domain.
These are the canonical data contracts used across all layers.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, model_validator
import re


# ─────────────────────────────────────────────
# ENUMERATIONS
# ─────────────────────────────────────────────

class ClaimStatus(str, Enum):
    RECEIVED = "RECEIVED"
    OCR_PROCESSING = "OCR_PROCESSING"
    EXTRACTING = "EXTRACTING"
    VALIDATING = "VALIDATING"
    POLICY_CHECK = "POLICY_CHECK"
    FRAUD_ANALYSIS = "FRAUD_ANALYSIS"
    DECISION_PENDING = "DECISION_PENDING"
    HITL_REVIEW = "HITL_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    INVESTIGATING = "INVESTIGATING"
    ERROR = "ERROR"


class ClaimDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    INVESTIGATE = "INVESTIGATE"
    PENDING = "PENDING"


class InsuranceType(str, Enum):
    HEALTH = "HEALTH"
    MOTOR = "MOTOR"
    LIFE = "LIFE"
    PROPERTY = "PROPERTY"
    TRAVEL = "TRAVEL"
    CROP = "CROP"         # India-specific
    PRADHAN_MANTRI = "PRADHAN_MANTRI"  # India govt schemes
    AYUSHMAN_BHARAT = "AYUSHMAN_BHARAT"
    OTHER = "OTHER"


class FraudLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Country(str, Enum):
    INDIA = "IN"
    USA = "US"
    UK = "GB"
    UAE = "AE"
    SINGAPORE = "SG"
    OTHER = "OTHER"


class HITLAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    INVESTIGATE = "INVESTIGATE"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"


# ─────────────────────────────────────────────
# DOCUMENT & OCR MODELS
# ─────────────────────────────────────────────

class DocumentUpload(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    claim_id: Optional[str] = None


class OCRResult(BaseModel):
    raw_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    language_detected: str = "en"
    pages: int = 1
    extraction_time_ms: float = 0.0
    engine_used: str = "easyocr"
    error: Optional[str] = None


# ─────────────────────────────────────────────
# EXTRACTED CLAIM DATA
# ─────────────────────────────────────────────

class ClaimantInfo(BaseModel):
    name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    aadhaar_number: Optional[str] = None  # India
    pan_number: Optional[str] = None      # India
    passport_number: Optional[str] = None
    national_id: Optional[str] = None     # Generic

    @field_validator("aadhaar_number", mode="before")
    @classmethod
    def mask_aadhaar(cls, v):
        """Mask Aadhaar for GDPR/DPDP compliance - show only last 4 digits."""
        if v and len(str(v)) == 12:
            return "XXXX-XXXX-" + str(v)[-4:]
        return v


class PolicyInfo(BaseModel):
    policy_number: Optional[str] = None
    insurance_company: Optional[str] = None
    policy_type: Optional[InsuranceType] = None
    policy_start_date: Optional[str] = None
    policy_end_date: Optional[str] = None
    sum_insured: Optional[float] = None
    premium_amount: Optional[float] = None
    currency: str = "INR"


class IncidentInfo(BaseModel):
    incident_date: Optional[str] = None
    incident_location: Optional[str] = None
    incident_description: Optional[str] = None
    reported_date: Optional[str] = None
    hospital_name: Optional[str] = None      # Health claims
    doctor_name: Optional[str] = None        # Health claims
    diagnosis: Optional[str] = None          # Health claims
    vehicle_number: Optional[str] = None     # Motor claims
    accident_description: Optional[str] = None  # Motor claims
    damaged_items: Optional[list[str]] = None   # Property claims
    treatment_details: Optional[str] = None


class ClaimAmounts(BaseModel):
    claimed_amount: Optional[float] = None
    currency: str = "INR"
    breakdown: Optional[dict[str, float]] = None
    supporting_invoices: Optional[list[str]] = None


class ExtractedClaimData(BaseModel):
    claimant: ClaimantInfo = Field(default_factory=ClaimantInfo)
    policy: PolicyInfo = Field(default_factory=PolicyInfo)
    incident: IncidentInfo = Field(default_factory=IncidentInfo)
    amounts: ClaimAmounts = Field(default_factory=ClaimAmounts)
    country: Country = Country.INDIA
    raw_ocr_text: Optional[str] = None
    extraction_confidence: float = 0.0
    extraction_notes: Optional[str] = None


# ─────────────────────────────────────────────
# AGENT OUTPUTS
# ─────────────────────────────────────────────

class ValidationError(BaseModel):
    field: str
    error: str
    severity: str = "ERROR"  # ERROR | WARNING


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    completeness_score: float = Field(ge=0.0, le=1.0, default=0.0)
    rules_applied: list[str] = []


class PolicyEligibilityResult(BaseModel):
    is_eligible: bool
    eligibility_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reason: str = ""
    policy_clauses_matched: list[str] = []
    exclusions_triggered: list[str] = []
    retrieved_context: list[str] = []
    coverage_details: Optional[dict[str, Any]] = None


class FraudIndicator(BaseModel):
    indicator: str
    weight: float
    description: str


class FraudAnalysisResult(BaseModel):
    fraud_score: float = Field(ge=0.0, le=1.0)
    fraud_level: FraudLevel
    indicators: list[FraudIndicator] = []
    anomalies_detected: list[str] = []
    risk_factors: list[str] = []
    analysis_notes: str = ""


class DecisionResult(BaseModel):
    decision: ClaimDecision
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    approved_amount: Optional[float] = None
    rejection_reasons: list[str] = []
    conditions: list[str] = []
    requires_hitl: bool = False
    decision_factors: dict[str, Any] = {}


# ─────────────────────────────────────────────
# WORKFLOW STATE (LangGraph central state)
# ─────────────────────────────────────────────

class WorkflowState(BaseModel):
    """Central state object passed across all LangGraph nodes."""
    claim_id: str
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    status: ClaimStatus = ClaimStatus.RECEIVED
    document_path: Optional[str] = None
    document_id: Optional[str] = None

    # Agent outputs
    ocr_result: Optional[OCRResult] = None
    extracted_data: Optional[ExtractedClaimData] = None
    validation_result: Optional[ValidationResult] = None
    policy_result: Optional[PolicyEligibilityResult] = None
    fraud_result: Optional[FraudAnalysisResult] = None
    decision_result: Optional[DecisionResult] = None

    # Control flow
    should_skip_downstream: bool = False
    retry_count: int = 0
    max_retries: int = 3
    errors: list[str] = []
    warnings: list[str] = []

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True


# ─────────────────────────────────────────────
# API REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────

class ClaimSubmitResponse(BaseModel):
    claim_id: str
    status: ClaimStatus
    message: str
    correlation_id: str


class ClaimStatusResponse(BaseModel):
    claim_id: str
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime
    extracted_data: Optional[ExtractedClaimData] = None
    fraud_score: Optional[float] = None
    fraud_level: Optional[str] = None
    decision: Optional[str] = None
    decision_confidence: Optional[float] = None
    explanation: Optional[str] = None
    errors: list[str] = []


class ClaimListItem(BaseModel):
    claim_id: str
    status: ClaimStatus
    policy_type: Optional[str] = None
    claimed_amount: Optional[float] = None
    currency: str = "INR"
    fraud_score: Optional[float] = None
    decision: Optional[str] = None
    created_at: datetime
    claimant_name: Optional[str] = None


class ClaimListResponse(BaseModel):
    claims: list[ClaimListItem]
    total: int
    page: int
    page_size: int


class HITLReviewRequest(BaseModel):
    action: HITLAction
    reviewer_id: str
    reviewer_notes: str = ""
    approved_amount: Optional[float] = None
    rejection_reason: Optional[str] = None


class HITLReviewResponse(BaseModel):
    claim_id: str
    action: HITLAction
    reviewer_id: str
    reviewed_at: datetime
    new_status: ClaimStatus
    message: str


class PolicyIndexRequest(BaseModel):
    policy_text: str
    policy_name: str
    insurance_type: InsuranceType
    country: Country = Country.INDIA
    company: Optional[str] = None
    effective_date: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]
    timestamp: datetime


class AuditLogEntry(BaseModel):
    id: str
    claim_id: str
    event_type: str
    actor: str
    details: dict[str, Any]
    timestamp: datetime
