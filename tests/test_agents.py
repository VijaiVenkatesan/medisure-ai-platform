"""
tests/test_agents.py
Unit tests for all five AI agents.
LLM and vector store calls are mocked - no Groq API key needed to run these.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.schemas import (
    WorkflowState, ClaimStatus, OCRResult, ExtractedClaimData,
    ClaimantInfo, PolicyInfo, IncidentInfo, ClaimAmounts,
    InsuranceType, Country, FraudLevel, ValidationResult, ValidationError
)


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

def make_state(**overrides) -> WorkflowState:
    """Build a minimal WorkflowState for testing."""
    defaults = dict(claim_id=f"CLM-TEST-{str(uuid4())[:8].upper()}", correlation_id=str(uuid4()))
    defaults.update(overrides)
    return WorkflowState(**defaults)


def make_extracted_data(
    policy_type=InsuranceType.HEALTH,
    claimed_amount=45000.0,
    sum_insured=300000.0,
    country=Country.INDIA,
    fraud_score_hint=0.1,
) -> ExtractedClaimData:
    return ExtractedClaimData(
        claimant=ClaimantInfo(
            name="Test Claimant",
            dob="15/06/1985",
            contact_number="9876543210",
            aadhaar_number="XXXX-XXXX-1234",
        ),
        policy=PolicyInfo(
            policy_number="TEST/2024/001",
            insurance_company="Test Insurance Co",
            policy_type=policy_type,
            policy_start_date="01/01/2024",
            policy_end_date="31/12/2024",
            sum_insured=sum_insured,
            currency="INR",
        ),
        incident=IncidentInfo(
            incident_date="15/06/2024",
            incident_location="Chennai, Tamil Nadu",
            incident_description="Hospitalization for surgery",
            hospital_name="Apollo Hospitals",
            diagnosis="Appendicitis",
            reported_date="16/06/2024",
        ),
        amounts=ClaimAmounts(claimed_amount=claimed_amount, currency="INR"),
        country=country,
        extraction_confidence=0.90,
    )


# ─────────────────────────────────────────────
# OCR NODE TESTS
# ─────────────────────────────────────────────

class TestOCRNode:
    @pytest.mark.asyncio
    async def test_ocr_missing_document_path(self):
        """OCR node should handle missing document path gracefully."""
        from app.workflows.claims_workflow import ocr_node
        state = make_state()
        result = await ocr_node(state)
        assert ClaimStatus.ERROR == result.status
        assert any("No document path" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_ocr_nonexistent_file(self):
        """OCR node should handle non-existent file gracefully."""
        from app.workflows.claims_workflow import ocr_node
        state = make_state(document_path="/tmp/does_not_exist_xyz.pdf")
        result = await ocr_node(state)
        # Should set ocr_result with error, not crash
        assert result.ocr_result is not None
        assert result.ocr_result.error is not None

    @pytest.mark.asyncio
    async def test_ocr_success_path(self, tmp_path):
        """OCR node with a real text file (bypass actual OCR)."""
        from app.workflows.claims_workflow import ocr_node
        from app.infrastructure.ocr.engine import OCREngine

        # Write a fake image file
        fake_file = tmp_path / "claim.png"
        fake_file.write_bytes(b"PNG_DUMMY")

        mock_result = OCRResult(
            raw_text="Patient: John Doe\nPolicy: TEST/2024/001\nAmount: Rs. 45,000",
            confidence=0.92,
            engine_used="easyocr",
        )

        with patch.object(OCREngine, "extract_text", AsyncMock(return_value=mock_result)):
            state = make_state(document_path=str(fake_file))
            result = await ocr_node(state)

        assert result.ocr_result is not None
        assert result.ocr_result.confidence == 0.92
        assert "John Doe" in result.ocr_result.raw_text


# ─────────────────────────────────────────────
# EXTRACTION AGENT TESTS
# ─────────────────────────────────────────────

MOCK_EXTRACTION_RESPONSE = {
    "claimant": {"name": "Rajesh Kumar", "dob": "15/06/1980", "gender": "MALE",
                 "contact_number": "9876543210", "aadhaar_number": "1234"},
    "policy": {"policy_number": "LIC/001", "insurance_company": "LIC",
               "policy_type": "HEALTH", "sum_insured": 300000, "currency": "INR"},
    "incident": {"incident_date": "01/06/2024", "hospital_name": "Apollo",
                 "diagnosis": "Appendicitis", "reported_date": "02/06/2024"},
    "amounts": {"claimed_amount": 45000, "currency": "INR"},
    "country": "IN",
    "extraction_confidence": 0.92,
    "extraction_notes": "Clear document, all fields extracted",
}


class TestExtractionAgent:
    @pytest.mark.asyncio
    async def test_extraction_with_no_ocr_text(self):
        """Should handle missing OCR text gracefully."""
        from app.agents.extraction_agent import extraction_agent
        state = make_state()
        result = await extraction_agent(state)
        assert result.extracted_data is not None
        assert any("No OCR text" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_extraction_success(self):
        """Should correctly parse LLM JSON output into ExtractedClaimData."""
        from app.agents.extraction_agent import extraction_agent
        from app.infrastructure.llm.groq_client import GroqClient

        ocr = OCRResult(raw_text="Policy: LIC/001 Amount: 45000 Patient: Rajesh Kumar", confidence=0.9)
        state = make_state(ocr_result=ocr)

        with patch.object(GroqClient, "extract_json", AsyncMock(return_value=MOCK_EXTRACTION_RESPONSE)):
            result = await extraction_agent(state)

        assert result.extracted_data is not None
        assert result.extracted_data.claimant.name == "Rajesh Kumar"
        assert result.extracted_data.policy.insurance_company == "LIC"
        assert result.extracted_data.amounts.claimed_amount == 45000.0
        assert result.extracted_data.policy.policy_type == InsuranceType.HEALTH
        assert result.extracted_data.country == Country.INDIA

    @pytest.mark.asyncio
    async def test_extraction_llm_failure_fallback(self):
        """Should return partial data and record error on LLM failure."""
        from app.agents.extraction_agent import extraction_agent
        from app.infrastructure.llm.groq_client import GroqClient

        ocr = OCRResult(raw_text="Some claim text", confidence=0.7)
        state = make_state(ocr_result=ocr)

        with patch.object(GroqClient, "extract_json", AsyncMock(side_effect=RuntimeError("LLM unavailable"))):
            result = await extraction_agent(state)

        assert result.extracted_data is not None  # Should not be None even on failure
        assert any("Extraction failed" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_extraction_round_number_amounts(self):
        """Should parse Indian number formats correctly."""
        from app.agents.extraction_agent import _build_extracted_data

        raw = {**MOCK_EXTRACTION_RESPONSE, "amounts": {"claimed_amount": "1,50,000", "currency": "INR"}}
        result = _build_extracted_data(raw, "test ocr text")
        assert result.amounts.claimed_amount == 150000.0

    def test_aadhaar_masking(self):
        """Aadhaar numbers should be masked to last 4 digits."""
        claimant = ClaimantInfo(aadhaar_number="123456789012")
        assert claimant.aadhaar_number.endswith("9012")
        assert "123456" not in claimant.aadhaar_number


# ─────────────────────────────────────────────
# VALIDATION AGENT TESTS
# ─────────────────────────────────────────────

class TestValidationAgent:
    @pytest.mark.asyncio
    async def test_valid_claim_passes(self):
        """A well-formed claim should pass validation."""
        from app.agents.validation_agent import validation_agent
        state = make_state(extracted_data=make_extracted_data())
        result = await validation_agent(state)
        assert result.validation_result is not None
        assert result.validation_result.is_valid is True
        assert len(result.validation_result.errors) == 0

    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Missing claimant name and incident date should produce errors."""
        from app.agents.validation_agent import validation_agent
        data = make_extracted_data()
        data.claimant.name = None
        data.incident.incident_date = None
        state = make_state(extracted_data=data)
        result = await validation_agent(state)
        assert result.validation_result.is_valid is False
        fields_with_errors = [e.field for e in result.validation_result.errors]
        assert "claimant.name" in fields_with_errors
        assert "incident.incident_date" in fields_with_errors

    @pytest.mark.asyncio
    async def test_claimed_exceeds_sum_insured(self):
        """Claimed > sum insured should produce a validation error."""
        from app.agents.validation_agent import validation_agent
        data = make_extracted_data(claimed_amount=500000.0, sum_insured=300000.0)
        state = make_state(extracted_data=data)
        result = await validation_agent(state)
        assert any("sum insured" in e.error.lower() for e in result.validation_result.errors)

    @pytest.mark.asyncio
    async def test_motor_claim_missing_vehicle_number(self):
        """Motor claim without vehicle number should produce warning."""
        from app.agents.validation_agent import validation_agent
        data = make_extracted_data(policy_type=InsuranceType.MOTOR)
        data.incident.vehicle_number = None
        state = make_state(extracted_data=data)
        result = await validation_agent(state)
        veh_errors = [e for e in result.validation_result.errors if "vehicle" in e.field.lower()]
        assert len(veh_errors) > 0

    @pytest.mark.asyncio
    async def test_future_incident_date(self):
        """Incident date in the future should be flagged."""
        from app.agents.validation_agent import validation_agent
        data = make_extracted_data()
        data.incident.incident_date = "01/01/2099"
        state = make_state(extracted_data=data)
        result = await validation_agent(state)
        future_errors = [e for e in result.validation_result.errors if "future" in e.error.lower()]
        assert len(future_errors) > 0

    @pytest.mark.asyncio
    async def test_completeness_score_calculation(self):
        """Completeness score should reflect data quality."""
        from app.agents.validation_agent import validation_agent
        data = make_extracted_data()
        state = make_state(extracted_data=data)
        result = await validation_agent(state)
        assert result.validation_result.completeness_score > 0.7


