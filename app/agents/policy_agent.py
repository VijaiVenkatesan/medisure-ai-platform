"""
Policy Agent: RAG-based policy eligibility determination.
Retrieves relevant policy clauses and uses LLM to determine coverage.
Cites retrieved context in its response.
"""
from __future__ import annotations
from app.infrastructure.llm.groq_client import get_groq_client
from app.infrastructure.vectorstore.chroma_store import get_vector_store
from app.models.schemas import (
    WorkflowState, ClaimStatus, PolicyEligibilityResult, ExtractedClaimData
)
from app.core.logging import get_logger, log_agent_start, log_agent_complete, log_agent_error

logger = get_logger(__name__)

POLICY_SYSTEM_PROMPT = """You are an expert insurance policy analyst specializing in:
- Indian insurance regulations (IRDAI, IRDA circular compliance)
- LIC, Star Health, HDFC ERGO, Bajaj Allianz, New India Assurance policies
- Ayushman Bharat (PM-JAY), PMFBY, ESIC policies
- International policies (US, UK, UAE)

Based on the retrieved policy clauses, determine if the claim is eligible for coverage.
You MUST cite specific policy clauses in your response.
Return ONLY valid JSON."""

ELIGIBILITY_SCHEMA = """{
  "is_eligible": true/false,
  "eligibility_score": 0.0-1.0,
  "reason": "detailed explanation with specific clause references",
  "policy_clauses_matched": ["clause 1 summary", "clause 2 summary"],
  "exclusions_triggered": ["exclusion name if any"],
  "coverage_details": {
    "covered_amount": number or null,
    "coverage_percentage": number or null,
    "conditions": ["list of conditions"]
  }
}"""


async def policy_agent(state: WorkflowState) -> WorkflowState:
    """
    LangGraph node: Check policy eligibility using RAG.
    Retrieves relevant policy chunks and uses LLM to determine coverage.
    """
    log_agent_start(logger, "PolicyAgent", state.claim_id)
    state.status = ClaimStatus.POLICY_CHECK

    if not state.extracted_data:
        state.errors.append("No extracted data for policy check")
        return state

    try:
        vector_store = get_vector_store()
        llm = get_groq_client()
        data = state.extracted_data

        # Build query for semantic search
        query = _build_policy_query(data)

        # Retrieve relevant policy chunks
        insurance_type = None
        if data.policy.policy_type:
            insurance_type = data.policy.policy_type.value

        country_code = data.country.value if data.country else "IN"

        retrieved_chunks = await vector_store.search(
            query=query,
            insurance_type=insurance_type,
            country=country_code,
            top_k=6,
        )

        retrieved_context = [chunk["text"] for chunk in retrieved_chunks]
        retrieved_sources = [f"[{chunk['policy_name']}]" for chunk in retrieved_chunks]

        # If no policies indexed, provide rule-based fallback
        if not retrieved_chunks:
            logger.warning(
                f"No policy documents in vector store - using rule-based eligibility",
                extra={"extra_data": {"claim_id": state.claim_id}}
            )
            result = _rule_based_eligibility(data)
            result.retrieved_context = ["No policies indexed - rule-based check applied"]
            state.policy_result = result
            return state

        # Use LLM for eligibility determination
        context_text = "\n\n---\n\n".join([
            f"[Source: {chunk['policy_name']} | Score: {chunk['score']:.2f}]\n{chunk['text']}"
            for chunk in retrieved_chunks
        ])

        claim_summary = _build_claim_summary(data)

        prompt = f"""INSURANCE CLAIM DETAILS:
{claim_summary}

RETRIEVED POLICY CLAUSES (semantic similarity search results):
{context_text}

TASK: Based on the retrieved policy clauses, determine if this claim is eligible for coverage.
You must:
1. Cite specific clauses from the retrieved context
2. Check for exclusions that may apply
3. Consider Indian insurance regulations if applicable
4. Provide a coverage amount estimate if possible

Return JSON matching this schema:
{ELIGIBILITY_SCHEMA}"""

        raw_result = await llm.extract_json(
            prompt=prompt,
            system_prompt=POLICY_SYSTEM_PROMPT,
        )

        result = PolicyEligibilityResult(
            is_eligible=bool(raw_result.get("is_eligible", True)),
            eligibility_score=float(raw_result.get("eligibility_score", 0.7)),
            reason=str(raw_result.get("reason", "")),
            policy_clauses_matched=raw_result.get("policy_clauses_matched", []),
            exclusions_triggered=raw_result.get("exclusions_triggered", []),
            retrieved_context=retrieved_context,
            coverage_details=raw_result.get("coverage_details"),
        )

        state.policy_result = result
        log_agent_complete(logger, "PolicyAgent", state.claim_id, {
            "is_eligible": result.is_eligible,
            "score": result.eligibility_score,
            "chunks_retrieved": len(retrieved_chunks),
        })

    except Exception as e:
        log_agent_error(logger, "PolicyAgent", state.claim_id, e)
        state.errors.append(f"Policy check failed: {str(e)}")
        # Default to eligible with low confidence on error
        state.policy_result = PolicyEligibilityResult(
            is_eligible=True,
            eligibility_score=0.5,
            reason=f"Policy check failed due to error - defaulting to eligible for manual review: {str(e)}",
            retrieved_context=[],
        )

    return state


