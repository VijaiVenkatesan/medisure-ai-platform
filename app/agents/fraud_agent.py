"""
Fraud Detection Agent: Multi-layered fraud analysis combining rule-based signals
and LLM-assisted pattern recognition. Returns fraud score 0-1.
India-focused fraud patterns included.
"""
from __future__ import annotations
import re
from datetime import datetime
from typing import Optional
from app.infrastructure.llm.groq_client import get_groq_client
from app.models.schemas import (
    WorkflowState, ClaimStatus, FraudAnalysisResult, FraudIndicator,
    FraudLevel, ExtractedClaimData, InsuranceType, Country
)
from app.core.config import settings
from app.core.logging import get_logger, log_agent_start, log_agent_complete, log_agent_error

logger = get_logger(__name__)

FRAUD_SYSTEM_PROMPT = """You are an expert insurance fraud analyst with deep knowledge of:
- Indian insurance fraud patterns (ghost hospitals, inflated bills, fake accidents)
- International fraud patterns
- Temporal anomalies in claims
- Document inconsistencies
- Statistical outliers

Analyze the provided claim data for fraud indicators.
Return ONLY valid JSON with your analysis."""

FRAUD_SCHEMA = """{
  "llm_fraud_score": 0.0-1.0,
  "llm_indicators": ["indicator 1", "indicator 2"],
  "anomalies": ["anomaly description"],
  "analysis_notes": "detailed reasoning"
}"""


