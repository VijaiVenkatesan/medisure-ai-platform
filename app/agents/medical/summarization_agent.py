"""
Medical Summarization Agent — Phase 2
Converts raw medical document text into structured clinical summary.
Supports: discharge summaries, OPD notes, lab reports, prescriptions.
India-first: ABDM FHIR R4 compatible output.
"""
from __future__ import annotations
from app.infrastructure.llm.groq_client import get_groq_client
from app.core.logging import get_logger

logger = get_logger(__name__)

SUMMARY_SYSTEM = """You are a senior medical officer and clinical documentation specialist 
with expertise in Indian healthcare (ABDM, NMC guidelines) and international standards (WHO, HL7 FHIR).
Extract and structure ALL clinically relevant information accurately.
Never hallucinate medical data — only extract what is explicitly stated.
Return valid JSON only."""

SUMMARY_SCHEMA = """{
  "document_type": "DISCHARGE_SUMMARY|OPD_NOTE|LAB_REPORT|PRESCRIPTION|RADIOLOGY|OTHER",
  "patient": {
    "name": "string or null",
    "age": "string or null",
    "gender": "MALE|FEMALE|OTHER|null",
    "abha_number": "string or null",
    "uhid": "string or null"
  },
  "facility": {
    "hospital_name": "string or null",
    "doctor_name": "string or null",
    "department": "string or null",
    "date": "string or null"
  },
  "chief_complaint": "primary reason for visit in one sentence",
  "diagnoses": [
    {
      "description": "diagnosis text",
      "icd10_code": "ICD-10 code if determinable",
      "type": "PRIMARY|SECONDARY|COMORBIDITY"
    }
  ],
  "vitals": {
    "bp": "string or null",
    "pulse": "string or null",
    "temperature": "string or null",
    "spo2": "string or null",
    "weight": "string or null",
    "height": "string or null"
  },
  "key_findings": ["list of significant clinical findings"],
  "lab_results": [
    {"test": "name", "value": "result", "unit": "unit", "flag": "HIGH|LOW|NORMAL|null"}
  ],
  "medications": [
    {"drug": "name", "dose": "dosage", "frequency": "timing", "duration": "days/months", "route": "oral/IV/etc"}
  ],
  "procedures": ["list of procedures performed"],
  "allergies": ["list or empty"],
  "treatment_summary": "brief paragraph of treatment given",
  "follow_up": "follow-up instructions",
  "red_flags": ["urgent findings requiring immediate attention"],
  "summary_paragraph": "2-3 sentence clinical summary for non-specialist",
  "confidence": 0.0
}"""


async def summarize_medical_document(
    ocr_text: str,
    doc_type_hint: str = "auto"
) -> dict:
    """
    Summarize a medical document from OCR text.
    Returns structured clinical summary.
    """
    if not ocr_text or len(ocr_text.strip()) < 20:
        return {"error": "Insufficient text to summarize", "confidence": 0.0}

    llm = get_groq_client()

    prompt = f"""Analyze this medical document and extract all clinical information.

DOCUMENT TEXT:
{ocr_text[:6000]}

DOCUMENT TYPE HINT: {doc_type_hint}

Return complete JSON matching this schema:
{SUMMARY_SCHEMA}

Important rules:
- For Indian documents: look for ABHA number, UHID, registration numbers
- Extract ALL medications with complete dosage information
- Flag any critical/emergency findings in red_flags
- ICD-10 codes: use ICD-10-CM format (e.g., J18.9 for pneumonia)
- If lab values are abnormal, mark flag as HIGH or LOW"""

    try:
        result = await llm.extract_json(
            prompt=prompt,
            system_prompt=SUMMARY_SYSTEM,
            model="llama-3.3-70b-versatile"
        )
        logger.info("Medical summarization complete",
                    extra={"extra_data": {"diagnoses": len(result.get("diagnoses", []))}})
        return result
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return {"error": str(e), "confidence": 0.0}
