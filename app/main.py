"""
Main FastAPI application entry point.
Handles startup, middleware, CORS, and route registration.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import settings
from app.core.logging import setup_logging, get_logger, set_correlation_id
from app.infrastructure.db.models import init_db

setup_logging(level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.
    IMPORTANT: Port must bind BEFORE any heavy model loading.
    All slow tasks run in background after startup completes.
    """
    import asyncio

    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # ── STEP 1: DB init (fast, must complete before serving) ──
    await init_db()
    logger.info("Database ready")

    # ── STEP 2: Yield immediately so Render detects the open port ──
    # Background tasks run AFTER the server is already accepting requests
    logger.info("Application startup complete — server accepting requests")

    # Schedule heavy init as a background task (non-blocking)
    asyncio.create_task(_background_startup())

    yield

    logger.info("Application shutting down")


async def _background_startup():
    """
    Heavy initialisation that runs AFTER the server is live.
    This prevents Render's port-binding timeout.
    """
    import asyncio
    import os

    # Small delay to ensure server is fully up
    await asyncio.sleep(2)

    logger.info("Background startup: initialising services...")

    # Vector store
    try:
        from app.infrastructure.vectorstore.chroma_store import get_vector_store
        vs = get_vector_store()
        stats = vs.get_stats()
        logger.info(f"Vector store ready: {stats}")
    except Exception as e:
        logger.warning(f"Vector store init warning: {e}")

    # Pre-compile LangGraph workflow
    try:
        from app.workflows.claims_workflow import get_workflow
        get_workflow()
        logger.info("LangGraph workflow compiled")
    except Exception as e:
        logger.warning(f"Workflow compile warning: {e}")

    # Index default policies only if vector store is empty
    try:
        await _index_default_policies()
    except Exception as e:
        logger.warning(f"Default policy indexing warning: {e}")

    # Ensure default users exist + refresh password hashes
    try:
        from app.api.routes.auth import ensure_default_users
        await ensure_default_users()
    except Exception as e:
        logger.warning(f"User setup warning: {e}")

    logger.info("Background startup complete — all services ready")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Insurance Claims Processing Platform
    
    Enterprise-grade AI-powered insurance claims processing with:
    - **OCR** document extraction (English + Hindi)
    - **Multi-agent** LLM pipeline (Groq Llama3/Mixtral)
    - **RAG-based** policy eligibility checking
    - **Fraud detection** (rule-based + LLM)
    - **Human-in-the-loop** review workflow
    - **Full audit trail** for compliance
    
    ### India Focus
    Supports IRDAI regulations, Ayushman Bharat, PMFBY, LIC, and all major Indian insurers.
    Also supports US, UK, UAE, Singapore insurance.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─────────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────────

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Inject correlation ID into every request."""
    corr_id = request.headers.get("X-Correlation-ID") or set_correlation_id()
    start_time = time.monotonic()

    response = await call_next(request)

    elapsed = (time.monotonic() - start_time) * 1000
    response.headers["X-Correlation-ID"] = corr_id
    response.headers["X-Processing-Time-Ms"] = str(round(elapsed, 2))
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

from app.api.routes.claims  import router as claims_router
from app.api.routes.medical import router as medical_router
from app.api.routes.admin   import router as admin_router
from app.api.routes.auth    import router as auth_router
from app.api.routes.support     import router as support_router
from app.api.routes.enterprise  import router as enterprise_router

app.include_router(claims_router,  prefix=settings.API_PREFIX)
app.include_router(medical_router, prefix=settings.API_PREFIX)
app.include_router(admin_router,   prefix=settings.API_PREFIX)
app.include_router(auth_router,    prefix=settings.API_PREFIX)
app.include_router(support_router,    prefix=settings.API_PREFIX)
app.include_router(enterprise_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": f"{settings.API_PREFIX}/health",
    }


# ─────────────────────────────────────────────
# DEFAULT POLICY INDEXING
# ─────────────────────────────────────────────

async def _index_default_policies():
    """Index built-in insurance policy templates for India and international."""
    from app.infrastructure.vectorstore.chroma_store import get_vector_store
    from app.models.schemas import InsuranceType, Country

    vs = get_vector_store()
    stats = vs.get_stats()

    if stats.get("total_chunks", 0) > 0:
        logger.info("Policies already indexed, skipping default indexing")
        return

    policies = [
        {
            "name": "Standard Indian Health Insurance Policy",
            "type": InsuranceType.HEALTH,
            "country": Country.INDIA,
            "company": "Generic IRDAI Compliant",
            "text": """