def _build_policy_query(data: ExtractedClaimData) -> str:
    """Build semantic search query from claim data."""
    parts = []

    if data.policy.policy_type:
        parts.append(data.policy.policy_type.value.lower().replace("_", " "))
    if data.policy.insurance_company:
        parts.append(data.policy.insurance_company)
    if data.incident.diagnosis:
        parts.append(data.incident.diagnosis)
    if data.incident.incident_description:
        parts.append(data.incident.incident_description[:200])
    if data.policy.policy_number:
        parts.append(f"policy {data.policy.policy_number}")

    query = " ".join(parts) if parts else "insurance claim coverage eligibility"
    return query[:500]


def _build_claim_summary(data: ExtractedClaimData) -> str:
    """Build a human-readable claim summary for the LLM."""
    lines = [
        f"Claimant: {data.claimant.name or 'Unknown'}",
        f"Policy Type: {data.policy.policy_type.value if data.policy.policy_type else 'Unknown'}",
        f"Insurance Company: {data.policy.insurance_company or 'Unknown'}",
        f"Policy Number: {data.policy.policy_number or 'Unknown'}",
        f"Claimed Amount: {data.amounts.currency} {data.amounts.claimed_amount or 'Unknown'}",
        f"Incident Date: {data.incident.incident_date or 'Unknown'}",
        f"Incident Description: {data.incident.incident_description or 'Unknown'}",
        f"Country: {data.country.value if data.country else 'IN'}",
    ]
    if data.incident.hospital_name:
        lines.append(f"Hospital: {data.incident.hospital_name}")
    if data.incident.diagnosis:
        lines.append(f"Diagnosis: {data.incident.diagnosis}")
    if data.incident.vehicle_number:
        lines.append(f"Vehicle: {data.incident.vehicle_number}")
    if data.policy.sum_insured:
        lines.append(f"Sum Insured: {data.amounts.currency} {data.policy.sum_insured}")

    return "\n".join(lines)


def _rule_based_eligibility(data: ExtractedClaimData) -> PolicyEligibilityResult:
    """
    Fallback rule-based eligibility when no policies are indexed.
    Basic checks without LLM.
    """
    reasons = []
    score = 0.7  # Default: assume eligible

    # Check policy dates if available
    if data.policy.policy_end_date and data.incident.incident_date:
        reasons.append("Policy and incident dates present - coverage period check recommended")

    # Check claimed amount vs sum insured
    if data.amounts.claimed_amount and data.policy.sum_insured:
        if data.amounts.claimed_amount <= data.policy.sum_insured:
            reasons.append("Claimed amount within sum insured limits")
            score += 0.1
        else:
            reasons.append("Claimed amount EXCEEDS sum insured - partially eligible at best")
            score = max(0.3, score - 0.3)

    # India government scheme checks
    from app.models.schemas import InsuranceType
    if data.policy.policy_type in [InsuranceType.AYUSHMAN_BHARAT, InsuranceType.PRADHAN_MANTRI]:
        reasons.append("Government scheme - standard IRDAI compliance applies")
        score = 0.75

    reason_str = (
        "No policy documents indexed. Rule-based check applied. "
        + " | ".join(reasons) if reasons else "Manual policy verification required."
    )

    return PolicyEligibilityResult(
        is_eligible=score >= 0.5,
        eligibility_score=min(1.0, score),
        reason=reason_str,
        policy_clauses_matched=[],
        exclusions_triggered=[],
    )
