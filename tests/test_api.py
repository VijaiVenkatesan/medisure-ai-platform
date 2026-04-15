"""
tests/test_api.py
Integration tests for the FastAPI routes.
Uses in-memory SQLite and mocked LLM/OCR calls.
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.infrastructure.db.models import Base, engine, init_db
from app.models.schemas import OCRResult


# ─────────────────────────────────────────────
# TEST SETUP
# ─────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    """Create all tables in the test database before tests run."""
    await init_db()
    yield
    # Teardown: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def make_minimal_pdf_bytes() -> bytes:
    """Return a minimal valid PDF file in bytes."""
    return b"""%PDF-1.4
1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj
2 0 obj<</Type /Pages /Kids [3 0 R] /Count 1>>endobj
3 0 obj<</Type /Page /MediaBox [0 0 612 792]>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer<</Size 4 /Root 1 0 R>>
startxref
190
%%EOF"""


MOCK_OCR_SUCCESS = OCRResult(
    raw_text="""Insurance Claim Form
Patient Name: Test Patient
Policy Number: TEST/2024/001
Claimed Amount: Rs. 45,000
Incident Date: 15/06/2024
Hospital: Apollo Hospital
Diagnosis: Appendicitis Surgery""",
    confidence=0.91,
    engine_used="easyocr",
)

MOCK_EXTRACTION = {
    "claimant": {"name": "Test Patient", "contact_number": "9876543210"},
    "policy": {"policy_number": "TEST/2024/001", "insurance_company": "Test Co",
               "policy_type": "HEALTH", "sum_insured": 200000, "currency": "INR"},
    "incident": {"incident_date": "15/06/2024", "hospital_name": "Apollo Hospital",
                 "diagnosis": "Appendicitis Surgery", "reported_date": "16/06/2024"},
    "amounts": {"claimed_amount": 45000, "currency": "INR"},
    "country": "IN", "extraction_confidence": 0.91, "extraction_notes": None
}

MOCK_POLICY_RESULT = {
    "is_eligible": True, "eligibility_score": 0.88,
    "reason": "Eligible per policy terms.", "policy_clauses_matched": [],
    "exclusions_triggered": [], "coverage_details": None
}

MOCK_FRAUD_RESULT = {
    "llm_fraud_score": 0.08, "llm_indicators": [], "anomalies": [],
    "analysis_notes": "Clean claim."
}

MOCK_DECISION_RESULT = {
    "decision": "APPROVE", "confidence": 0.91,
    "explanation": "Claim approved automatically.", "approved_amount": 45000.0,
    "rejection_reasons": [], "conditions": [], "requires_hitl": False,
    "decision_factors": {}
}


# ─────────────────────────────────────────────
# HEALTH ENDPOINT
# ─────────────────────────────────────────────

class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        assert "name" in response.json()


# ─────────────────────────────────────────────
# CLAIM SUBMISSION
# ─────────────────────────────────────────────

class TestClaimSubmission:
    @pytest.mark.asyncio
    async def test_submit_pdf_claim(self, client):
        """Valid PDF upload should return 202 with claim_id."""
        from app.infrastructure.ocr.engine import OCREngine
        from app.infrastructure.llm.groq_client import GroqClient
        from app.infrastructure.vectorstore.chroma_store import PolicyVectorStore

        with patch.object(OCREngine, "extract_text", AsyncMock(return_value=MOCK_OCR_SUCCESS)), \
             patch.object(GroqClient, "extract_json", AsyncMock(return_value=MOCK_EXTRACTION)):

            files = {"file": ("claim.pdf", make_minimal_pdf_bytes(), "application/pdf")}
            response = await client.post("/api/v1/claims/submit", files=files)

        assert response.status_code == 202
        data = response.json()
        assert "claim_id" in data
        assert data["claim_id"].startswith("CLM-")
        assert data["status"] == "RECEIVED"
        assert "correlation_id" in data

    @pytest.mark.asyncio
    async def test_submit_unsupported_file_type(self, client):
        """Unsupported file type should return 422."""
        files = {"file": ("claim.exe", b"binary content", "application/octet-stream")}
        response = await client.post("/api/v1/claims/submit", files=files)
        assert response.status_code == 422
        assert "Unsupported file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_submit_empty_file(self, client):
        """Empty file should be rejected."""
        files = {"file": ("claim.pdf", b"", "application/pdf")}
        response = await client.post("/api/v1/claims/submit", files=files)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_idempotent_submission(self, client):
        """Same correlation_id should return same claim_id."""
        from app.infrastructure.ocr.engine import OCREngine
        from app.infrastructure.llm.groq_client import GroqClient

        corr_id = "test-idempotency-key-123"

        with patch.object(OCREngine, "extract_text", AsyncMock(return_value=MOCK_OCR_SUCCESS)), \
             patch.object(GroqClient, "extract_json", AsyncMock(return_value=MOCK_EXTRACTION)):

            files = {"file": ("claim.pdf", make_minimal_pdf_bytes(), "application/pdf")}
            data = {"correlation_id": corr_id}

            r1 = await client.post("/api/v1/claims/submit", files=files, data=data)
            files = {"file": ("claim.pdf", make_minimal_pdf_bytes(), "application/pdf")}
            r2 = await client.post("/api/v1/claims/submit", files=files, data=data)

        assert r1.status_code == 202
        assert r2.status_code == 202
        # Both should return the same claim_id
        assert r1.json()["claim_id"] == r2.json()["claim_id"]
        assert "idempotent" in r2.json()["message"].lower()


# ─────────────────────────────────────────────
# CLAIM RETRIEVAL
# ─────────────────────────────────────────────

class TestClaimRetrieval:
    @pytest_asyncio.fixture
    async def submitted_claim_id(self, client) -> str:
        """
        Submit a claim and return its ID.
        We only need the claim to exist in DB — we don't wait for full processing.
        """
        from app.infrastructure.ocr.engine import OCREngine
        from app.infrastructure.llm.groq_client import GroqClient
        import asyncio

        with patch.object(OCREngine, "extract_text", AsyncMock(return_value=MOCK_OCR_SUCCESS)), \
             patch.object(GroqClient, "extract_json", AsyncMock(return_value=MOCK_EXTRACTION)):

            files = {"file": ("claim.pdf", make_minimal_pdf_bytes(), "application/pdf")}
            response = await client.post("/api/v1/claims/submit", files=files)

        assert response.status_code == 202
        claim_id = response.json()["claim_id"]

        # Give background task a brief moment to start then cancel gracefully
        # We only need the claim record to exist in DB for retrieval tests
        await asyncio.sleep(0.2)
        return claim_id

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_get_claim_status(self, client, submitted_claim_id):
        """Should return claim status for valid claim_id."""
        response = await client.get(f"/api/v1/claims/{submitted_claim_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["claim_id"] == submitted_claim_id
        assert "status" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_get_nonexistent_claim(self, client):
        """Non-existent claim should return 404."""
        response = await client.get("/api/v1/claims/CLM-DOES-NOT-EXIST")
        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_list_claims(self, client):
        """List endpoint should return paginated results."""
        response = await client.get("/api/v1/claims")
        assert response.status_code == 200
        data = response.json()
        assert "claims" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["claims"], list)

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_list_claims_with_status_filter(self, client):
        """Status filter should work correctly."""
        response = await client.get("/api/v1/claims?status_filter=RECEIVED")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_list_claims_pagination_validation(self, client):
        """Invalid pagination params should return 422."""
        response = await client.get("/api/v1/claims?page=0")
        assert response.status_code == 422


# ─────────────────────────────────────────────
# HITL ENDPOINTS
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
# HITL ENDPOINTS
# ─────────────────────────────────────────────

class TestHITLEndpoints:
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_get_pending_hitl_empty(self, client):
        """Pending HITL list should return valid response."""
        response = await client.get("/api/v1/hitl/pending")
        assert response.status_code == 200
        data = response.json()
        assert "claims" in data

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_hitl_review_wrong_status(self, client):
        """Reviewing a non-HITL claim should return 422."""
        from app.infrastructure.ocr.engine import OCREngine
        from app.infrastructure.llm.groq_client import GroqClient

        with patch.object(OCREngine, "extract_text", AsyncMock(return_value=MOCK_OCR_SUCCESS)), \
             patch.object(GroqClient, "extract_json", AsyncMock(return_value=MOCK_EXTRACTION)):
            files = {"file": ("claim.pdf", make_minimal_pdf_bytes(), "application/pdf")}
            submit_resp = await client.post("/api/v1/claims/submit", files=files)

        assert submit_resp.status_code == 202
        claim_id = submit_resp.json()["claim_id"]

        # Very short sleep — just enough for DB record to exist
        await asyncio.sleep(0.1)

        review_payload = {
            "action": "APPROVE",
            "reviewer_id": "reviewer_001",
            "reviewer_notes": "Looks good.",
        }
        response = await client.post(f"/api/v1/hitl/{claim_id}/review", json=review_payload)
        # Should fail because status is RECEIVED, not HITL_REVIEW
        assert response.status_code == 422


# ─────────────────────────────────────────────
# POLICY INDEXING
# ─────────────────────────────────────────────

class TestPolicyIndexing:
    @pytest.mark.asyncio
    async def test_index_policy_success(self, client):
        """Policy indexing should succeed and return chunk count."""
        from app.infrastructure.vectorstore.chroma_store import PolicyVectorStore

        with patch.object(PolicyVectorStore, "index_policy", AsyncMock(return_value=5)):
            payload = {
                "policy_text": "This policy covers all medical expenses up to sum insured.",
                "policy_name": "Test Health Policy",
                "insurance_type": "HEALTH",
                "country": "IN",
                "company": "Test Insurance Ltd",
            }
            response = await client.post("/api/v1/policies/index", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "indexed"
        assert data["chunks_indexed"] == 5


# ─────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────

class TestAnalytics:
    @pytest.mark.asyncio
    async def test_analytics_summary(self, client):
        """Analytics endpoint should return status breakdown."""
        response = await client.get("/api/v1/analytics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "by_status" in data
        assert isinstance(data["by_status"], list)
