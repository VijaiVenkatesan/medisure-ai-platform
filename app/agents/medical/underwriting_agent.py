"""
Medical Underwriting Agent — Module 3
AI-powered insurance underwriting that assesses applicant health risk,
recommends premium loading, exclusions, and policy terms.

Supports:
- Life insurance underwriting (LIC, Max Life, HDFC Life)
- Health insurance underwriting (IRDAI guidelines)
- Critical illness underwriting
- International standards (USA, UK, UAE)
"""
from __future__ import annotations
from typing import Optional
from app.infrastructure.llm.groq_client import get_groq_client
from app.core.logging import get_logger

logger = get_logger(__name__)

UNDERWRITING_SYSTEM = """You are a Senior Medical Underwriter with 20+ years of experience
at leading insurance companies in India (LIC, Star Health, HDFC Life) and international markets.

You assess applicant health risk based on medical reports, BMI, age, lifestyle, and pre-existing conditions.
You follow:
- IRDAI underwriting guidelines for Indian policies
- ABI (Association of British Insurers) guidelines for UK
- NAIC guidelines for USA
- Standard reinsurance mortality tables

Always provide evidence-based decisions with specific medical rationale.
Never discriminate unlawfully. Follow applicable regulations.
Return valid JSON only."""

UNDERWRITING_SCHEMA = """{
  "applicant_summary": {
    "age": "number",
    "gender": "MALE|FEMALE|OTHER",
    "bmi": "number or null",
    "bmi_category": "UNDERWEIGHT|NORMAL|OVERWEIGHT|OBESE|null",
    "smoking_status": "NON_SMOKER|SMOKER|EX_SMOKER|null",
    "occupation_risk": "LOW|MEDIUM|HIGH|VERY_HIGH"
  },
  "medical_findings": [
    {
      "condition": "medical condition name",
      "icd10_code": "ICD-10 code",
      "severity": "MILD|MODERATE|SEVERE",
      "controlled": true,
      "risk_impact": "LOW|MODERATE|HIGH|DECLINE",
      "notes": "clinical notes"
    }
  ],
  "risk_assessment": {
    "mortality_risk": "STANDARD|SUBSTANDARD|PREFERRED|DECLINE",
    "morbidity_risk": "STANDARD|SUBSTANDARD|PREFERRED|DECLINE",
    "overall_risk_class": "PREFERRED|STANDARD|SUBSTANDARD_1|SUBSTANDARD_2|SUBSTANDARD_3|DECLINE",
    "risk_score": "0-1000 (Standard = 100, higher = worse)",
    "risk_narrative": "paragraph explaining the risk assessment"
  },
  "underwriting_decision": {
    "decision": "ACCEPT_STANDARD|ACCEPT_WITH_LOADING|ACCEPT_WITH_EXCLUSION|POSTPONE|DECLINE",
    "confidence": "0.0-1.0",
    "premium_loading_percent": "0 for standard, e.g. 25 for 25% extra premium",
    "policy_term_restriction": "e.g. max 10 years or null",
    "sum_assured_restriction": "max amount or null",
    "waiting_period_months": "0-24",
    "reasons": ["list of specific reasons for decision"]
  },
  "exclusions": [
    {
      "condition": "excluded condition",
      "exclusion_type": "SPECIFIC|GENERAL",
      "duration": "PERMANENT|TEMPORARY|null",
      "review_after_years": "number or null"
    }
  ],
  "recommendations": [
    "list of recommendations for improving insurability"
  ],
  "additional_requirements": [
    "list of additional medical tests or documents required before final decision"
  ],
  "india_specific": {
    "irdai_compliance": "COMPLIANT|REVIEW_NEEDED",
    "ayushman_bharat_eligible": true,
    "pmjay_eligible": true,
    "notes": "India-specific regulatory notes"
  },
  "country": "IN|US|GB|AE",
  "overall_confidence": "0.0-1.0"
}"""


