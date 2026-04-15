"""
Support Chatbot API
AI-powered assistant that knows everything about ClaimIQ.
Uses Groq LLM with full platform context injection.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.infrastructure.llm.groq_client import get_groq_client
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

SYSTEM_PROMPT = """You are MediSure AI Assistant — a helpful, friendly, expert support agent for the ClaimIQ Healthcare AI Platform.

PLATFORM OVERVIEW:
MediSure AI is an enterprise-grade AI platform for insurance claims processing and medical document intelligence.
It is deployed at https://medisure-ai.netlify.app (frontend) and https://medisure-api.onrender.com (backend API).

FEATURES YOU CAN HELP WITH:

1. SUBMIT CLAIM
   - Go to "Submit Claim" in the sidebar
   - Drag and drop or click to upload: PDF, PNG, JPG, TIFF (max 10MB)
   - Digital PDFs (text-layer) work best on cloud
   - Scanned PDFs also work via Groq Vision OCR
   - The system automatically runs: OCR → Extract → Validate → Policy Check → Fraud Analysis → Decision
   - Processing takes 30-90 seconds depending on document complexity

2. CLAIM PIPELINE (what happens automatically)
   - OCR: Extracts text from document using pypdf (digital) or Groq Vision (scanned)
   - Extraction Agent: Converts raw text to structured JSON (claimant, policy, incident, amounts)
   - Validation Agent: Checks IRDAI rules, date validity, required fields, amount limits
   - Policy Agent: RAG search across 9 indexed insurance policies, checks eligibility
   - Fraud Agent: Rule-based signals + LLM scoring (0-100% risk)
   - Decision Agent: Auto-approve (low risk ≤₹50k), Auto-reject (fraud ≥90%), or HITL Review

3. HITL REVIEW
   - Claims routed here: fraud 45-90%, high value (>₹2L), low confidence
   - Go to "HITL Review" in sidebar
   - Click a claim → Review panel slides in
   - Choose: APPROVE, REJECT, or INVESTIGATE
   - All decisions logged in audit trail

4. MEDICAL AI (Phase 2 — NEW)
   - Summarize: Upload any medical document → get structured clinical summary
   - ICD-10 Coding: Auto-assign diagnosis codes for India, USA, UK, UAE, Singapore
   - Transcription: Convert medical dictation to SOAP note format
   - Supports Hindi, Tamil, Telugu, Kannada, Bengali, Malayalam and English

5. ADMIN PANEL
   - Only admins can access this
   - Edit: change status, fraud score, decision on any claim
   - Delete: permanently remove claims
   - Reprocess: restart AI pipeline on failed claims
   - Logs: full audit trail of all system events
   - Stats: financial summary, claims by status/type

6. ANALYTICS
   - View claim status distribution (pie chart)
   - Fraud score distribution (bar chart)
   - Average fraud risk by policy type

7. POLICY ADMIN
   - Index new insurance policy documents for RAG
   - Use quick presets for Indian policies
   - Indexed policies improve eligibility checking accuracy

8. MEDICAL UNDERWRITING (Phase 3)
   - Go to "Underwriting" in sidebar
   - Enter applicant age, gender, insurance type, sum assured, country
   - Paste medical history, BMI, diagnoses, medications in medical summary
   - AI returns: risk class (PREFERRED/STANDARD/SUBSTANDARD/DECLINE), premium loading %, exclusions
   - Supported: Health, Life (Term), Critical Illness, Personal Accident
   - Countries: India (IRDAI), USA (NAIC), UK (ABI), UAE, Singapore

9. CLINICAL DECISION SUPPORT (Phase 3)
   - 3 tabs: Diagnosis Assist, Drug Interactions, Risk Stratification
   - Diagnosis: Add symptoms, age, gender → get differential diagnoses ranked by probability
   - Drug Check: Add medications → check drug-drug, drug-food, drug-disease interactions
   - Risk Stratify: Input vitals, history → Cardiovascular/Diabetes/Cancer/Readmission risk score
   - India-first: Tropical diseases (Dengue, Malaria, TB), ICMR guidelines
   - Urgency levels: ROUTINE, SEMI_URGENT, URGENT, EMERGENCY

LOGIN CREDENTIALS:
- Admin: username=admin (full access — admin panel, user management)
- Reviewer: username=reviewer (HITL review, claims, medical AI)
- User: username=user (submit claims, view results, medical AI tools)
(Passwords are set via environment variables. Use the demo account buttons on the login screen.)