SECTION 1 - COVERAGE
This health insurance policy covers hospitalization expenses including:
- Room and boarding charges up to the sub-limit specified
- Surgical fees and operation theater charges
- Intensive Care Unit (ICU) charges
- Doctor and specialist consultation fees during hospitalization
- Diagnostic tests, investigations and medical examinations
- Medicines, drugs and consumables during hospitalization
- Ambulance charges up to INR 5,000 per hospitalization

SECTION 2 - PRE-HOSPITALIZATION AND POST-HOSPITALIZATION
- Pre-hospitalization expenses covered for 30 days before admission
- Post-hospitalization expenses covered for 60 days after discharge
- Domiciliary hospitalization covered if patient cannot be moved

SECTION 3 - EXCLUSIONS
The following are NOT covered under this policy:
- Pre-existing diseases during the first 2 years of the policy
- Cosmetic or plastic surgery unless required due to accident
- Treatment for infertility or assisted reproduction
- Self-inflicted injuries or suicide attempts
- Injuries due to war, nuclear hazards, or civil commotion
- Experimental treatments or investigational therapies
- Dental treatment unless due to accident
- Maternity expenses (unless specifically included as a rider)
- Obesity treatment and weight reduction programs
- Spectacles, contact lenses, hearing aids

SECTION 4 - CLAIM PROCEDURE
All claims must be filed within 30 days of discharge (cashless) or 15 days of payment (reimbursement).
Required documents:
- Duly filled claim form
- Original bills and receipts
- Discharge summary from hospital
- Investigation reports
- Doctor's prescription and case history
- Aadhaar card / PAN card of insured
- Policy document copy

SECTION 5 - CASHLESS FACILITY
Cashless claims are available at network hospitals.
For planned hospitalization: notify TPA 48 hours in advance.
For emergency: notify TPA within 24 hours of admission.

SECTION 6 - INDIA SPECIFIC PROVISIONS
Ayushman Bharat / PM-JAY beneficiaries: Additional government scheme benefits apply.
IRDAI grievance: In case of dispute, contact IRDAI at igms.irda.gov.in or toll-free 155255.
All disputes subject to Indian jurisdiction and applicable IRDAI regulations.
""",
        },
        {
            "name": "Motor Insurance - Comprehensive Policy India",
            "type": InsuranceType.MOTOR,
            "country": Country.INDIA,
            "company": "Generic IRDAI Motor",
            "text": """
SECTION 1 - COVERAGE (OWN DAMAGE)
Comprehensive motor insurance covers:
- Accidental damage to the insured vehicle
- Theft or attempted theft of the vehicle
- Fire, self-ignition, lightning damage
- Natural calamities: flood, cyclone, earthquake, landslide, rockslide
- Transit damage (by rail, road, air, or water)
- Malicious damage and riot/strike damage

SECTION 2 - THIRD PARTY LIABILITY
Unlimited liability for third party bodily injury or death.
Third party property damage up to INR 7.5 lakh.
Mandatory under Motor Vehicles Act 1988.

SECTION 3 - EXCLUSIONS
- Damage caused by unlicensed driver
- Damage while driving under influence of alcohol or drugs
- Damage outside the geographical area (India)
- Mechanical/electrical breakdown
- Depreciation and wear and tear
- Overloading or using vehicle for unlawful purposes
- Consequential losses

SECTION 4 - CLAIM PROCEDURE
For accidents: File FIR with police within 24 hours for third party claims.
Notify insurer/surveyor within 48 hours of accident.
Do not repair vehicle before survey unless for safety reasons.
Required documents:
- Claim form (duly filled)
- Copy of driving license
- Copy of RC (Registration Certificate)
- FIR copy (for theft/third party)
- Repair estimate from authorized workshop
- Original bills after repair

