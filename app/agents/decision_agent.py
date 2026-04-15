"""
Decision Agent: Makes the final claim decision.
Combines validation, policy eligibility, and fraud signals.
Uses deterministic rules + LLM reasoning for explainable decisions.
"""
from __future__ import annotations
from app.infrastructure.llm.groq_client import get_groq_client
from app.models.schemas import (
    WorkflowState, ClaimStatus, DecisionResult, ClaimDecision,
    FraudLevel, InsuranceType, Country
)
from app.core.config import settings
from app.core.logging import get_logger, log_agent_start, log_agent_complete, log_agent_error

logger = get_logger(__name__)

DECISION_SYSTEM_PROMPT = """You are a senior insurance claims adjuster with 20+ years of experience.
You make fair, evidence-based decisions on insurance claims considering:
- Indian IRDAI regulations and consumer protection rights
- Policy terms and conditions
- Fraud risk
- Business rules
- Claimant's right to fair settlement

Provide clear, empathetic explanations that a claimant can understand.
Return ONLY valid JSON."""

DECISION_SCHEMA = """{
  "decision": "APPROVE|REJECT|INVESTIGATE",
  "confidence": 0.0-1.0,
  "explanation": "clear explanation for the claimant",
  "approved_amount": number or null,
  "rejection_reasons": ["reason 1", "reason 2"],
  "conditions": ["condition if approved with conditions"],
  "requires_hitl": true/false,
  "decision_factors": {
    "validation_weight": 0.0-1.0,
    "policy_weight": 0.0-1.0,
    "fraud_weight": 0.0-1.0
  }
}"""


async def decision_agent(state: WorkflowState) -> WorkflowState:
    """
    LangGraph node: Final decision making.
    Uses deterministic rules first, then LLM for complex cases.
    """
    log_agent_start(logger, "DecisionAgent", state.claim_id)
    state.status = ClaimStatus.DECISION_PENDING

    try:
        # Step 1: Deterministic decision rules
        deterministic_result = _deterministic_decision(state)

        if deterministic_result:
            state.decision_result = deterministic_result
            log_agent_complete(logger, "DecisionAgent", state.claim_id, {
                "decision": deterministic_result.decision.value,
                "method": "deterministic",
                "confidence": deterministic_result.confidence,
            })
            return state

        # Step 2: LLM-assisted decision for ambiguous cases
        llm_result = await _llm_decision(state)
        state.decision_result = llm_result

        # Step 3: Route to HITL if needed
        if llm_result.requires_hitl or _should_require_hitl(state):
            state.status = ClaimStatus.HITL_REVIEW
            state.decision_result.requires_hitl = True
        else:
            # Apply final decision to status
            if llm_result.decision == ClaimDecision.APPROVE:
                state.status = ClaimStatus.APPROVED
            elif llm_result.decision == ClaimDecision.REJECT:
                state.status = ClaimStatus.REJECTED
            else:
                state.status = ClaimStatus.INVESTIGATING

        log_agent_complete(logger, "DecisionAgent", state.claim_id, {
            "decision": llm_result.decision.value,
            "method": "llm_assisted",
            "confidence": llm_result.confidence,
            "requires_hitl": llm_result.requires_hitl,
        })

    except Exception as e:
        log_agent_error(logger, "DecisionAgent", state.claim_id, e)
        state.errors.append(f"Decision agent error: {str(e)}")
        state.decision_result = DecisionResult(
            decision=ClaimDecision.INVESTIGATE,
            confidence=0.0,
            explanation=f"System error during decision making - routed for manual review: {str(e)}",
            requires_hitl=True,
        )
        state.status = ClaimStatus.HITL_REVIEW

    return state