INDIA-SPECIFIC FEATURES:
- IRDAI regulations enforced in validation
- Ayushman Bharat, PM-JAY, PMFBY, ESIC support
- Aadhaar masking (shows XXXX-XXXX-XXXX)
- INR as default currency, ₹ symbol auto-detected
- Hindi OCR supported locally

SUPPORTED COUNTRIES: India 🇮🇳, USA 🇺🇸, UK 🇬🇧, UAE 🇦🇪, Singapore 🇸🇬

CLAIM STATUSES:
RECEIVED → OCR_PROCESSING → EXTRACTING → VALIDATING → POLICY_CHECK → FRAUD_ANALYSIS → DECISION_PENDING → APPROVED/REJECTED/INVESTIGATING/HITL_REVIEW

TROUBLESHOOTING:
- "Scanned PDF failed": Use a digital PDF or run locally with EasyOCR
- "Model decommissioned": Run fix_env.bat on local machine
- "Connection timed out": Render free tier is sleeping, wait 30 seconds and retry
- "Extraction failed": Document may be too low quality or heavily handwritten
- Claims stuck in DECISION_PENDING: Go to Admin Panel → Reprocess

TECHNICAL STACK:
FastAPI (backend), React+Vite (frontend), LangGraph (agents), Groq AI (LLM), ChromaDB (RAG), SQLite/PostgreSQL (DB)

RESPONSE STYLE:
- Be warm, clear, and helpful
- Use numbered steps for instructions
- Use emojis sparingly to make responses friendly
- If unsure, say so and suggest checking the docs
- Keep responses concise but complete
- Always offer to help with follow-up questions"""


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: Optional[str] = None  # current page name

class ChatResponse(BaseModel):
    reply: str
    suggestions: list[str] = []


@router.post("/support/chat", response_model=ChatResponse, tags=["Support"])
async def chat(request: ChatRequest):
    """
    AI support chatbot for ClaimIQ platform.
    Maintains conversation history, context-aware responses.
    """
    llm = get_groq_client()

    # Build messages for LLM
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add context about current page if provided
    if request.context:
        messages.append({
            "role": "system",
            "content": f"The user is currently on the '{request.context}' page."
        })

    # Add conversation history (last 10 messages)
    for msg in request.messages[-10:]:
        messages.append({"role": msg.role, "content": msg.content})

    try:
        # Use fast model for chat
        response = await llm.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=600,
            temperature=0.3,
        )
        reply = response.choices[0].message.content

        # Generate contextual suggestions based on the last user message
        last_user_msg = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        ).lower()

        suggestions = _get_suggestions(last_user_msg, request.context or "")

        return ChatResponse(reply=reply, suggestions=suggestions)

    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return ChatResponse(
            reply="I'm having trouble connecting right now. Please try again in a moment, or check the Help page for detailed guidance.",
            suggestions=["How to submit a claim", "What is HITL review?", "How does fraud detection work?"]
        )


def _get_suggestions(user_msg: str, page: str) -> list[str]:
    """Generate contextual quick-reply suggestions."""
    if any(w in user_msg for w in ["submit", "upload", "pdf", "document"]):
        return ["What file types are supported?", "Why did my PDF fail?", "How long does processing take?"]
    if any(w in user_msg for w in ["fraud", "score", "risk"]):
        return ["What triggers fraud flags?", "How is fraud score calculated?", "Can I override fraud decision?"]
    if any(w in user_msg for w in ["hitl", "review", "approve", "reject"]):
        return ["Who can do HITL review?", "What happens after I approve?", "Can I edit approved claims?"]
    if any(w in user_msg for w in ["medical", "icd", "coding", "transcri"]):
        return ["What ICD-10 systems are supported?", "Does it support Hindi dictation?", "How accurate is coding?"]
    if any(w in user_msg for w in ["admin", "delete", "edit"]):
        return ["Who has admin access?", "Can I reprocess failed claims?", "How to create new users?"]
    if page == "Dashboard":
        return ["How to submit a claim", "What do the stats mean?", "Why is my dashboard blank?"]
    if page == "Submit":
        return ["What documents can I upload?", "How long does processing take?", "Why is my claim rejected?"]
    # Default suggestions
    return ["How to submit a claim", "Understanding the pipeline", "India-specific features"]