SECTION 5 - IDV (INSURED DECLARED VALUE)
Claim settlement based on IDV minus depreciation.
Total loss if repair cost exceeds 75% of IDV.
Age-based depreciation schedule as per IRDAI guidelines.

SECTION 6 - CASHLESS REPAIRS
Available at authorized network garages across India.
List available on insurer website and mobile app.
""",
        },
        {
            "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY) - Crop Insurance",
            "type": InsuranceType.CROP,
            "country": Country.INDIA,
            "company": "Government of India Scheme",
            "text": """
PMFBY CROP INSURANCE SCHEME

SECTION 1 - ELIGIBLE CROPS
All food crops, oilseeds, and commercial/horticultural crops notified by state governments.
Coverage available for Kharif, Rabi, and annual commercial crops.

SECTION 2 - COVERED RISKS
- Yield losses due to non-preventable risks:
  * Natural fire and lightning
  * Storm, hailstorm, cyclone, typhoon, flood, inundation
  * Pest and disease
  * Drought, dry spells
  * Landslide in limited areas
- Post-harvest losses for 14 days for cut and spread crops
- Localized calamities for hailstorm, landslide, inundated crops

SECTION 3 - PREMIUM RATES
Farmer premium: Maximum 2% for Kharif, 1.5% for Rabi food crops
Government subsidy covers balance actuarial premium
No cap on government subsidy

SECTION 4 - CLAIM PROCEDURE
Notify crop loss within 72 hours via:
- Crop Insurance App
- Toll-free: 14447
- Insurance company portal
Crop cutting experiments conducted by state government
Claims settled based on yield data comparison

SECTION 5 - SUM INSURED
Based on Scale of Finance for the crop
Minimum: Cost of cultivation per hectare
Maximum: Market value of produce

SECTION 6 - ELIGIBILITY
All farmers (tenant/sharecropper/owner) growing notified crops
Loanee farmers: Mandatory enrollment through bank
Non-loanee farmers: Voluntary enrollment through bank/CSC/portal
""",
        },
        {
            "name": "International Travel Insurance - Worldwide Cover",
            "type": InsuranceType.TRAVEL,
            "country": Country.OTHER,
            "company": "Generic International",
            "text": """
INTERNATIONAL TRAVEL INSURANCE POLICY

SECTION 1 - MEDICAL EMERGENCY COVERAGE
- Emergency medical treatment and hospitalization abroad
- Medical evacuation and repatriation to home country
- Emergency dental treatment up to USD 500
- Prescription medication costs during covered emergency

SECTION 2 - TRIP CANCELLATION/INTERRUPTION
- Covered reasons: illness, injury, death, natural disaster
- Reimbursement of non-refundable trip costs
- Additional accommodation and transport costs if trip interrupted

SECTION 3 - BAGGAGE AND PERSONAL BELONGINGS
- Lost, stolen, or damaged baggage up to the limit
- Baggage delay: compensation after 12-hour delay
- Electronics and valuables covered up to sub-limit

SECTION 4 - EXCLUSIONS
- Pre-existing medical conditions (unless declared and endorsed)
- Travelling against medical advice
- High-risk activities (unless adventure sports rider purchased)
- War zones and countries under travel advisories
- Travelling to seek medical treatment
- Pandemic/epidemic exclusions (COVID-19 terms vary)

SECTION 5 - CLAIM PROCEDURE
Medical claims: Contact 24/7 emergency assistance line immediately
All claims must be filed within 30 days of return
Required: original bills, medical reports, boarding passes, passport copy

SECTION 6 - INDIA OUTBOUND TRAVEL
For Indian travellers: INR premium policy, USD benefits
FEMA compliance for foreign currency transactions
""",
        },
    ]

    for policy in policies:
        try:
            await vs.index_policy(
                policy_text=policy["text"],
                policy_name=policy["name"],
                insurance_type=policy["type"],
                country=policy["country"],
                company=policy.get("company"),
            )
        except Exception as e:
            logger.warning(f"Failed to index policy {policy['name']}: {e}")

    logger.info(f"Default policies indexed: {len(policies)} policies")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
