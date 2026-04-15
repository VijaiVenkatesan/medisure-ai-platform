# ClaimIQ Healthcare AI Platform
## Complete Enterprise Architecture — Open Source, India-First, Global Ready

---

## Platform Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│           CLAIMIQ HEALTHCARE AI PLATFORM v2.0                       │
│                                                                      │
│  Insurance Claims  │  Medical Records  │  Clinical Decision Support │
│  ─────────────────   ─────────────────   ──────────────────────────  │
│  OCR → Extract     │  EHR Integration  │  Drug Interaction Check    │
│  Validate          │  Summarization    │  Diagnosis Assist          │
│  Fraud Detection   │  Medical Coding   │  Treatment Protocol        │
│  HITL Review       │  Transcription    │  Risk Stratification       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Full System Architecture

```
                         ┌─────────────────────────────────────────┐
                         │           API GATEWAY (FastAPI)          │
                         │   /claims  /medical  /coding  /clinical  │
                         └──────────────────┬──────────────────────┘
                                            │
              ┌─────────────────────────────┼──────────────────────────────┐
              │                             │                              │
              ▼                             ▼                              ▼
  ┌─────────────────────┐    ┌──────────────────────────┐   ┌──────────────────────┐
  │  CLAIMS PIPELINE    │    │   MEDICAL RECORDS        │   │  CLINICAL AI         │
  │  (Current - v1)     │    │   PIPELINE (v2)          │   │  PIPELINE (v2)       │
  │                     │    │                          │   │                      │
  │  OCR Agent          │    │  Document Ingestion      │   │  Symptom Analysis    │
  │  Extraction Agent   │    │  Medical Summarization   │   │  Diagnosis Assist    │
  │  Validation Agent   │    │  ICD-10/CPT Coding       │   │  Drug Checker        │
  │  Policy Agent (RAG) │    │  Medical Transcription   │   │  Lab Result Interp.  │
  │  Fraud Agent        │    │  ABDM/HL7 FHIR Export    │   │  Radiology Assist    │
  │  Decision Agent     │    │  De-identification       │   │  Risk Scoring        │
  └─────────────────────┘    └──────────────────────────┘   └──────────────────────┘
              │                             │                              │
              └─────────────────────────────┼──────────────────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                         │         SHARED INFRASTRUCTURE        │
                         │                                      │
                         │  LangGraph (Orchestration)           │
                         │  Groq LLM (llama-3.3-70b-versatile) │
                         │  ChromaDB (RAG Vector Store)         │
                         │  PostgreSQL (Primary DB)             │
                         │  Redis (Task Queue + Cache)          │
                         │  MinIO (Document Storage)            │
                         └──────────────────────────────────────┘
```

---

## Module 1: Insurance Claims (Current — Deployed)

**Status: ✅ LIVE**

```
URL: https://claimiq-vijai.netlify.app
API: https://claimiq-api.onrender.com
```

**Agents:**
- OCR Agent → EasyOCR (local) / pypdf (cloud)
- Extraction Agent → llama-3.3-70b-versatile
- Validation Agent → IRDAI business rules
- Policy Agent → ChromaDB RAG
- Fraud Agent → Rule-based + LLM
- Decision Agent → Auto approve/reject/HITL

**India Support:**
- Ayushman Bharat, PM-JAY, PMFBY, ESIC, CGHS
- Aadhaar masking, PAN validation
- Hindi + English OCR

---

## Module 2: Medical Records AI (New — To Build)

### 2A. Medical Document Summarization

**Input:** Discharge summaries, OPD notes, prescriptions, lab reports (PDF/image)
**Output:** Structured medical summary with key findings

```python
# Agent Pipeline
class MedicalSummarizationAgent:
    """
    Summarizes complex medical documents into structured format.
    
    Supports:
    - Discharge summaries (all Indian hospitals)
    - OPD consultation notes
    - Specialist referral letters
    - Pathology/radiology reports
    - Prescription analysis
    """
    
    async def summarize(self, document_text: str, doc_type: str) -> MedicalSummary:
        prompt = f"""
        You are a medical document specialist. Summarize this {doc_type}:
        
        {document_text}
        
        Extract:
        1. Chief complaint / Reason for visit
        2. Diagnosis (primary + secondary) with ICD-10 codes
        3. Key findings (lab values, vitals, imaging)
        4. Medications prescribed (with dosage)
        5. Treatment given
        6. Follow-up instructions
        7. Risk factors identified
        8. Red flags (if any)
        
        Format as structured JSON.
        """
        return await llm.extract_json(prompt)
```