async def underwrite_applicant(
    medical_summary: str,
    age: int,
    gender: str,
    insurance_type: str = "HEALTH",
    sum_assured: Optional[float] = None,
    policy_term_years: Optional[int] = None,
    country: str = "IN",
    additional_context: Optional[str] = None,
) -> dict:
    """
    Perform AI-powered medical underwriting for an insurance applicant.

    Args:
        medical_summary: Medical history, reports, test results as text
        age: Applicant age
        gender: MALE / FEMALE / OTHER
        insurance_type: HEALTH / LIFE / CRITICAL_ILLNESS / DISABILITY
        sum_assured: Proposed sum assured in INR/USD
        policy_term_years: Proposed policy term
        country: Country for regulatory compliance
        additional_context: BMI, occupation, lifestyle, family history

    Returns:
        Structured underwriting decision with risk class, loading, exclusions
    """
    if not medical_summary.strip():
        return {"error": "Medical summary required for underwriting"}

    llm = get_groq_client()

    country_context = {
        "IN": "India — follow IRDAI guidelines, IRDA Act 1999, and standard Indian reinsurance tables",
        "US": "USA — follow NAIC guidelines, HIPAA, and standard US mortality tables",
        "GB": "UK — follow ABI guidelines, FCA regulations, and UK standard mortality tables",
        "AE": "UAE — follow UAE Insurance Authority guidelines",
    }.get(country, "Follow international standard underwriting guidelines")

    insurance_context = {
        "HEALTH": "Health insurance underwriting — focus on morbidity risk, pre-existing conditions, chronic diseases",
        "LIFE": "Life insurance underwriting — focus on mortality risk, critical illness probability, longevity",
        "CRITICAL_ILLNESS": "Critical illness underwriting — assess probability of cancer, heart attack, stroke, kidney failure",
        "DISABILITY": "Disability/income protection underwriting — assess occupation risk and injury/illness probability",
    }.get(insurance_type, "General insurance underwriting")

    prompt = f"""Perform complete medical underwriting for this insurance applicant.

APPLICANT DETAILS:
Age: {age} years
Gender: {gender}
Insurance Type: {insurance_type}
Sum Assured: {f'₹{sum_assured:,.0f}' if sum_assured else 'Not specified'}
Policy Term: {f'{policy_term_years} years' if policy_term_years else 'Not specified'}
Country: {country} — {country_context}

INSURANCE CONTEXT: {insurance_context}

MEDICAL HISTORY & REPORTS:
{medical_summary[:5000]}

{f'ADDITIONAL CONTEXT: {additional_context}' if additional_context else ''}

UNDERWRITING INSTRUCTIONS:
1. Identify ALL medical conditions with their ICD-10 codes
2. Assess mortality AND morbidity risk separately
3. Assign risk class: Preferred/Standard/Substandard 1-3/Decline
4. Calculate premium loading percentage (0% = standard rate)
5. List ALL specific exclusions with durations
6. For India: check IRDAI guidelines, Ayushman Bharat eligibility
7. List any additional requirements (ECG, stress test, specialist reports)
8. Provide actionable recommendations to improve insurability

Return complete JSON matching this schema:
{UNDERWRITING_SCHEMA}"""

    try:
        result = await llm.extract_json(
            prompt=prompt,
            system_prompt=UNDERWRITING_SYSTEM,
            model="llama-3.3-70b-versatile"
        )
        logger.info(
            "Medical underwriting complete",
            extra={"extra_data": {
                "decision": result.get("underwriting_decision", {}).get("decision"),
                "risk_class": result.get("risk_assessment", {}).get("overall_risk_class"),
                "loading": result.get("underwriting_decision", {}).get("premium_loading_percent"),
            }}
        )
        return result
    except Exception as e:
        logger.error(f"Underwriting failed: {e}", exc_info=True)
        return {"error": str(e), "overall_confidence": 0.0}


async def batch_underwrite(applications: list[dict]) -> list[dict]:
    """Process multiple underwriting applications concurrently."""
    import asyncio
    tasks = [
        underwrite_applicant(**app)
        for app in applications
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)
