"""
Enterprise API routes — Phase 3 & 4
Underwriting, clinical decision support, drug interactions,
risk stratification, and enterprise health endpoints.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.medical.underwriting_agent import underwrite_applicant
from app.agents.medical.clinical_agent import (
    clinical_diagnosis_support,
    check_drug_interactions,
    patient_risk_stratification,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ── MEDICAL UNDERWRITING ─────────────────────────────────────────────

class UnderwritingRequest(BaseModel):
    medical_summary: str
    age: int
    gender: str = "MALE"
    insurance_type: str = "HEALTH"
    sum_assured: Optional[float] = None
    policy_term_years: Optional[int] = None
    country: str = "IN"
    additional_context: Optional[str] = None


@router.post(
    "/underwriting/assess",
    tags=["Medical Underwriting"],
    summary="AI-powered medical underwriting risk assessment",
)
async def underwriting_assessment(request: UnderwritingRequest):
    """
    Perform complete medical underwriting for an insurance applicant.

    Assesses:
    - Mortality and morbidity risk
    - Premium loading percentage
    - Specific exclusions with duration
    - Additional medical requirements
    - IRDAI compliance (India)

    Returns risk class: PREFERRED / STANDARD / SUBSTANDARD 1-3 / DECLINE
    """
    if len(request.medical_summary.strip()) < 20:
        raise HTTPException(422, "Medical summary too short for underwriting")

    result = await underwrite_applicant(
        medical_summary=request.medical_summary,
        age=request.age,
        gender=request.gender,
        insurance_type=request.insurance_type,
        sum_assured=request.sum_assured,
        policy_term_years=request.policy_term_years,
        country=request.country,
        additional_context=request.additional_context,
    )

    if "error" in result:
        raise HTTPException(422, result["error"])
    return result


# ── CLINICAL DECISION SUPPORT ────────────────────────────────────────

class DiagnosisRequest(BaseModel):
    symptoms: list[str]
    patient_age: int
    patient_gender: str = "MALE"
    duration: str = ""
    vitals: Optional[dict] = None
    lab_results: Optional[str] = None
    medical_history: Optional[str] = None
    country: str = "IN"


@router.post(
    "/clinical/diagnose",
    tags=["Clinical Decision Support"],
    summary="AI-powered differential diagnosis support",
)
async def diagnosis_support(request: DiagnosisRequest):
    """
    Generate evidence-based differential diagnoses from clinical presentation.

    India-first: Considers tropical diseases (Dengue, Malaria, TB, Typhoid),
    nutritional deficiencies, and ICMR clinical guidelines.

    DISCLAIMER: Decision support only — clinical judgment required.
    """
    if not request.symptoms:
        raise HTTPException(422, "At least one symptom required")

    result = await clinical_diagnosis_support(
        symptoms=request.symptoms,
        patient_age=request.patient_age,
        patient_gender=request.patient_gender,
        duration=request.duration,
        vitals=request.vitals,
        lab_results=request.lab_results,
        medical_history=request.medical_history,
        country=request.country,
    )

    if "error" in result:
        raise HTTPException(422, result["error"])
    return result


class DrugInteractionRequest(BaseModel):
    medications: list[str]
    patient_age: int = 40
    conditions: Optional[list[str]] = None
    renal_function: Optional[str] = None
    hepatic_function: Optional[str] = None


@router.post(
    "/clinical/drug-interactions",
    tags=["Clinical Decision Support"],
    summary="Check drug-drug and drug-food interactions",
)
async def drug_interaction_check(request: DrugInteractionRequest):
    """
    Check interactions between multiple medications.
    Includes drug-drug, drug-food (Indian diet aware), drug-disease interactions.
    Provides severity: CONTRAINDICATED / MAJOR / MODERATE / MINOR.
    """
    if not request.medications:
        raise HTTPException(422, "At least one medication required")

    result = await check_drug_interactions(
        medications=request.medications,
        patient_age=request.patient_age,
        conditions=request.conditions,
        renal_function=request.renal_function,
        hepatic_function=request.hepatic_function,
    )

    if "error" in result:
        raise HTTPException(422, result["error"])
    return result


class RiskStratificationRequest(BaseModel):
    patient_data: dict
    risk_type: str = "CARDIOVASCULAR"


@router.post(
    "/clinical/risk-stratify",
    tags=["Clinical Decision Support"],
    summary="Patient risk stratification for prevention and underwriting",
)
async def risk_stratification(request: RiskStratificationRequest):
    """
    Stratify patient risk for disease prevention.

    Risk types: CARDIOVASCULAR, DIABETES, CANCER, READMISSION

    Returns: risk score, category (LOW/MODERATE/HIGH/VERY_HIGH),
    10-year risk %, modifiable factors, interventions.
    """
    result = await patient_risk_stratification(
        patient_data=request.patient_data,
        risk_type=request.risk_type,
    )
    if "error" in result:
        raise HTTPException(422, result["error"])
    return result