# ─────────────────────────────────────────────
# POLICY AGENT TESTS
# ─────────────────────────────────────────────

MOCK_POLICY_LLM_RESPONSE = {
    "is_eligible": True,
    "eligibility_score": 0.87,
    "reason": "Claim is eligible based on Section 1 coverage for surgical procedures. Appendectomy is listed under covered day-care procedures.",
    "policy_clauses_matched": ["Section 1: Surgical cover", "Section 4: Day Care procedures"],
    "exclusions_triggered": [],
    "coverage_details": {"coverage_percentage": 100, "conditions": []},
}


class TestPolicyAgent:
    @pytest.mark.asyncio
    async def test_no_extracted_data(self):
        """Should handle missing extracted data gracefully."""
        from app.agents.policy_agent import policy_agent
        state = make_state()
        result = await policy_agent(state)
        assert any("No extracted data" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_eligible_with_policies_indexed(self):
        """Should return eligible result when policies exist in vector store."""
        from app.agents.policy_agent import policy_agent
        from app.infrastructure.vectorstore.chroma_store import PolicyVectorStore
        from app.infrastructure.llm.groq_client import GroqClient

        mock_chunks = [{"text": "Health insurance covers surgery.", "score": 0.85,
                        "policy_name": "Test Policy", "insurance_type": "HEALTH",
                        "country": "IN", "company": "Test Co"}]

        state = make_state(extracted_data=make_extracted_data())

        with patch.object(PolicyVectorStore, "search", AsyncMock(return_value=mock_chunks)), \
             patch.object(GroqClient, "extract_json", AsyncMock(return_value=MOCK_POLICY_LLM_RESPONSE)):
            result = await policy_agent(state)

        assert result.policy_result is not None
        assert result.policy_result.is_eligible is True
        assert result.policy_result.eligibility_score == 0.87
        assert len(result.policy_result.retrieved_context) > 0

    @pytest.mark.asyncio
    async def test_fallback_when_no_policies(self):
        """Should use rule-based fallback when vector store is empty."""
        from app.agents.policy_agent import policy_agent
        from app.infrastructure.vectorstore.chroma_store import PolicyVectorStore

        state = make_state(extracted_data=make_extracted_data())

        with patch.object(PolicyVectorStore, "search", AsyncMock(return_value=[])):
            result = await policy_agent(state)

        assert result.policy_result is not None
        assert "rule-based" in result.policy_result.reason.lower()


# ─────────────────────────────────────────────
# FRAUD AGENT TESTS
# ─────────────────────────────────────────────

MOCK_FRAUD_LLM_RESPONSE = {
    "llm_fraud_score": 0.12,
    "llm_indicators": [],
    "anomalies": [],
    "analysis_notes": "No significant fraud patterns detected.",
}


class TestFraudAgent:
    @pytest.mark.asyncio
    async def test_low_risk_legitimate_claim(self):
        """Clean claim should produce low fraud score."""
        from app.agents.fraud_agent import fraud_agent
        from app.infrastructure.llm.groq_client import GroqClient

        state = make_state(extracted_data=make_extracted_data())

        with patch.object(GroqClient, "extract_json", AsyncMock(return_value=MOCK_FRAUD_LLM_RESPONSE)):
            result = await fraud_agent(state)

        assert result.fraud_result is not None
        assert result.fraud_result.fraud_score < 0.50
        assert result.fraud_result.fraud_level in [FraudLevel.LOW, FraudLevel.MEDIUM]

    @pytest.mark.asyncio
    async def test_early_claim_flag(self):
        """Claim filed 5 days after policy start should trigger EARLY_CLAIM indicator."""
        from app.agents.fraud_agent import RuleBasedFraudDetector

        data = make_extracted_data()
        data.policy.policy_start_date = "01/06/2024"
        data.incident.incident_date = "05/06/2024"

        detector = RuleBasedFraudDetector()
        indicators = detector.analyze(data)
        indicator_names = [i.indicator for i in indicators]
        assert "EARLY_CLAIM" in indicator_names

    @pytest.mark.asyncio
    async def test_maximum_claim_flag(self):
        """Claiming 100% of sum insured triggers MAX_CLAIM indicator."""
        from app.agents.fraud_agent import RuleBasedFraudDetector

        data = make_extracted_data(claimed_amount=300000.0, sum_insured=300000.0)
        detector = RuleBasedFraudDetector()
        indicators = detector.analyze(data)
        indicator_names = [i.indicator for i in indicators]
        assert "MAXIMUM_CLAIM" in indicator_names

    @pytest.mark.asyncio
    async def test_round_number_flag(self):
        """Large round-number claim amount triggers indicator."""
        from app.agents.fraud_agent import RuleBasedFraudDetector

        data = make_extracted_data(claimed_amount=100000.0)
        detector = RuleBasedFraudDetector()
        indicators = detector.analyze(data)
        indicator_names = [i.indicator for i in indicators]
        assert "ROUND_NUMBER_AMOUNT" in indicator_names

    @pytest.mark.asyncio
    async def test_fraud_score_bounds(self):
        """Fraud score should always be between 0 and 1."""
        from app.agents.fraud_agent import fraud_agent
        from app.infrastructure.llm.groq_client import GroqClient

        state = make_state(extracted_data=make_extracted_data())
        high_fraud_response = {**MOCK_FRAUD_LLM_RESPONSE, "llm_fraud_score": 0.99}

        with patch.object(GroqClient, "extract_json", AsyncMock(return_value=high_fraud_response)):
            result = await fraud_agent(state)

        assert 0.0 <= result.fraud_result.fraud_score <= 1.0

    @pytest.mark.asyncio
    async def test_graceful_llm_failure(self):
        """Should still return result when LLM analysis fails."""
        from app.agents.fraud_agent import fraud_agent
        from app.infrastructure.llm.groq_client import GroqClient

        state = make_state(extracted_data=make_extracted_data())

        with patch.object(GroqClient, "extract_json", AsyncMock(side_effect=RuntimeError("LLM down"))):
            result = await fraud_agent(state)

        # Should fall back to rule-based only
        assert result.fraud_result is not None
        assert result.fraud_result.fraud_score >= 0.0


# ─────────────────────────────────────────────
# DECISION AGENT TESTS
# ─────────────────────────────────────────────

from app.models.schemas import (
    ValidationResult, PolicyEligibilityResult, FraudAnalysisResult,
    FraudIndicator, ClaimDecision
)


def make_full_state(
    fraud_score=0.1,
    claimed_amount=45000.0,
    is_valid=True,
    is_eligible=True,
) -> WorkflowState:
    from app.models.schemas import ValidationResult, PolicyEligibilityResult, FraudAnalysisResult

    state = make_state(
        extracted_data=make_extracted_data(claimed_amount=claimed_amount),
        validation_result=ValidationResult(
            is_valid=is_valid,
            errors=[] if is_valid else [ValidationError(field="test", error="Critical error")],
            completeness_score=0.85 if is_valid else 0.3,
        ),
        policy_result=PolicyEligibilityResult(
            is_eligible=is_eligible,
            eligibility_score=0.85 if is_eligible else 0.1,
            reason="Coverage confirmed" if is_eligible else "Excluded condition",
        ),
        fraud_result=FraudAnalysisResult(
            fraud_score=fraud_score,
            fraud_level=FraudLevel.LOW if fraud_score < 0.45 else FraudLevel.HIGH,
            indicators=[],
        ),
    )
    return state


class TestDecisionAgent:
    @pytest.mark.asyncio
    async def test_auto_approve_low_risk_small_amount(self):
        """Low-risk claim within auto-approve threshold should be auto-approved."""
        from app.agents.decision_agent import decision_agent
        state = make_full_state(fraud_score=0.08, claimed_amount=40000.0)
        result = await decision_agent(state)
        assert result.decision_result is not None
        assert result.decision_result.decision == ClaimDecision.APPROVE
        assert result.decision_result.approved_amount == 40000.0
        assert result.decision_result.requires_hitl is False

    @pytest.mark.asyncio
    async def test_auto_reject_critical_fraud(self):
        """Critical fraud score should trigger automatic rejection."""
        from app.agents.decision_agent import decision_agent
        state = make_full_state(fraud_score=0.92)
        result = await decision_agent(state)
        assert result.decision_result.decision == ClaimDecision.REJECT
        assert result.decision_result.requires_hitl is False

    @pytest.mark.asyncio
    async def test_route_to_investigate_high_fraud(self):
        """High fraud score (but below auto-reject) should route to INVESTIGATE."""
        from app.agents.decision_agent import decision_agent
        state = make_full_state(fraud_score=0.78, claimed_amount=180000.0)
        result = await decision_agent(state)
        assert result.decision_result.decision == ClaimDecision.INVESTIGATE
        assert result.decision_result.requires_hitl is True

    @pytest.mark.asyncio
    async def test_llm_decision_for_ambiguous(self):
        """Ambiguous case should use LLM decision."""
        from app.agents.decision_agent import decision_agent
        from app.infrastructure.llm.groq_client import GroqClient

        mock_llm_decision = {
            "decision": "APPROVE",
            "confidence": 0.75,
            "explanation": "Claim appears legitimate with minor risk factors.",
            "approved_amount": 75000.0,
            "rejection_reasons": [],
            "conditions": ["Original bills to be submitted"],
            "requires_hitl": False,
            "decision_factors": {},
        }

        state = make_full_state(fraud_score=0.30, claimed_amount=75000.0)

        with patch.object(GroqClient, "extract_json", AsyncMock(return_value=mock_llm_decision)):
            result = await decision_agent(state)

        assert result.decision_result is not None
        assert result.decision_result.decision == ClaimDecision.APPROVE

    @pytest.mark.asyncio
    async def test_hitl_required_high_value(self):
        """High-value claims should always route to HITL."""
        from app.agents.decision_agent import decision_agent, _should_require_hitl
        from app.infrastructure.llm.groq_client import GroqClient

        mock_llm = {
            "decision": "APPROVE", "confidence": 0.80,
            "explanation": "Large claim approved.", "approved_amount": 350000.0,
            "rejection_reasons": [], "conditions": [], "requires_hitl": False,
            "decision_factors": {}
        }

        state = make_full_state(fraud_score=0.15, claimed_amount=350000.0)

        with patch.object(GroqClient, "extract_json", AsyncMock(return_value=mock_llm)):
            result = await decision_agent(state)

        # Either HITL required by LLM or by _should_require_hitl check
        assert result.decision_result.requires_hitl is True or result.status == ClaimStatus.HITL_REVIEW

    @pytest.mark.asyncio
    async def test_explanation_present_always(self):
        """Every decision must include a non-empty explanation."""
        from app.agents.decision_agent import decision_agent
        state = make_full_state(fraud_score=0.05, claimed_amount=30000.0)
        result = await decision_agent(state)
        assert result.decision_result.explanation
        assert len(result.decision_result.explanation) > 10
