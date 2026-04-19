# MediSure AI — Healthcare Intelligence Platform

[![CI/CD](https://github.com/VijaiVenkatesan/medisure-ai-platform/actions/workflows/deploy.yml/badge.svg)](https://github.com/VijaiVenkatesan/medisure-ai-platform/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> Enterprise-grade multi-agent AI platform for insurance claims, medical document intelligence, clinical decision support, and medical underwriting. India-first. 100% open-source. Free to deploy.

---

## Live URLs

| Service | URL |
| --- | --- |
| **Frontend (Cloudflare Pages)** | https://medisure-ai-platform.pages.dev |
| **Backend API (Render)** | https://medisure-api-vyx1.onrender.com |
| **API Docs (Swagger)** | https://medisure-api-vyx1.onrender.com/docs |
| **Health Check** | https://medisure-api-vyx1.onrender.com/api/v1/health |
| **Source Code** | https://github.com/VijaiVenkatesan/medisure-ai-platform |

> Render free tier sleeps after 15 min idle. First request takes ~30 seconds to wake. Subsequent requests are fast. The UI shows an automatic wake-up banner.

---

## Login Credentials

| Role | Username | Password | What they can do |
| --- | --- | --- | --- |
| **Admin** | `admin` | env: `ADMIN_PASSWORD` | Everything — all pages, edit/delete claims, manage users |
| **Reviewer** | `reviewer` | env: `REVIEWER_PASSWORD` | HITL review, claims, medical AI, underwriting, clinical |
| **User** | `user` | env: `USER_PASSWORD` | Submit claims, view results, medical AI tools |

---

## Platform Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        MEDISURE AI PLATFORM v2.0                         │
│                                                                           │
│  BROWSER ──────────────────────────────────────────────────────────────  │
│     │                                                                     │
│     ▼                                                                     │
│  CLOUDFLARE PAGES (React + Vite)   RENDER.COM (FastAPI + Python 3.11)   │
│  medisure-ai-platform.pages.dev ─► medisure-api-vyx1.onrender.com       │
│  ├── Global CDN (300+ locations)        │  JWT auth + HTTPS              │
│  ├── Unlimited builds (free)       ┌────┴────────────────────────────┐   │
│  └── SPA via ui/public/_redirects  │           GROQ AI CLOUD         │   │
│                                    │  llama-3.3-70b-versatile         │   │
│                                    │  llama-3.1-8b-instant            │   │
│                                    │  llama-4-scout-17b (vision OCR)  │   │
│                                    │  whisper-large-v3  (audio STT)   │   │
│                                    └─────────────────────────────────┘    │
│                                         │                                 │
│                                    ┌────┴───────────┐  ┌──────────────┐  │
│                                    │  SQLite / PG   │  │ ChromaDB RAG │  │
│                                    │  Claims        │  │ 180+ chunks  │  │
│                                    │  Users + Auth  │  │ 9 policies   │  │
│                                    │  Audit Logs    │  └──────────────┘  │
│                                    └────────────────┘                    │
│                                                                           │
│  GITHUB ─── source of truth, CI/CD, auto-deploys both services           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## All 4 Phases

### Phase 1 — Insurance Claims Processing ✅ LIVE

**New: OCR Review & Edit** — upload document → AI extracts data → you review & correct before submitting to pipeline.

```
UPLOAD PDF/IMAGE
      │
      ▼
 OCR Node ──────────────────────────────────────────────────────────────
  Digital PDF → pypdf text layer (fast, accurate)
  Scanned PDF → Groq Vision (llama-4-scout) via base64 encoding
  Image       → Groq Vision → full text extraction
  Languages   → English + Hindi (Devanagari detection)
      │
      ▼
 Extraction Agent (llama-3.3-70b-versatile)
  raw text → structured JSON
  Claimant info, policy details, incident data, claimed amounts
  ICD-10 codes (if present in document)
      │
      ▼
 Validation Agent (rule-based, no LLM call)
  IRDAI rules, required fields, date logic, policy lapse check
  Amount limits, Indian phone/Aadhaar/PAN format
  Motor: vehicle number required
  Health: hospital name required (IRDAI mandate)
      │
      ├── 3+ critical errors ──► SKIP → Decision (auto-reject)
      ▼
 Policy Agent (ChromaDB RAG + llama-3.3-70b)
  Semantic search → top 6 policy chunks
  LLM eligibility check → Y/N + cited clauses + exclusions
      │
      ▼
 Fraud Agent (rule-based + llama-3.1-8b)
  Rules: early claim (<30d), round amounts, ghost hospital
  LLM pattern analysis → fraud_score 0.0–1.0
      │
      ├── score ≥ 0.90 ──────────────────────────► AUTO REJECT
      ├── score ≥ 0.75 ──────────────────────────► INVESTIGATE → HITL
      ▼
 Decision Agent (deterministic + llama-3.3-70b)
  Auto-approve: low risk + amount ≤ ₹50,000
  Auto-reject: fraud ≥ 90% OR 3+ critical errors
  HITL: amount > ₹2L, fraud 45-90%, confidence < 65%
      │
      └──► APPROVED | REJECTED | HITL_REVIEW | INVESTIGATING
```

**India Compliance:** IRDAI, Ayushman Bharat, PM-JAY, PMFBY, ESIC, CGHS

### Phase 2 — Medical Document Intelligence ✅ LIVE

| Feature | What it does |
| --- | --- |
| **Medical Summarization** | Any document (discharge summary, OPD, lab, prescription) → structured clinical summary with diagnoses, medications, vitals, lab results, red flags |
| **ICD-10 Auto-Coding** | Clinical text or document → ICD-10 codes with confidence, CPT (USA), coding rationale, query flags for physician |
| **SOAP Transcription** | Dictation text or audio file → structured SOAP note (Subjective/Objective/Assessment/Plan) via Groq Whisper |
| **Multi-language** | Hindi, Tamil, Telugu, Kannada, Bengali, Malayalam, English (90+ languages for audio) |
| **Country support** | India (ABDM ICD-10), USA (ICD-10-CM + CPT), UK (NHS), UAE, Singapore |

### Phase 3 — Clinical Decision Support & Underwriting ✅ LIVE

#### Medical Underwriting

* Risk classes: PREFERRED / STANDARD / SUBSTANDARD 1-3 / DECLINE
* Premium loading %, specific exclusions with duration and rationale
* Medical requirements (echo, treadmill, blood work)
* India (IRDAI) / USA (NAIC) / UK (ABI) regulatory compliance
* Supports: Health, Life (Term), Critical Illness, Personal Accident

#### Clinical Decision Support

* **Diagnosis Assist:** Differential diagnoses ranked by probability with supporting/against features
* **Drug Interactions:** CONTRAINDICATED / MAJOR / MODERATE / MINOR + renal/hepatic dosing
* **Risk Stratification:** Cardiovascular, Diabetes, Cancer, Readmission risk with 10-year % risk
* India-first: Dengue, Malaria, TB, Typhoid, nutritional deficiencies in differential

### Phase 4 — Enterprise Platform 🔜 Roadmap

* Multi-tenant SaaS architecture
* HIPAA / GDPR / DPDP (India) compliance module
* Real-time HL7 FHIR R4 health record streaming
* HIS / EMR connector framework
* WhatsApp / SMS patient communication bot
* Radiology AI (chest X-ray TB detection via CheXNet)

---

## All 5 Modules

| Module | Phase | Status | API Prefix |
| --- | --- | --- | --- |
| Insurance Claims | Phase 1 | ✅ Live | `/api/v1/claims` |
| Medical Document Intelligence | Phase 2 | ✅ Live | `/api/v1/medical` |
| Medical Underwriting | Phase 3 | ✅ Live | `/api/v1/underwriting` |
| Clinical Decision Support | Phase 3 | ✅ Live | `/api/v1/clinical` |
| Enterprise / FHIR / HIS | Phase 4 | 🔜 Roadmap | `/api/v1/enterprise` |

---

## Complete UI Pages

| Page | Route | Role | Description |
| --- | --- | --- | --- |
| Login | `/login` | All | JWT auth, demo account buttons, role-colored |
| Dashboard | `/` | All | KPI cards, recent claims, quick links, error+retry |
| Submit Claim | `/submit` | All | Drag-drop upload, live pipeline steps, auto-refresh |
| OCR Review | `/ocr-review` | All | Upload → AI extracts → **user reviews & corrects** → submit (prevents wrong amounts) |
| All Claims | `/claims` | All | Searchable, filterable table, pagination |
| Claim Detail | `/claims/:id` | All | Full data, fraud gauge, pipeline tracker, audit trail |
| HITL Review | `/hitl` | Reviewer+ | Queue list, slide-in panel, approve/reject/investigate |
| Analytics | `/analytics` | All | Pie + bar charts, fraud distribution |
| Policy Admin | `/policies` | All | Index policies for RAG, quick presets |
| Medical AI | `/medical` | All | Summarize, ICD-10 code, SOAP transcription |
| Underwriting | `/underwriting` | All | Risk assessment, loading %, exclusions |
| Clinical DSS | `/clinical` | All | Diagnosis, drug interactions, risk stratification |
| Admin Panel | `/admin` | Admin | Edit/delete/reprocess claims, logs, stats |
| Help & Docs | `/help` | All | Full step-by-step guide, all features |
| About | `/about` | All | Platform info, roadmap, architecture |
| AI Chatbot | (floating) | All | Context-aware support, quick suggestions |

---

## Tech Stack (100% Free & Open Source)

| Layer | Technology |
| --- | --- |
| LLM Primary | Groq `llama-3.3-70b-versatile` |
| LLM Fast | Groq `llama-3.1-8b-instant` |
| Vision OCR | Groq `meta-llama/llama-4-scout-17b-16e-instruct` |
| Audio STT | Groq `whisper-large-v3` |
| Agent Pipeline | LangGraph (stateful, resumable) |
| Vector RAG | ChromaDB 0.4.24 |
| Backend | FastAPI + Uvicorn + SQLAlchemy async |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Database | SQLite (dev) → PostgreSQL (prod) |
| Frontend | React 18 + Vite |
| Animations | Framer Motion |
| Charts | Recharts |
| Icons | Lucide React |
| Deploy Backend | Render.com (free) |
| Deploy Frontend | **Cloudflare Pages (free, unlimited builds)** |
| CI/CD | GitHub Actions |

---

## Local Development

### Prerequisites

```
Python 3.11+  →  https://python.org
Node.js 20+   →  https://nodejs.org
Groq API key  →  https://console.groq.com (free, no credit card)
```

### Setup

```
git clone https://github.com/VijaiVenkatesan/medisure-ai-platform.git
cd medisure-ai-platform

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
notepad .env
```

Set in `.env`:

```
GROQ_API_KEY=gsk_your_actual_key_here
SECRET_KEY=any-long-random-string-at-least-32-chars
GROQ_MODEL_PRIMARY=llama-3.3-70b-versatile
GROQ_MODEL_FAST=llama-3.1-8b-instant
```

```
python -m scripts.init_db --seed
python -m scripts.seed_policies

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

New terminal:

```
cd ui
npm install
npm run dev
```

Open: **http://localhost:5173** → login with admin account (use demo button on login screen)

---

## Cloud Deployment

### Step 1: GitHub repository

Repo is already set up at: `https://github.com/VijaiVenkatesan/medisure-ai-platform`

### Step 2: Deploy Backend on Render

1. https://render.com → **New** → **Web Service**
2. Connect `VijaiVenkatesan/medisure-ai-platform`
3. Settings:

| Field | Value |
| --- | --- |
| Name | `medisure-api` |
| Region | Singapore |
| Branch | `main` |
| Runtime | Python 3 |
| Build Command | `pip install --upgrade pip && pip install -r requirements-render.txt && python -m scripts.init_db --seed && python -m scripts.seed_policies` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Plan | Free |

4. Environment Variables:

| Key | Value |
| --- | --- |
| `GROQ_API_KEY` | your key |
| `SECRET_KEY` | long random string |
| `RENDER` | `true` |
| `OCR_ENGINE` | `pypdf` |
| `LOG_FILE` | *(blank)* |
| `CORS_ORIGINS` | `["*"]` |
| `GROQ_MODEL_PRIMARY` | `llama-3.3-70b-versatile` |
| `GROQ_MODEL_FAST` | `llama-3.1-8b-instant` |
| `ADMIN_PASSWORD` | your admin password |
| `REVIEWER_PASSWORD` | your reviewer password |
| `USER_PASSWORD` | your user password |

5. Click **Create Web Service** → wait 5-8 min
6. Test: https://medisure-api-vyx1.onrender.com/api/v1/health

### Step 3: Deploy Frontend on Cloudflare Pages

> **Note:** Moved from Netlify to Cloudflare Pages (unlimited free builds, global CDN).

1. https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Pages**
2. **Connect to Git** → GitHub → select `VijaiVenkatesan/medisure-ai-platform`
3. Build settings:

| Field | Value |
| --- | --- |
| Project name | `medisure-ai-platform` |
| Root directory | `ui` |
| Build command | `npm run build` |
| Build output directory | `dist` |

4. Environment variables → Add:

| Variable | Value |
| --- | --- |
| `VITE_API_URL` | `https://medisure-api-vyx1.onrender.com/api/v1` |
| `VITE_DEMO_ADMIN_PW` | your admin password |
| `VITE_DEMO_REVIEWER_PW` | your reviewer password |
| `VITE_DEMO_USER_PW` | your user password |

5. Click **Save and Deploy** → live at `medisure-ai-platform.pages.dev`

SPA routing is handled by `ui/public/_redirects` (already in repo):
```
/* /index.html 200
```

### Step 4: GitHub Secrets (auto-deploy CI/CD)

Go to: `https://github.com/VijaiVenkatesan/medisure-ai-platform/settings/secrets/actions`

| Secret | Value | How to get |
| --- | --- | --- |
| `CLOUDFLARE_API_TOKEN` | CF token | Cloudflare → My Profile → API Tokens → Create Token → "Edit Cloudflare Workers" template |
| `CLOUDFLARE_ACCOUNT_ID` | Account ID | Cloudflare → right sidebar |
| `GROQ_API_KEY` | your Groq key | console.groq.com |
| `VITE_API_URL` | `https://medisure-api-vyx1.onrender.com/api/v1` | hardcoded |

After this: every `git push` → auto-deploy both services.

---

## Complete API Reference

### Auth

```
POST /api/v1/auth/login          Login → JWT token
GET  /api/v1/auth/me             Current user profile
GET  /api/v1/auth/users          List users (admin)
POST /api/v1/auth/users          Create user (admin)
DELETE /api/v1/auth/users/{u}    Delete user (admin)
```

### Claims (Phase 1)

```
POST /api/v1/claims/submit           Upload document
GET  /api/v1/claims/{id}             Get claim + full data
GET  /api/v1/claims                  List (paged, filtered)
GET  /api/v1/claims/{id}/audit       Audit trail
GET  /api/v1/analytics/summary       Status analytics
GET  /api/v1/hitl/pending            HITL queue
POST /api/v1/hitl/{id}/review        APPROVE / REJECT / INVESTIGATE
POST /api/v1/policies/index          Index policy for RAG
```

### Medical AI (Phase 2)

```
POST /api/v1/medical/summarize            Document → clinical summary
POST /api/v1/medical/code                 Text → ICD-10 codes
POST /api/v1/medical/code-document        Document → ICD-10 codes
POST /api/v1/medical/transcribe           Dictation text → SOAP note
POST /api/v1/medical/transcribe-audio     Audio file → SOAP note
```

### Underwriting & Clinical (Phase 3)

```
POST /api/v1/underwriting/assess          Medical history → risk class + loading
POST /api/v1/clinical/diagnose            Symptoms → differential diagnoses
POST /api/v1/clinical/drug-interactions   Medications → interaction report
POST /api/v1/clinical/risk-stratify       Patient data → risk score
```

### Admin

```
GET    /api/v1/admin/claims              All claims (admin)
PATCH  /api/v1/admin/claims/{id}         Edit claim
DELETE /api/v1/admin/claims/{id}         Delete claim
POST   /api/v1/admin/claims/{id}/reprocess  Restart pipeline
GET    /api/v1/admin/logs                Audit logs
GET    /api/v1/admin/stats               System stats
```

### Support

```
POST /api/v1/support/chat    AI chatbot conversation
```

---

## India-Specific Features

| Feature | Implementation |
| --- | --- |
| IRDAI compliance | Validation agent enforces health/motor rules |
| Govt schemes | Ayushman Bharat, PM-JAY, PMFBY, ESIC, CGHS in RAG |
| Aadhaar | Auto-masked XXXX-XXXX-XXXX |
| PAN validation | Format: XXXXX9999X |
| Hindi OCR | EasyOCR (local), Groq Vision (cloud) |
| INR detection | ₹, Rs., Rupees auto-detected |
| ABDM | FHIR-compatible medical summary output |
| Tropical diseases | Dengue, Malaria, TB, Typhoid in differential |
| ICMR guidelines | Applied in clinical decision support |
| IRDAI underwriting | Applied in medical underwriting module |

---

## Git Push Commands

### First push (new repo)

```
cd D:\medisure-ai-platform
git init
git add .
git commit -m "feat: MediSure AI v2 - all 4 phases, auth, chatbot, underwriting, clinical"
git branch -M main
git remote add origin https://github.com/VijaiVenkatesan/medisure-ai-platform.git
git push -u origin main
```

### Subsequent pushes

```
git add .
git commit -m "your change"
git push
```

---

## Troubleshooting

| Problem | Solution |
| --- | --- |
| Login fails / timeout | Render sleeping — wait 30s, click demo button on login screen |
| Scanned PDF error | Groq Vision is used automatically — check GROQ\_API\_KEY set in Render |
| Dashboard blank | Click Refresh button — backend error state shown |
| Claim stuck processing | Admin Panel → find claim → ↺ Reprocess |
| `model_decommissioned` | Run `fix_env.bat` to update model names in `.env` |
| Render 522 timeout | Normal free-tier sleep — first request wakes it |
| Push rejected (secrets) | Delete `.env.backup`, add to `.gitignore` |
| CI tests timeout | `pytest-timeout` is in requirements, tests have `@pytest.mark.timeout(30)` |
| Netlify "Site not available" | Moved to Cloudflare Pages — use https://medisure-ai-platform.pages.dev |

---

## License

MIT — free to use, modify, and deploy commercially.