**Tech Stack (Free/Open Source):**
- LLM: Groq llama-3.3-70b-versatile
- OCR: EasyOCR (English + Hindi + Tamil + Telugu)
- PDF: pypdf + pdfplumber
- NLP: scispacy (medical NER)
- Standards: HL7 FHIR R4

---

### 2B. Medical Coding (ICD-10 + CPT + SNOMED)

**What it does:** Automatically assigns standard medical codes from clinical text.

```python
class MedicalCodingAgent:
    """
    Auto-codes diagnoses and procedures.
    
    Supported code systems:
    - ICD-10-CM (International — all countries)
    - ICD-10-PCS (Procedures)
    - CPT (USA)
    - SNOMED CT
    - LOINC (Lab tests)
    - India: ICD-10 as per ABDM standards
    """
    
    CODING_PROMPT = """
    You are a certified medical coder (CPC, CCS).
    
    Clinical text: {text}
    
    Assign the most accurate codes:
    
    PRIMARY DIAGNOSIS:
    - ICD-10-CM code
    - Description
    - Specificity (with/without complications)
    
    SECONDARY DIAGNOSES (comorbidities):
    - List each with ICD-10-CM code
    
    PROCEDURES PERFORMED:
    - CPT codes (if USA)
    - ICD-10-PCS codes
    - Description
    
    REASON: Explain why each code was selected.
    
    CONFIDENCE: Score 0-1 for each code.
    """
    
    async def code_document(self, clinical_text: str, 
                             country: str = "IN") -> CodingResult:
        # Step 1: Extract medical entities using scispacy
        entities = self.ner_model(clinical_text)
        
        # Step 2: RAG lookup against ICD-10 codebook
        relevant_codes = await self.vector_store.search(
            query=clinical_text,
            collection="icd10_codes",
            top_k=10
        )
        
        # Step 3: LLM assigns final codes
        return await self.llm.extract_json(
            self.CODING_PROMPT.format(text=clinical_text)
        )
```

**Free Resources to Index:**
- ICD-10-CM codes: CMS.gov (free download)
- SNOMED CT: SNOMED International (free for India)
- LOINC: loinc.org (free)

---

### 2C. Medical Transcription

**What it does:** Converts doctor's audio notes / dictation into structured clinical text.

```python
class MedicalTranscriptionAgent:
    """
    Transcribes and structures medical audio/text.
    
    Supports:
    - Doctor dictation (audio → text via Whisper)
    - Voice notes from ASHA workers
    - Telemedicine consultation notes
    - Structured output: SOAP format
    """
    
    async def transcribe_and_structure(self, 
                                        audio_file: str) -> SOAPNote:
        # Step 1: Whisper large-v3 for transcription
        # Free via Groq: whisper-large-v3
        raw_text = await self.groq_whisper.transcribe(audio_file)
        
        # Step 2: Structure as SOAP note via LLM
        soap = await self.llm.extract_json(f"""
        Convert this medical dictation to SOAP format:
        
        {raw_text}
        
        Return:
        {{
          "subjective": "Patient's complaints and history",
          "objective": "Vitals, exam findings, lab results",
          "assessment": "Diagnosis with ICD-10 codes",
          "plan": "Treatment, medications, follow-up"
        }}
        """)
        return soap
```

**Tech Stack:**
- Audio: Groq Whisper (free tier — 7,200 audio minutes/day)
- Languages: Hindi, Tamil, Telugu, Kannada, Bengali, English

---

## Module 3: Clinical Decision Support (New)

### 3A. Diagnosis Assistance

```python
class DiagnosisAssistAgent:
    """
    Suggests differential diagnoses based on symptoms.
    NOT a replacement for clinical judgment.
    Evidence-based, cites medical literature.
    
    India-specific:
    - Tropical diseases (Dengue, Malaria, Typhoid, Leptospirosis)
    - Nutritional deficiencies (Vit D, B12, Iron)
    - TB screening (India has highest TB burden)
    - Diabetes complications (India #2 globally)
    """
    
    async def suggest_diagnoses(self, symptoms: list[str],
                                 patient_history: dict,
                                 country: str = "IN") -> DiagnosisList:
        # RAG: retrieve relevant clinical guidelines
        guidelines = await self.vector_store.search(
            query=" ".join(symptoms),
            collection="clinical_guidelines",  # WHO, ICMR, NICE
            top_k=5
        )
        
        return await self.llm.complete(f"""
        Patient: {patient_history}
        Symptoms: {symptoms}
        Country: {country}
        
        Relevant guidelines: {guidelines}
        
        Provide differential diagnoses ranked by probability.
        Include: red flags to watch, recommended investigations,
        first-line treatment per {country} guidelines.
        
        IMPORTANT: This is decision SUPPORT only, 
        not a replacement for clinical judgment.
        """)
```