class RuleBasedFraudDetector:
    """
    Rule-based fraud signal detection.
    Each rule returns a weight (0-1) and description.
    """

    def analyze(self, data: ExtractedClaimData) -> list[FraudIndicator]:
        indicators = []

        for rule_fn in [
            self._check_round_numbers,
            self._check_claim_timing,
            self._check_new_policy_claim,
            self._check_high_amount_anomaly,
            self._check_missing_critical_fields,
            self._check_contact_info_anomaly,
            self._check_india_fraud_patterns,
            self._check_multiple_incidents,
            self._check_hospital_anomaly,
        ]:
            result = rule_fn(data)
            if result:
                indicators.extend(result)

        return indicators

    def _check_round_numbers(self, data: ExtractedClaimData) -> list[FraudIndicator]:
        """Round numbers in claim amounts are a fraud indicator."""
        indicators = []
        amount = data.amounts.claimed_amount

        if amount is not None:
            # Check if amount is suspiciously round (e.g., exactly 50000, 100000)
            if amount > 1000 and amount == int(amount):
                if amount % 10000 == 0:
                    indicators.append(FraudIndicator(
                        indicator="ROUND_NUMBER_AMOUNT",
                        weight=0.2,
                        description=f"Claimed amount is a suspiciously round number: {data.amounts.currency} {amount:,.0f}"
                    ))

        return indicators

    def _check_claim_timing(self, data: ExtractedClaimData) -> list[FraudIndicator]:
        """Check for suspicious timing patterns."""
        indicators = []

        if data.incident.incident_date and data.incident.reported_date:
            try:
                formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]
                inc_dt = None
                rep_dt = None

                for fmt in formats:
                    try:
                        inc_dt = datetime.strptime(data.incident.incident_date.strip(), fmt)
                        break
                    except ValueError:
                        continue

                for fmt in formats:
                    try:
                        rep_dt = datetime.strptime(data.incident.reported_date.strip(), fmt)
                        break
                    except ValueError:
                        continue

                if inc_dt and rep_dt:
                    delay_days = (rep_dt - inc_dt).days

                    # Very quick reporting may indicate pre-planned fraud
                    if delay_days == 0:
                        indicators.append(FraudIndicator(
                            indicator="SAME_DAY_REPORTING",
                            weight=0.15,
                            description="Incident reported on the same day as occurrence - unusual for genuine claims"
                        ))

                    # Very late reporting
                    if delay_days > 90:
                        indicators.append(FraudIndicator(
                            indicator="LATE_REPORTING",
                            weight=0.25,
                            description=f"Claim reported {delay_days} days after incident - exceeds typical 30-day window"
                        ))

            except Exception:
                pass

        return indicators

    def _check_new_policy_claim(self, data: ExtractedClaimData) -> list[FraudIndicator]:
        """Claims filed very soon after policy purchase are suspicious."""
        indicators = []

        if data.policy.policy_start_date and data.incident.incident_date:
            try:
                formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]
                start_dt = None
                inc_dt = None

                for fmt in formats:
                    try:
                        start_dt = datetime.strptime(data.policy.policy_start_date.strip(), fmt)
                        inc_dt = datetime.strptime(data.incident.incident_date.strip(), fmt)
                        break
                    except ValueError:
                        continue

                if start_dt and inc_dt:
                    days_after_start = (inc_dt - start_dt).days

                    if 0 <= days_after_start <= 30:
                        indicators.append(FraudIndicator(
                            indicator="EARLY_CLAIM",
                            weight=0.40,
                            description=f"Claim filed {days_after_start} days after policy start - high fraud risk"
                        ))
                    elif 31 <= days_after_start <= 90:
                        indicators.append(FraudIndicator(
                            indicator="EARLY_CLAIM_MODERATE",
                            weight=0.20,
                            description=f"Claim filed {days_after_start} days after policy start - moderate concern"
                        ))
            except Exception:
                pass

        return indicators

    def _check_high_amount_anomaly(self, data: ExtractedClaimData) -> list[FraudIndicator]:
        """High claimed amounts relative to sum insured."""
        indicators = []

        if data.amounts.claimed_amount and data.policy.sum_insured and data.policy.sum_insured > 0:
            ratio = data.amounts.claimed_amount / data.policy.sum_insured

            if ratio > 0.95:
                indicators.append(FraudIndicator(
                    indicator="MAXIMUM_CLAIM",
                    weight=0.30,
                    description=f"Claiming {ratio*100:.1f}% of total sum insured in a single incident"
                ))

        return indicators

    def _check_missing_critical_fields(self, data: ExtractedClaimData) -> list[FraudIndicator]:
        """Missing fields that should be present for legitimate claims."""
        indicators = []
        missing = []

        if not data.claimant.contact_number:
            missing.append("contact number")
        if not data.claimant.address:
            missing.append("address")

        if len(missing) >= 2:
            indicators.append(FraudIndicator(
                indicator="INCOMPLETE_CLAIMANT_INFO",
                weight=0.15,
                description=f"Multiple critical fields missing: {', '.join(missing)}"
            ))

        return indicators

    def _check_contact_info_anomaly(self, data: ExtractedClaimData) -> list[FraudIndicator]:
        """Check for suspicious contact information."""
        indicators = []

        if data.claimant.contact_number:
            # Repeated digit patterns
            phone = re.sub(r'[^0-9]', '', data.claimant.contact_number)
            if len(phone) >= 10:
                unique_digits = len(set(phone))
                if unique_digits <= 2:
                    indicators.append(FraudIndicator(
                        indicator="SUSPICIOUS_PHONE",
                        weight=0.20,
                        description=f"Phone number has very few unique digits - possible fake: {data.claimant.contact_number}"
                    ))

        return indicators

    def _check_india_fraud_patterns(self, data: ExtractedClaimData) -> list[FraudIndicator]:
        """India-specific fraud patterns."""
        indicators = []

        if data.country != Country.INDIA:
            return indicators

        # Health claim fraud: ghost hospitals
        if data.policy.policy_type == InsuranceType.HEALTH:
            if data.incident.hospital_name:
                hospital = data.incident.hospital_name.lower()
                # Very generic hospital names often indicate fraud
                suspicious_keywords = ["generic", "unnamed", "hospital", "clinic"]
                if hospital.strip() in suspicious_keywords:
                    indicators.append(FraudIndicator(
                        indicator="SUSPICIOUS_HOSPITAL_NAME",
                        weight=0.25,
                        description=f"Hospital name appears generic or suspicious: {data.incident.hospital_name}"
                    ))

            # Check for suspiciously high medical bills in India
            if data.amounts.claimed_amount and data.amounts.currency == "INR":
                if data.amounts.claimed_amount > 500000:  # 5 lakh
                    indicators.append(FraudIndicator(
                        indicator="HIGH_MEDICAL_BILL_INDIA",
                        weight=0.20,
                        description=f"Medical claim of ₹{data.amounts.claimed_amount:,.0f} is very high for India - verify itemized bills"
                    ))

        # Motor fraud: accident description anomalies
        if data.policy.policy_type == InsuranceType.MOTOR:
            if data.incident.incident_description:
                desc = data.incident.incident_description.lower()
                if any(kw in desc for kw in ["total loss", "completely destroyed", "beyond repair"]):
                    indicators.append(FraudIndicator(
                        indicator="TOTAL_LOSS_CLAIM",
                        weight=0.20,
                        description="Total loss claim - requires independent inspection"
                    ))

        return indicators

    def _check_multiple_incidents(self, data: ExtractedClaimData) -> list[FraudIndicator]:
        """Placeholder for historical claim checking - would query DB in production."""
        # In production, this would check the DB for previous claims from same claimant
        return []

    def _check_hospital_anomaly(self, data: ExtractedClaimData) -> list[FraudIndicator]:
        """Check for hospital/doctor anomalies."""
        indicators = []

        if data.incident.hospital_name and data.incident.doctor_name:
            # Both present is good
            pass
        elif data.policy.policy_type == InsuranceType.HEALTH and not data.incident.hospital_name and not data.incident.doctor_name:
            indicators.append(FraudIndicator(
                indicator="MISSING_MEDICAL_PROVIDER",
                weight=0.20,
                description="No hospital or doctor information for health insurance claim"
            ))

        return indicators


_rule_detector = RuleBasedFraudDetector()


def _calculate_fraud_level(score: float) -> FraudLevel:
    if score >= settings.FRAUD_HIGH_THRESHOLD:
        return FraudLevel.CRITICAL if score >= 0.90 else FraudLevel.HIGH
    elif score >= settings.FRAUD_MEDIUM_THRESHOLD:
        return FraudLevel.MEDIUM
    else:
        return FraudLevel.LOW