def _deterministic_decision(state: WorkflowState) -> DecisionResult | None:
    """
    Apply deterministic rules that don't need LLM reasoning.
    Returns a decision if clearly deterministic, else None.
    """
    fraud_result = state.fraud_result
    validation_result = state.validation_result
    extracted_data = state.extracted_data

    # AUTO-REJECT: Critical fraud
    if fraud_result and fraud_result.fraud_score >= settings.AUTO_REJECT_FRAUD_THRESHOLD:
        return DecisionResult(
            decision=ClaimDecision.REJECT,
            confidence=0.95,
            explanation=(
                f"This claim has been identified as high-risk due to multiple fraud indicators "
                f"(risk score: {fraud_result.fraud_score:.0%}). "
                f"The claim has been rejected. If you believe this is incorrect, please contact our fraud review team."
            ),
            rejection_reasons=[
                f"Fraud risk score: {fraud_result.fraud_score:.0%} (threshold: {settings.AUTO_REJECT_FRAUD_THRESHOLD:.0%})",
                *[i.description for i in (fraud_result.indicators or [])[:3]],
            ],
            requires_hitl=False,
            decision_factors={"fraud_score": fraud_result.fraud_score},
        )

    # AUTO-REJECT: Too many validation errors
    if validation_result and not validation_result.is_valid:
        critical_errors = [e for e in validation_result.errors if e.severity == "ERROR"]
        if len(critical_errors) >= 3:
            return DecisionResult(
                decision=ClaimDecision.REJECT,
                confidence=0.90,
                explanation=(
                    "This claim cannot be processed due to critical data issues. "
                    "Please resubmit with complete and accurate information."
                ),
                rejection_reasons=[e.error for e in critical_errors],
                requires_hitl=False,
                decision_factors={"validation_errors": len(critical_errors)},
            )

    # AUTO-APPROVE: Low risk, small amount, valid
    if (extracted_data and
        fraud_result and fraud_result.fraud_score <= 0.15 and
        validation_result and validation_result.completeness_score >= 0.75 and
        extracted_data.amounts.claimed_amount and
        extracted_data.amounts.claimed_amount <= settings.AUTO_APPROVE_MAX_AMOUNT_INR):

        amount = extracted_data.amounts.claimed_amount
        currency = extracted_data.amounts.currency

        return DecisionResult(
            decision=ClaimDecision.APPROVE,
            confidence=settings.AUTO_APPROVE_THRESHOLD,
            explanation=(
                f"Your claim for {currency} {amount:,.2f} has been approved. "
                f"The claim passed all automated checks with low risk indicators. "
                f"Payment will be processed within 7 working days."
            ),
            approved_amount=amount,
            requires_hitl=False,
            decision_factors={
                "fraud_score": fraud_result.fraud_score,
                "completeness": validation_result.completeness_score,
                "auto_approve_threshold": settings.AUTO_APPROVE_MAX_AMOUNT_INR,
            },
        )

    # ROUTE TO INVESTIGATE: High fraud (medium tier)
    if fraud_result and fraud_result.fraud_score >= settings.FRAUD_HIGH_THRESHOLD:
        return DecisionResult(
            decision=ClaimDecision.INVESTIGATE,
            confidence=0.80,
            explanation=(
                f"This claim has been flagged for further investigation due to elevated risk factors "
                f"(risk score: {fraud_result.fraud_score:.0%}). "
                f"A specialist will review your claim within 3-5 working days."
            ),
            requires_hitl=True,
            decision_factors={"fraud_score": fraud_result.fraud_score},
        )

    # No deterministic rule matched - use LLM
    return None