### 3B. Drug Interaction Checker

```python
class DrugInteractionAgent:
    """
    Checks for drug-drug, drug-food, drug-condition interactions.
    
    Data sources (free):
    - OpenFDA drug database
    - DrugBank (free academic license)
    - WHO Essential Medicines List
    - CDSCO India approved drugs list
    """
    
    async def check_interactions(self, 
                                  medications: list[str],
                                  conditions: list[str],
                                  patient_age: int) -> InteractionReport:
        pass
```

---

## Module 4: Standards & Compliance

### India — ABDM (Ayushman Bharat Digital Mission)

```python
class ABDMIntegrationService:
    """
    Integrates with India's national health digital infrastructure.
    
    Features:
    - ABHA (Ayushman Bharat Health Account) verification
    - Health Records sharing via PHR app
    - Consent management (patient consent before data sharing)
    - FHIR R4 compliant health records
    - NHA sandbox for development
    """
    
    BASE_URL = "https://sandbox.abdm.gov.in"
    
    async def verify_abha(self, abha_number: str) -> ABHAProfile:
        """Verify patient ABHA number and get linked records."""
        pass
    
    async def push_health_record(self, 
                                  fhir_bundle: dict,
                                  patient_abha: str) -> str:
        """Push structured health record to ABDM HIU."""
        pass
```

### International Standards

| Standard | Use Case | Implementation |
|----------|----------|----------------|
| HL7 FHIR R4 | Health record exchange | `fhirpy` library |
| DICOM | Radiology images | `pydicom` library |
| IHE profiles | Document sharing | Custom implementation |
| HIPAA (USA) | Data privacy | Field-level encryption |
| GDPR (EU) | Data privacy | Consent management |
| PDPA (Singapore) | Data privacy | Access controls |
| DPDP (India) | Data privacy | Aadhaar masking done |

---

## Module 5: Radiology AI

```python
class RadiologyAssistAgent:
    """
    Assists radiologists with preliminary findings.
    Open source models:
    - chest X-ray: CheXNet (densenet121)
    - CT scan: TotalSegmentator
    - Mammography: BreastAI
    
    India focus:
    - TB detection from chest X-ray (very high prevalence)
    - Bone density (osteoporosis common)
    """
    
    async def analyze_xray(self, image_path: str) -> RadiologyReport:
        # Step 1: Run CheXNet for pathology detection
        findings = self.chexnet_model.predict(image_path)
        
        # Step 2: LLM generates radiologist-style report
        report = await self.llm.complete(f"""
        CheXNet detected: {findings}
        
        Write a preliminary radiology report in standard format:
        TECHNIQUE, FINDINGS, IMPRESSION.
        Flag urgent findings requiring immediate attention.
        """)
        return report
```

---

## Complete Tech Stack (100% Free/Open Source)

### AI / LLM Layer
| Component | Technology | Why |
|-----------|-----------|-----|
| LLM (text) | Groq llama-3.3-70b-versatile | Free 14,400 req/day, fastest |
| LLM (fast) | Groq llama-3.1-8b-instant | Low latency tasks |
| Audio transcription | Groq Whisper large-v3 | Free, multilingual |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 | Free, local |
| Medical NER | scispacy + en_core_sci_lg | Free, clinical entities |
| Radiology | CheXNet (open weights) | Free TB/pneumonia detection |

### Orchestration
| Component | Technology |
|-----------|-----------|
| Agent pipeline | LangGraph (stateful, resumable) |
| Task queue | Celery + Redis |
| Workflow retry | Tenacity |
| Human-in-loop | Custom HITL (built) |

### Storage
| Component | Technology |
|-----------|-----------|
| Primary DB | PostgreSQL (Supabase free tier) |
| Vector store | ChromaDB (local) / Qdrant (cloud free) |
| Document store | MinIO (S3-compatible, free self-hosted) |
| Cache | Redis (Upstash free tier) |
| Search | Elasticsearch (Bonsai free tier) |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Uvicorn |
| Frontend | React + Vite (Netlify free) |
| Backend hosting | Render.com (free) |
| CI/CD | GitHub Actions (free) |
| Monitoring | Prometheus + Grafana (free) |
| Logging | Structured JSON → Loki (free) |

---

## Multi-Country Support Matrix

