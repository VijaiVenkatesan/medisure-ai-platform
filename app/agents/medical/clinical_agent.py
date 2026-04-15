"""
Clinical Decision Support Agent — Phase 3
Evidence-based clinical assistance for diagnosis, drug interactions,
and patient risk stratification.

IMPORTANT: This is decision SUPPORT only — not a replacement for
clinical judgment. Always defers to licensed medical professionals.

India focus: Tropical diseases, ICMR guidelines, ABDM integration.
"""
from __future__ import annotations
from typing import Optional
from app.infrastructure.llm.groq_client import get_groq_client
from app.core.logging import get_logger

logger = get_logger(__name__)

CDS_SYSTEM = """You are a clinical decision support system with knowledge of:
- Indian clinical guidelines (ICMR, NMC, MCI standards)
- WHO International guidelines
- Tropical medicine (diseases endemic to South/Southeast Asia)
- Evidence-based medicine (Cochrane, BMJ, NEJM evidence levels)

CRITICAL DISCLAIMER: This is decision SUPPORT only.
Always state: "This is AI-generated decision support. Clinical judgment of a licensed physician is required."
Never diagnose definitively. Use probabilistic language: "suggests", "consistent with", "consider".
Flag emergency conditions immediately.
Return valid JSON only."""

DIAGNOSIS_SCHEMA = """{
  "disclaimer": "This is AI-generated decision support. Clinical judgment of a licensed physician is required.",
  "chief_complaint": "primary complaint in one line",
  "red_flags": ["emergency/urgent findings requiring immediate attention"],
  "differential_diagnoses": [
    {
      "diagnosis": "condition name",
      "icd10_code": "code",
      "probability": "HIGH|MODERATE|LOW",
      "probability_percent": "estimated %",
      "supporting_features": ["features supporting this diagnosis"],
      "against_features": ["features arguing against"],
      "recommended_investigations": ["tests to confirm/rule out"],
      "india_specific": "India-specific considerations (tropical diseases, nutrition, etc.)"
    }
  ],
  "immediate_actions": ["urgent steps if red flags present"],
  "recommended_investigations": {
    "urgent": ["tests needed within hours"],
    "routine": ["tests needed within days"],
    "specialist_referral": ["referrals needed"]
  },
  "initial_management": {
    "non_pharmacological": ["lifestyle, diet, monitoring advice"],
    "pharmacological": ["first-line medications per guidelines"],
    "guidelines_followed": ["ICMR/WHO/NICE guideline references"]
  },
  "follow_up": "recommended follow-up timeline",
  "patient_education": ["key points to explain to patient"],
  "confidence": "0.0-1.0"
}"""

DRUG_INTERACTION_SCHEMA = """{
  "medications_analyzed": ["list of drugs checked"],
  "interactions": [
    {
      "drug_1": "drug name",
      "drug_2": "drug name",
      "severity": "CONTRAINDICATED|MAJOR|MODERATE|MINOR",
      "mechanism": "pharmacodynamic or pharmacokinetic interaction",
      "clinical_effect": "what happens clinically",
      "management": "how to manage this interaction",
      "alternative": "safer alternative if available"
    }
  ],
  "food_interactions": [
    {
      "drug": "drug name",
      "food_item": "food",
      "effect": "clinical effect",
      "advice": "patient advice"
    }
  ],
  "condition_interactions": [
    {
      "drug": "drug name",
      "condition": "medical condition",
      "risk": "risk description",
      "advice": "monitoring or adjustment needed"
    }
  ],
  "age_considerations": ["dose adjustments for age if applicable"],
  "renal_considerations": ["adjustments for kidney disease if applicable"],
  "hepatic_considerations": ["adjustments for liver disease if applicable"],
  "overall_safety": "SAFE|CAUTION_NEEDED|REVIEW_REQUIRED|CONTRAINDICATED",
  "summary": "plain language summary for prescriber",
  "confidence": "0.0-1.0"
}"""


async def clinical_diagnosis_support(
    symptoms: list[str],
    patient_age: int,
    patient_gender: str,
    duration: str = "",
    vitals: Optional[dict] = None,
    lab_results: Optional[str] = None,
    medical_history: Optional[str] = None,
    country: str = "IN",
) -> dict:
    """
    Generate differential diagnoses from clinical presentation.
    India-first: considers tropical diseases, nutritional deficiencies.
    """
    llm = get_groq_client()

    country_note = {
        "IN": "India — consider: TB, Dengue, Malaria, Typhoid, Leptospirosis, Vitamin D/B12 deficiency, Diabetes complications",
        "US": "USA — consider: Lyme disease, influenza, community-acquired infections",
        "GB": "UK — consider: NICE guidelines, NHS referral pathways",
    }.get(country, "International presentation")

    vitals_str = ""
    if vitals:
        vitals_str = f"\nVITALS: {', '.join(f'{k}: {v}' for k, v in vitals.items() if v)}"

    prompt = f"""Generate differential diagnoses for this clinical presentation.

PATIENT: {patient_age}yr {patient_gender}
COUNTRY: {country_note}
SYMPTOMS: {', '.join(symptoms)}
DURATION: {duration or 'Not specified'}
{vitals_str}
{f'LAB RESULTS: {lab_results}' if lab_results else ''}
{f'MEDICAL HISTORY: {medical_history}' if medical_history else ''}

Instructions:
1. List RED FLAGS first — any emergency/urgent conditions
2. Generate top 5 differential diagnoses in order of probability
3. For India: ALWAYS consider tropical diseases if fever/constitutional symptoms
4. Recommend minimum investigations needed (cost-effective for India)
5. First-line treatment per ICMR/WHO guidelines
6. Use ICD-10 codes for all diagnoses
7. Flag if specialist/emergency referral needed

Return complete JSON:
{DIAGNOSIS_SCHEMA}"""

    try:
        result = await llm.extract_json(
            prompt=prompt,
            system_prompt=CDS_SYSTEM,
            model="llama-3.3-70b-versatile"
        )
        logger.info("Clinical diagnosis support generated",
                    extra={"extra_data": {
                        "diagnoses": len(result.get("differential_diagnoses", [])),
                        "red_flags": len(result.get("red_flags", [])),
                    }})
        return result
    except Exception as e:
        logger.error(f"Clinical decision support failed: {e}")
        return {"error": str(e), "disclaimer": "AI error — consult physician directly"}


