"""
Extraction Agent: Converts raw OCR text into structured claim data using LLM.
Enforces strict JSON schema output with validation fallbacks.
"""
from __future__ import annotations
import json
from app.infrastructure.llm.groq_client import get_groq_client
from app.models.schemas import (
    WorkflowState, ClaimStatus, ExtractedClaimData,
    ClaimantInfo, PolicyInfo, IncidentInfo, ClaimAmounts,
    InsuranceType, Country
)
from app.core.logging import get_logger, log_agent_start, log_agent_complete, log_agent_error

logger = get_logger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are an expert insurance claim data extraction specialist with deep knowledge of:
- Indian insurance policies (LIC, IRDAI regulations, Ayushman Bharat, PM-JAY, PMFBY)
- International insurance (US, UK, UAE, Singapore)
- Medical insurance terminology (Hindi and English)
- Motor, health, life, property, crop insurance documents

Your task is to extract structured information from OCR text of insurance claim documents.
You MUST handle:
- Hindi/English mixed documents
- Damaged or partially readable text  
- Aadhaar numbers (mask to XXXX-XXXX-XXXX format)
- Indian formats: DD/MM/YYYY dates, INR amounts, CIN/IRDA numbers

Return ONLY a valid JSON object with no markdown or explanation."""

EXTRACTION_SCHEMA = """
{
  "claimant": {
    "name": "string or null",
    "dob": "DD/MM/YYYY or null",
    "gender": "MALE|FEMALE|OTHER or null",
    "contact_number": "string or null",
    "email": "string or null",
    "address": "string or null",
    "aadhaar_number": "last 4 digits only or null",
    "pan_number": "string or null",
    "national_id": "string or null"
  },
  "policy": {
    "policy_number": "string or null",
    "insurance_company": "string or null",
    "policy_type": "HEALTH|MOTOR|LIFE|PROPERTY|TRAVEL|CROP|PRADHAN_MANTRI|AYUSHMAN_BHARAT|OTHER",
    "policy_start_date": "DD/MM/YYYY or null",
    "policy_end_date": "DD/MM/YYYY or null",
    "sum_insured": "number or null",
    "premium_amount": "number or null",
    "currency": "INR|USD|GBP|AED|SGD"
  },
  "incident": {
    "incident_date": "DD/MM/YYYY or null",
    "incident_location": "string or null",
    "incident_description": "string or null",
    "reported_date": "DD/MM/YYYY or null",
    "hospital_name": "string or null",
    "doctor_name": "string or null",
    "diagnosis": "string or null",
    "vehicle_number": "string or null",
    "treatment_details": "string or null"
  },
  "amounts": {
    "claimed_amount": "number or null",
    "currency": "INR|USD|GBP",
    "breakdown": {"item_name": "amount"} or null
  },
  "country": "IN|US|GB|AE|SG|OTHER",
  "extraction_confidence": "0.0-1.0",
  "extraction_notes": "any observations about document quality or missing data"
}"""


async def extraction_agent(state: WorkflowState) -> WorkflowState:
    """
    LangGraph node: Extract structured data from OCR text using LLM.
    Validates and normalizes the output before returning.
    """
    log_agent_start(logger, "ExtractionAgent", state.claim_id)
    state.status = ClaimStatus.EXTRACTING

    if not state.ocr_result or not state.ocr_result.raw_text.strip():
        error_msg = "No OCR text available for extraction"
        state.errors.append(error_msg)
        logger.error(error_msg, extra={"extra_data": {"claim_id": state.claim_id}})
        state.extracted_data = ExtractedClaimData()
        return state

    try:
        llm = get_groq_client()

        prompt = f"""Extract all insurance claim information from this document text.

DOCUMENT TEXT:
{state.ocr_result.raw_text[:8000]}

OCR Confidence: {state.ocr_result.confidence:.2f}
Language Detected: {state.ocr_result.language_detected}

EXTRACTION SCHEMA:
{EXTRACTION_SCHEMA}