| Country | Insurance | Coding | Standards | Regulator | Language |
|---------|-----------|--------|-----------|-----------|----------|
| 🇮🇳 India | IRDAI, ABDM, PM-JAY | ICD-10 (ABDM) | FHIR R4 | NHA, IRDAI | Hindi, Tamil, Telugu... |
| 🇺🇸 USA | ACA, Medicare | ICD-10-CM, CPT | HL7 FHIR | CMS, FDA | English |
| 🇬🇧 UK | NHS, PMI | ICD-10 | SNOMED CT | MHRA, ICO | English |
| 🇦🇪 UAE | DHA, HAAD | ICD-10 | HL7 | MOH UAE | Arabic, English |
| 🇸🇬 Singapore | MediShield | ICD-10 | FHIR | MOH SG | English |
| 🇧🇩 Bangladesh | NHIS | ICD-10 | — | DGDA | Bengali |
| 🇳🇵 Nepal | NHIS | ICD-10 | — | DoHS | Nepali |

---

## Deployment Architecture (Production)

```
                    CLOUDFLARE (CDN + DDoS)
                           │
              ┌────────────┼────────────┐
              │            │            │
           NETLIFY      RENDER       SUPABASE
          (React UI)   (FastAPI)    (PostgreSQL)
              │            │
              │        UPSTASH
              │        (Redis)
              │
        USER BROWSER
        (laptop/mobile)
```

### For Scale (when free tier limits hit):
```
Replace Render → Railway ($5/mo) or AWS EC2 t3.small ($15/mo)
Replace Supabase → Neon.tech (free 3GB) or PlanetScale
Replace ChromaDB → Qdrant Cloud (free 1GB)
```

---

## Roadmap

### Phase 1 — Current (✅ Done)
- Insurance claims processing
- OCR + extraction + validation
- RAG policy checking
- Fraud detection
- HITL review
- Deployed: Netlify + Render

### Phase 2 — Medical Records (3-4 weeks)
- Medical document summarization
- ICD-10/CPT auto-coding
- Medical transcription (Whisper)
- ABDM FHIR integration
- Multi-language OCR (8 Indian languages)

### Phase 3 — Clinical AI (4-6 weeks)
- Diagnosis assistance
- Drug interaction checker
- Lab result interpretation
- Radiology assist (chest X-ray TB detection)
- Clinical guideline RAG (WHO + ICMR)

### Phase 4 — Enterprise (6-8 weeks)
- Multi-tenant architecture
- Role-based access (Doctor, Nurse, Admin, Auditor)
- HIPAA/GDPR/DPDP compliance module
- Real-time HL7 FHIR streams
- Hospital Information System (HIS) connectors
- WhatsApp bot for patient communication

---

## How to Extend the Current Platform

### Add Medical Summarization

**Step 1 — Add new agent:**
```python
# app/agents/medical_summary_agent.py
async def medical_summary_agent(state: WorkflowState) -> WorkflowState:
    text = state.ocr_result.raw_text
    result = await llm.extract_json(MEDICAL_SUMMARY_PROMPT.format(text=text))
    state.medical_summary = MedicalSummary(**result)
    return state
```

**Step 2 — Add to LangGraph workflow:**
```python
workflow.add_node("medical_summary", medical_summary_agent)
workflow.add_edge("extract", "medical_summary")
workflow.add_edge("medical_summary", "validate")
```

**Step 3 — Add API route:**
```python
@router.post("/medical/summarize")
async def summarize_medical_record(file: UploadFile):
    # same pattern as claims/submit
    pass
```

---

## Current Platform Issues & Fixes

### Issue 1: Scanned PDF fails on cloud
**Cause:** Cloud uses pypdf which only reads text-layer PDFs.
**Fix:** Use a text-layer PDF (generated digitally, not scanned).
**Workaround:** Run locally for scanned PDFs (EasyOCR works).

### Issue 2: Dashboard blank screen
**Fix:** Applied — added error state + retry button + empty state.

### Issue 3: Slow tab switching
**Fix:** React Router lazy loading — add to App.jsx:
```jsx
const Dashboard = lazy(() => import('./pages/Dashboard'))
// wrap routes in <Suspense>
```

### Issue 4: Logs location
**Local:** `D:\insurance-claims-platform\logs\claims.log`
**Render:** Render dashboard → your service → **Logs** tab
**Real-time:** Render dashboard → **Logs** → Live tail ✓

---

## Quick Start for Phase 2

```cmd
# Clone and setup
git clone https://github.com/VijaiVenkatesan/insurance-claims-platform
cd insurance-claims-platform

# Install additional medical AI packages
pip install scispacy pdfplumber python-docx

# Download medical NER model
python -m spacy download en_core_web_sm

# Run with medical modules enabled
python -m uvicorn app.main:app --reload --port 8000
```