async def check_drug_interactions(
    medications: list[str],
    patient_age: int = 40,
    conditions: Optional[list[str]] = None,
    renal_function: Optional[str] = None,
    hepatic_function: Optional[str] = None,
) -> dict:
    """
    Check drug-drug, drug-food, and drug-condition interactions.
    Uses LLM with pharmacology knowledge base.
    """
    if len(medications) < 1:
        return {"error": "At least one medication required"}

    llm = get_groq_client()

    prompt = f"""Perform a comprehensive drug interaction check.

MEDICATIONS: {', '.join(medications)}
PATIENT AGE: {patient_age} years
{f'CONDITIONS: {", ".join(conditions)}' if conditions else ''}
{f'RENAL FUNCTION: {renal_function}' if renal_function else ''}
{f'HEPATIC FUNCTION: {hepatic_function}' if hepatic_function else ''}

Check for:
1. Drug-drug interactions (all combinations)
2. Drug-food interactions (especially Indian diet: dairy, spices, grapefruit)
3. Drug-disease contraindications
4. Age-appropriate dosing (pediatric/geriatric adjustments)
5. Renal/hepatic dose adjustments if applicable
6. Indian generic equivalents where relevant

Severity levels:
- CONTRAINDICATED: Never use together
- MAJOR: Potentially life-threatening, avoid if possible
- MODERATE: Use with caution and monitoring
- MINOR: Minor clinical significance

Return complete JSON:
{DRUG_INTERACTION_SCHEMA}"""

    try:
        result = await llm.extract_json(
            prompt=prompt,
            system_prompt=CDS_SYSTEM,
            model="llama-3.3-70b-versatile"
        )
        logger.info("Drug interaction check complete",
                    extra={"extra_data": {
                        "drugs": len(medications),
                        "interactions": len(result.get("interactions", [])),
                        "safety": result.get("overall_safety"),
                    }})
        return result
    except Exception as e:
        logger.error(f"Drug interaction check failed: {e}")
        return {"error": str(e)}


async def patient_risk_stratification(
    patient_data: dict,
    risk_type: str = "CARDIOVASCULAR",
) -> dict:
    """
    Stratify patient risk for disease prevention and insurance.

    risk_type options:
    - CARDIOVASCULAR: Framingham/WHO CVD risk score
    - DIABETES: Diabetes risk score (ADA/ICMR)
    - CANCER: General cancer risk factors
    - READMISSION: Hospital readmission risk
    """
    llm = get_groq_client()

    RISK_SCHEMA = """{
      "risk_type": "type of risk assessed",
      "risk_score": "0-100 or standard risk score value",
      "risk_category": "LOW|MODERATE|HIGH|VERY_HIGH",
      "10_year_risk_percent": "estimated 10-year risk percentage",
      "modifiable_risk_factors": [{"factor": "name", "current_value": "value", "target": "target value", "intervention": "what to do"}],
      "non_modifiable_risk_factors": ["age", "family history", etc],
      "recommended_interventions": [{"intervention": "name", "evidence_level": "A|B|C", "expected_benefit": "description"}],
      "screening_recommendations": ["screening tests and frequency"],
      "lifestyle_modifications": ["specific actionable lifestyle changes"],
      "pharmacotherapy_threshold": "when to start medications based on risk",
      "follow_up_frequency": "monitoring schedule",
      "india_specific_notes": "India-specific risk factors and guidelines",
      "confidence": "0.0-1.0"
    }"""

    prompt = f"""Perform {risk_type} risk stratification for this patient.

PATIENT DATA: {patient_data}

Follow:
- India: ICMR/CSI guidelines for cardiovascular risk
- WHO/ISH risk charts for low-resource settings
- ADA/RSSDI guidelines for diabetes risk (India has highest T2DM burden)
- Provide specific, actionable interventions

Return JSON:
{RISK_SCHEMA}"""

    try:
        result = await llm.extract_json(
            prompt=prompt,
            system_prompt=CDS_SYSTEM,
            model="llama-3.3-70b-versatile"
        )
        return result
    except Exception as e:
        return {"error": str(e)}