async def _llm_decision(state: WorkflowState) -> DecisionResult:
    """LLM-assisted decision for ambiguous cases."""
    llm = get_groq_client()

    # Build context summary
    validation_summary = ""
    if state.validation_result:
        vr = state.validation_result
        validation_summary = f"""
Validation: {'PASSED' if vr.is_valid else 'FAILED'}
Completeness: {vr.completeness_score:.0%}
Errors: {len(vr.errors)} | Warnings: {len(vr.warnings)}
Key errors: {', '.join([e.error for e in vr.errors[:3]]) or 'None'}"""

    policy_summary = ""
    if state.policy_result:
        pr = state.policy_result
        policy_summary = f"""
Policy Eligibility: {'ELIGIBLE' if pr.is_eligible else 'NOT ELIGIBLE'}
Eligibility Score: {pr.eligibility_score:.0%}
Reason: {pr.reason[:300] if pr.reason else 'N/A'}
Exclusions: {', '.join(pr.exclusions_triggered) or 'None'}"""

    fraud_summary = ""
    if state.fraud_result:
        fr = state.fraud_result
        fraud_summary = f"""
Fraud Score: {fr.fraud_score:.0%}
Fraud Level: {fr.fraud_level.value}
Key Indicators: {', '.join([i.indicator for i in fr.indicators[:3]]) or 'None'}"""

    claim_summary = ""
    if state.extracted_data:
        ed = state.extracted_data
        claim_summary = f"""
Claimant: {ed.claimant.name or 'Unknown'}
Policy Type: {ed.policy.policy_type.value if ed.policy.policy_type else 'Unknown'}
Company: {ed.policy.insurance_company or 'Unknown'}
Claimed Amount: {ed.amounts.currency} {ed.amounts.claimed_amount or 'Unknown'}
Sum Insured: {ed.amounts.currency} {ed.policy.sum_insured or 'Unknown'}
Country: {ed.country.value if ed.country else 'IN'}
Incident: {(ed.incident.incident_description or '')[:200]}"""

    prompt = f"""Make a final decision on this insurance claim:

CLAIM SUMMARY:{claim_summary}

VALIDATION RESULTS:{validation_summary}

POLICY ELIGIBILITY:{policy_summary}

FRAUD ANALYSIS:{fraud_summary}

PREVIOUS ERRORS: {', '.join(state.errors) or 'None'}

Guidelines:
1. If fraud score > 0.60, recommend INVESTIGATE unless definitively fraudulent
2. If policy not eligible with exclusions, explain clearly
3. Approved amount should account for policy limits, deductibles
4. Require HITL for claims > ₹2,00,000 or any INVESTIGATE decision
5. Provide clear, compassionate explanation for the claimant
6. For Indian claims: mention IRDAI grievance redressal if rejecting

Return JSON matching:
{DECISION_SCHEMA}"""

    raw = await llm.extract_json(
        prompt=prompt,
        system_prompt=DECISION_SYSTEM_PROMPT,
        model=settings.GROQ_MODEL_PRIMARY,
    )

    # Parse decision
    decision_str = raw.get("decision", "INVESTIGATE").upper()
    try:
        decision = ClaimDecision(decision_str)
    except ValueError:
        decision = ClaimDecision.INVESTIGATE

    return DecisionResult(
        decision=decision,
        confidence=float(raw.get("confidence", 0.6)),
        explanation=str(raw.get("explanation", "Decision made by automated system.")),
        approved_amount=raw.get("approved_amount"),
        rejection_reasons=raw.get("rejection_reasons", []),
        conditions=raw.get("conditions", []),
        requires_hitl=bool(raw.get("requires_hitl", decision == ClaimDecision.INVESTIGATE)),
        decision_factors=raw.get("decision_factors", {}),
    )


def _should_require_hitl(state: WorkflowState) -> bool:
    """Additional HITL routing rules."""
    # High-value claims
    if (state.extracted_data and
        state.extracted_data.amounts.claimed_amount and
        state.extracted_data.amounts.claimed_amount > 200000):  # > 2 lakh INR
        return True

    # Low confidence decisions
    if state.decision_result and state.decision_result.confidence < 0.65:
        return True

    # Medium fraud score
    if state.fraud_result and state.fraud_result.fraud_score >= settings.FRAUD_MEDIUM_THRESHOLD:
        return True

    return False
