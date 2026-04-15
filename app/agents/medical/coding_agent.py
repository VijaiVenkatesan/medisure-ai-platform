"""
Medical Coding Agent — Phase 2
Auto-assigns ICD-10, CPT, and SNOMED codes from clinical text.
Supports India (ABDM ICD-10), USA (ICD-10-CM + CPT), UK (ICD-10).
"""
from __future__ import annotations
from app.infrastructure.llm.groq_client import get_groq_client
from app.core.logging import get_logger

logger = get_logger(__name__)

CODING_SYSTEM = """You are a Certified Professional Coder (CPC) and Certified Coding Specialist (CCS) 
with expertise in Indian ABDM coding standards, ICD-10-CM, CPT, and SNOMED CT.
Assign the most specific and accurate codes possible.
Always explain your coding rationale.
Return valid JSON only."""

CODING_SCHEMA = """{
  "primary_diagnosis": {
    "description": "diagnosis text",
    "icd10_code": "code",
    "icd10_description": "official description",
    "specificity": "explanation of why this specific code",
    "confidence": 0.0
  },
  "secondary_diagnoses": [
    {"description": "text", "icd10_code": "code", "confidence": 0.0}
  ],
  "procedures": [
    {
      "description": "procedure text",
      "cpt_code": "CPT code (USA) or null",
      "icd10_pcs": "ICD-10-PCS code or null",
      "confidence": 0.0
    }
  ],
  "drg": "Diagnosis Related Group code if determinable",
  "coding_notes": "any ambiguities or assumptions made",
  "query_flags": ["items needing physician clarification"],
  "overall_confidence": 0.0
}"""


async def code_medical_document(
    clinical_text: str,
    country: str = "IN",
    include_cpt: bool = False
) -> dict:
    """
    Auto-code a clinical document.
    
    Args:
        clinical_text: Raw or summarized clinical text
        country: IN (India), US (USA), GB (UK), etc.
        include_cpt: Include CPT codes (USA only)
    """
    if not clinical_text or len(clinical_text.strip()) < 20:
        return {"error": "Insufficient clinical text for coding"}

    llm = get_groq_client()

    country_guidance = {
        "IN": "Use ICD-10 as per ABDM/NHA guidelines. India uses ICD-10 (not ICD-10-CM).",
        "US": "Use ICD-10-CM for diagnoses and CPT codes for procedures.",
        "GB": "Use ICD-10 (NHS version). Follow SNOMED CT for clinical terms.",
        "AE": "Use ICD-10 per UAE MOH guidelines.",
        "SG": "Use ICD-10 per MOH Singapore guidelines.",
    }.get(country, "Use standard ICD-10 codes.")

    prompt = f"""Assign medical codes to this clinical documentation.

COUNTRY/CODING SYSTEM: {country} — {country_guidance}

CLINICAL TEXT:
{clinical_text[:5000]}

Instructions:
1. Assign the most specific ICD-10 code available (4th/5th character specificity)
2. Code all documented diagnoses, not just the primary
3. Code complications and comorbidities separately
4. For India: follow ABDM ICD-10 coding guidelines
5. Note any physician query flags (unclear documentation)

Return JSON matching:
{CODING_SCHEMA}"""

    try:
        result = await llm.extract_json(
            prompt=prompt,
            system_prompt=CODING_SYSTEM,
            model="llama-3.3-70b-versatile"
        )
        logger.info("Medical coding complete",
                    extra={"extra_data": {
                        "primary": result.get("primary_diagnosis", {}).get("icd10_code"),
                        "confidence": result.get("overall_confidence")
                    }})
        return result
    except Exception as e:
        logger.error(f"Coding failed: {e}")
        return {"error": str(e)}