async def fraud_agent(state: WorkflowState) -> WorkflowState:
    """LangGraph node: Multi-layered fraud analysis."""
    log_agent_start(logger, "FraudAgent", state.claim_id)
    state.status = ClaimStatus.FRAUD_ANALYSIS

    if not state.extracted_data:
        state.errors.append("No extracted data for fraud analysis")
        state.fraud_result = FraudAnalysisResult(
            fraud_score=0.5,
            fraud_level=FraudLevel.MEDIUM,
            analysis_notes="Insufficient data for fraud analysis",
        )
        return state

    try:
        data = state.extracted_data

        # Step 1: Rule-based detection
        rule_indicators = _rule_detector.analyze(data)
        rule_score = min(1.0, sum(i.weight for i in rule_indicators))

        # Step 2: LLM-based analysis
        llm_score, llm_indicators, anomalies, llm_notes = await _llm_fraud_analysis(data, rule_indicators)

        # Step 3: Combined scoring (weighted average)
        final_score = (rule_score * 0.6) + (llm_score * 0.4)
        final_score = min(1.0, max(0.0, final_score))

        fraud_level = _calculate_fraud_level(final_score)

        # Combine indicators
        all_indicators = rule_indicators + [
            FraudIndicator(indicator=ind, weight=0.1, description=ind)
            for ind in llm_indicators
            if ind not in [r.indicator for r in rule_indicators]
        ]

        result = FraudAnalysisResult(
            fraud_score=round(final_score, 4),
            fraud_level=fraud_level,
            indicators=all_indicators,
            anomalies_detected=anomalies,
            risk_factors=[i.description for i in all_indicators[:5]],
            analysis_notes=llm_notes or f"Rule score: {rule_score:.2f}, LLM score: {llm_score:.2f}",
        )

        state.fraud_result = result
        log_agent_complete(logger, "FraudAgent", state.claim_id, {
            "fraud_score": final_score,
            "fraud_level": fraud_level.value,
            "indicators_count": len(all_indicators),
        })

    except Exception as e:
        log_agent_error(logger, "FraudAgent", state.claim_id, e)
        state.errors.append(f"Fraud analysis error: {str(e)}")
        state.fraud_result = FraudAnalysisResult(
            fraud_score=0.3,
            fraud_level=FraudLevel.LOW,
            analysis_notes=f"Fraud analysis failed: {str(e)} - defaulting to low risk",
        )

    return state


async def _llm_fraud_analysis(
    data: ExtractedClaimData,
    rule_indicators: list[FraudIndicator],
) -> tuple[float, list[str], list[str], str]:
    """Run LLM-based fraud analysis."""
    try:
        llm = get_groq_client()

        rule_summary = "\n".join([f"- {i.indicator} (weight={i.weight}): {i.description}" for i in rule_indicators])

        claim_info = f"""
Claimant: {data.claimant.name or 'Unknown'}
Policy Type: {data.policy.policy_type.value if data.policy.policy_type else 'Unknown'}
Claimed Amount: {data.amounts.currency} {data.amounts.claimed_amount or 'Unknown'}
Sum Insured: {data.amounts.currency} {data.policy.sum_insured or 'Unknown'}
Policy Start: {data.policy.policy_start_date or 'Unknown'}
Incident Date: {data.incident.incident_date or 'Unknown'}
Reported Date: {data.incident.reported_date or 'Unknown'}
Hospital: {data.incident.hospital_name or 'N/A'}
Diagnosis: {data.incident.diagnosis or 'N/A'}
Country: {data.country.value if data.country else 'IN'}
Incident Description: {(data.incident.incident_description or '')[:300]}
"""

        prompt = f"""Analyze this insurance claim for fraud patterns:

CLAIM DETAILS:
{claim_info}

RULE-BASED FLAGS ALREADY DETECTED:
{rule_summary if rule_summary else "None"}

Based on your analysis, identify additional fraud signals NOT already captured above.
Consider:
1. Temporal inconsistencies
2. Amount anomalies for the claim type and location
3. Description red flags
4. Policy type specific fraud patterns
5. India-specific fraud schemes if applicable

Return JSON matching:
{FRAUD_SCHEMA}"""

        raw = await llm.extract_json(
            prompt=prompt,
            system_prompt=FRAUD_SYSTEM_PROMPT,
            model=settings.GROQ_MODEL_FAST,  # Use faster model for fraud check
        )

        llm_score = float(raw.get("llm_fraud_score", 0.1))
        llm_indicators = raw.get("llm_indicators", [])
        anomalies = raw.get("anomalies", [])
        notes = raw.get("analysis_notes", "")

        return llm_score, llm_indicators, anomalies, notes

    except Exception as e:
        logger.warning(f"LLM fraud analysis failed: {e} - using rule-based only")
        return 0.1, [], [], f"LLM analysis unavailable: {str(e)}"