Extract every piece of relevant information. If a field is not present, use null.
For Indian documents, look for: Aadhaar, PAN, policy number formats like LIC/###/###,
claim reference numbers, hospital registration numbers, CGHS/ECHS indicators.
For amounts in Indian documents: look for ₹, Rs., INR, Rupees."""

        raw_data = await llm.extract_json(
            prompt=prompt,
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
        )

        # Build structured extraction result
        extracted = _build_extracted_data(raw_data, state.ocr_result.raw_text)
        state.extracted_data = extracted

        log_agent_complete(
            logger, "ExtractionAgent", state.claim_id,
            {
                "policy_type": str(extracted.policy.policy_type),
                "claimant": extracted.claimant.name,
                "amount": extracted.amounts.claimed_amount,
                "confidence": extracted.extraction_confidence,
            }
        )

    except Exception as e:
        log_agent_error(logger, "ExtractionAgent", state.claim_id, e)
        state.errors.append(f"Extraction failed: {str(e)}")
        state.extracted_data = ExtractedClaimData(
            raw_ocr_text=state.ocr_result.raw_text if state.ocr_result else None,
            extraction_confidence=0.1,
            extraction_notes=f"Extraction error: {str(e)}",
        )

    return state


def _build_extracted_data(raw: dict, ocr_text: str) -> ExtractedClaimData:
    """Build and validate ExtractedClaimData from raw LLM output."""

    def safe_float(v) -> float | None:
        try:
            if v is None:
                return None
            # Handle Indian number formats: "1,50,000" -> 150000
            cleaned = str(v).replace(",", "").replace("₹", "").replace("Rs.", "").strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def safe_str(v) -> str | None:
        return str(v).strip() if v and str(v).strip() not in ["null", "None", ""] else None

    # Claimant
    claimant_raw = raw.get("claimant", {}) or {}
    claimant = ClaimantInfo(
        name=safe_str(claimant_raw.get("name")),
        dob=safe_str(claimant_raw.get("dob")),
        gender=safe_str(claimant_raw.get("gender")),
        contact_number=safe_str(claimant_raw.get("contact_number")),
        email=safe_str(claimant_raw.get("email")),
        address=safe_str(claimant_raw.get("address")),
        aadhaar_number=safe_str(claimant_raw.get("aadhaar_number")),
        pan_number=safe_str(claimant_raw.get("pan_number")),
        national_id=safe_str(claimant_raw.get("national_id")),
    )

    # Policy
    policy_raw = raw.get("policy", {}) or {}
    policy_type_str = policy_raw.get("policy_type", "OTHER")
    try:
        policy_type = InsuranceType(policy_type_str)
    except ValueError:
        policy_type = InsuranceType.OTHER

    policy = PolicyInfo(
        policy_number=safe_str(policy_raw.get("policy_number")),
        insurance_company=safe_str(policy_raw.get("insurance_company")),
        policy_type=policy_type,
        policy_start_date=safe_str(policy_raw.get("policy_start_date")),
        policy_end_date=safe_str(policy_raw.get("policy_end_date")),
        sum_insured=safe_float(policy_raw.get("sum_insured")),
        premium_amount=safe_float(policy_raw.get("premium_amount")),
        currency=safe_str(policy_raw.get("currency")) or "INR",
    )

    # Incident
    incident_raw = raw.get("incident", {}) or {}
    incident = IncidentInfo(
        incident_date=safe_str(incident_raw.get("incident_date")),
        incident_location=safe_str(incident_raw.get("incident_location")),
        incident_description=safe_str(incident_raw.get("incident_description")),
        reported_date=safe_str(incident_raw.get("reported_date")),
        hospital_name=safe_str(incident_raw.get("hospital_name")),
        doctor_name=safe_str(incident_raw.get("doctor_name")),
        diagnosis=safe_str(incident_raw.get("diagnosis")),
        vehicle_number=safe_str(incident_raw.get("vehicle_number")),
        treatment_details=safe_str(incident_raw.get("treatment_details")),
    )

    # Amounts
    amounts_raw = raw.get("amounts", {}) or {}
    breakdown = amounts_raw.get("breakdown")
    if breakdown and isinstance(breakdown, dict):
        breakdown = {k: safe_float(v) for k, v in breakdown.items() if safe_float(v) is not None}
    else:
        breakdown = None

    amounts = ClaimAmounts(
        claimed_amount=safe_float(amounts_raw.get("claimed_amount")),
        currency=safe_str(amounts_raw.get("currency")) or "INR",
        breakdown=breakdown,
    )

    # Country
    country_str = raw.get("country", "IN")
    try:
        country = Country(country_str)
    except ValueError:
        country = Country.INDIA

    confidence = raw.get("extraction_confidence", 0.7)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.7

    return ExtractedClaimData(
        claimant=claimant,
        policy=policy,
        incident=incident,
        amounts=amounts,
        country=country,
        raw_ocr_text=ocr_text[:5000],
        extraction_confidence=min(1.0, max(0.0, confidence)),
        extraction_notes=safe_str(raw.get("extraction_notes")),
    )
