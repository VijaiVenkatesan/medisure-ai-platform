import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  HelpCircle, ChevronDown, ChevronUp, Upload, ShieldCheck,
  FileText, BarChart2, Stethoscope, Shield, BookOpen,
  CheckCircle, AlertTriangle, Info, FileSearch, Activity
} from 'lucide-react'

const SECTIONS = [
  {
    id: 'getting-started',
    icon: <Upload size={18} />,
    color: 'var(--brand)',
    title: 'Getting Started',
    steps: [
      { step: '1', title: 'Login', desc: 'Use your credentials on the login screen. Demo accounts are available — click the role buttons on the login screen to auto-fill credentials' },
      { step: '2', title: 'Submit a Claim', desc: 'Click "Submit Claim" in the sidebar. Drag & drop a PDF, PNG, or JPG file (max 10MB). Digital PDFs work best; scanned docs use Groq Vision AI.' },
      { step: '3', title: 'Wait for Processing', desc: 'The AI pipeline runs automatically: OCR → Extract → Validate → Policy Check → Fraud Analysis → Decision. Takes 30–90 seconds.' },
      { step: '4', title: 'View Results', desc: 'Go to "All Claims" or click the claim ID to see the full decision, fraud score, extracted data, and audit trail.' },
    ]
  },
  {
    id: 'ai-pipeline',
    icon: <FileText size={18} />,
    color: 'var(--info)',
    title: 'Understanding the AI Pipeline',
    steps: [
      { step: 'OCR', title: 'Document Extraction', desc: 'Digital PDFs use pypdf text layer (fast). Scanned PDFs and images use Groq Vision (llama-4-scout) — converts page to base64 image and extracts all text including Hindi.' },
      { step: 'Extract', title: 'Data Extraction', desc: 'Groq LLM (llama-3.3-70b) converts raw text to structured JSON: claimant info, policy details, incident data, claimed amounts, ICD-10 codes.' },
      { step: 'Validate', title: 'Business Validation', desc: 'Checks IRDAI rules: required fields, date logic, policy lapse, amount limits, Indian phone format, Aadhaar format, motor vehicle number for motor claims.' },
      { step: 'Policy', title: 'Policy Eligibility (RAG)', desc: 'ChromaDB semantic search finds the 6 most relevant policy chunks. LLM determines if claim is covered, citing specific clauses.' },
      { step: 'Fraud', title: 'Fraud Analysis', desc: 'Rule-based checks (early claims, round numbers, high amounts) + LLM analysis = fraud score 0–100%. High risk → investigate.' },
      { step: 'Decision', title: 'Final Decision', desc: 'Auto-approve (≤₹50k, low risk), Auto-reject (fraud ≥90% or 3+ critical errors), HITL (ambiguous/high-value/medium fraud).' },
    ]
  },
  {
    id: 'hitl',
    icon: <ShieldCheck size={18} />,
    color: 'var(--investigate)',
    title: 'HITL Review (Human-in-the-Loop)',
    steps: [
      { step: '1', title: 'When Claims Route to HITL', desc: 'Fraud score 45–90%, claimed amount >₹2,00,000, AI confidence <65%, or explicitly flagged for investigation.' },
      { step: '2', title: 'Reviewing a Claim', desc: 'Go to "HITL Review". Select a claim from the queue. The review panel slides in showing AI recommendation, fraud score, and full claim details.' },
      { step: '3', title: 'Making a Decision', desc: 'Choose APPROVE (with optional modified amount), REJECT (with reason), or INVESTIGATE (route to specialist). All decisions require notes.' },
      { step: '4', title: 'Audit Trail', desc: 'Every HITL decision is logged with reviewer ID, timestamp, notes, and action. View in the claim detail page or Admin → Logs.' },
    ]
  },
  {
    id: 'medical-ai',
    icon: <Stethoscope size={18} />,
    color: 'var(--approve)',
    title: 'Medical AI Features (Phase 2)',
    steps: [
      { step: 'Summarize', title: 'Medical Document Summarization', desc: 'Upload any medical document (discharge summary, OPD note, lab report, prescription). AI extracts: diagnoses with ICD-10 codes, medications with dosage, vitals, lab results, follow-up, and a plain-language summary.' },
      { step: 'Code', title: 'ICD-10 Auto-Coding', desc: 'Paste clinical text or upload a document. Select your country (India/USA/UK/UAE). AI assigns ICD-10 codes, CPT codes (USA), explains coding rationale, flags query items for physician clarification.' },
      { step: 'Transcribe', title: 'Medical Transcription → SOAP', desc: 'Paste dictation text or upload an audio file (MP3, WAV). AI structures it as a SOAP note (Subjective, Objective, Assessment, Plan). Supports Hindi, Tamil, Telugu, and 90+ languages via Groq Whisper.' },
    ]
  },
  {
    id: 'admin',
    icon: <Shield size={18} />,
    color: 'var(--brand)',
    title: 'Admin Panel',
    steps: [
      { step: 'Claims', title: 'Manage Claims', desc: 'Edit any field (status, fraud score, decision, explanation, approved amount). Delete claims permanently. Reprocess failed claims by resetting to RECEIVED and rerunning the AI pipeline.' },
      { step: 'Logs', title: 'Audit Logs', desc: 'View all system events: CLAIM_SUBMITTED, DECISION_MADE, HITL_REVIEW_COMPLETED, ADMIN_UPDATE, POLICY_INDEXED. Filter by event type or actor. Full timestamp and detail data.' },
      { step: 'Stats', title: 'System Statistics', desc: 'Claims by status, claims by insurance type, total claimed amount (INR), total approved amount, average fraud score. Updated in real-time.' },
      { step: 'Users', title: 'User Management', desc: 'Create new users (ADMIN/REVIEWER/USER roles). Delete users. Only admins can access this. Via API: POST /api/v1/auth/users, GET /api/v1/auth/users.' },
    ]
  },
  {
    id: 'policy-admin',
    icon: <BookOpen size={18} />,
    color: 'var(--text-secondary)',
    title: 'Policy Administration',
    steps: [
      { step: '1', title: 'Why Index Policies', desc: 'The Policy Agent uses RAG (Retrieval-Augmented Generation) to check claim eligibility against indexed policies. More policies = better eligibility decisions.' },
      { step: '2', title: 'Quick Presets', desc: 'Click any preset (Star Health, HDFC ERGO Motor, Ayushman Bharat, PMFBY, etc.) to auto-fill the form with a standard policy template.' },
      { step: '3', title: 'Custom Policy', desc: 'Paste your own policy text. Select insurance type and country. Click "Index Policy". The system splits it into chunks, creates embeddings, and stores in ChromaDB.' },
      { step: '4', title: 'Best Practices', desc: 'Include: coverage details, exclusions list, claim procedure steps, required documents, waiting periods. More detail = better RAG results.' },
    ]
  },
  {
    id: 'underwriting',
    icon: <FileSearch size={18} />,
    color: '#f97316',
    title: 'Medical Underwriting (Phase 3)',
    steps: [
      { step: '1', title: 'What is Medical Underwriting', desc: 'AI-powered insurance risk assessment that determines risk class, premium loading percentage, and specific exclusions for an applicant based on their medical history.' },
      { step: '2', title: 'How to use it', desc: 'Go to "Underwriting" in the sidebar. Enter applicant age, gender, insurance type (Health/Life/Critical Illness), sum assured, and policy term. Select country for the right regulatory standard.' },
      { step: '3', title: 'Medical Summary', desc: "Paste the applicant's complete medical history: BMI, blood pressure, diagnoses (with ICD-10 if available), current medications, HbA1c (if diabetic), smoking status, and family history." },
      { step: '4', title: 'Understanding Results', desc: 'Risk Class: PREFERRED (below average risk, possible discount), STANDARD (normal premium), SUBSTANDARD 1-3 (loading applied), DECLINE (cannot offer cover). Premium loading shows the % increase over standard. Each exclusion lists condition, type, and duration.' },
      { step: '5', title: 'Regulatory Standards', desc: 'India uses IRDAI underwriting guidelines. USA uses NAIC standards. UK uses ABI guidelines. Results flag any additional medical requirements (echo, treadmill test, blood panel) needed before final decision.' },
    ]
  },
  {
    id: 'clinical',
    icon: <Activity size={18} />,
    color: 'var(--info)',
    title: 'Clinical Decision Support (Phase 3)',
    steps: [
      { step: 'DDx', title: 'Differential Diagnosis', desc: 'Go to Clinical DSS → Diagnosis tab. Add symptoms (press Enter after each one). Enter patient age, gender, duration of symptoms, and medical history. Select country for India (ICMR + tropical diseases), USA (CDC), or UK (NICE). Results show ranked differential diagnoses with probability %, supporting/against features, recommended investigations, and red flags.' },
      { step: 'Drug', title: 'Drug Interaction Checker', desc: 'Drug Interactions tab: add all medications (generic name + dose). Add medical conditions and select renal/hepatic function status. Results show interaction severity (CONTRAINDICATED, MAJOR, MODERATE, MINOR), mechanism, clinical significance, and management recommendation.' },
      { step: 'Risk', title: 'Risk Stratification', desc: 'Risk tab: select risk type (Cardiovascular, Diabetes, Cancer, Hospital Readmission). Enter vitals, check applicable risk factors (smoking, diabetes, hypertension, family history). Results show risk score /100, category (LOW/MODERATE/HIGH/VERY HIGH), 10-year risk %, and modifiable factors with interventions.' },
      { step: '!', title: 'Important Disclaimer', desc: 'Clinical Decision Support is assistance ONLY — it does not replace clinical examination, professional judgment, or licensed medical advice. All results should be reviewed by a qualified clinician before acting on them.' },
    ]
  },
  {
    id: 'troubleshooting',
    icon: <AlertTriangle size={18} />,
    color: 'var(--reject)',
    title: 'Troubleshooting',
    steps: [
      { step: '!', title: '"Scanned PDF detected" error', desc: 'Your PDF is an image-based (photographed) document. The AI Vision OCR should handle it. If it still fails, the image quality may be too low. Try a higher resolution scan or use a digital PDF.' },
      { step: '!', title: '"Backend waking up" banner', desc: 'Render free tier sleeps after 15 minutes of no traffic. Wait 30 seconds — the service wakes automatically. After the first request, all subsequent requests are fast.' },
      { step: '!', title: 'Claim stuck in processing', desc: 'Go to Admin Panel → Claims → find the stuck claim → click Reprocess (↺ icon). This resets it to RECEIVED and reruns the full AI pipeline.' },
      { step: '!', title: 'All fields show "—" after processing', desc: 'The OCR could not extract meaningful text. Common causes: password-protected PDF, very low resolution scan, non-standard language. Try a different document format.' },
      { step: '!', title: 'Login not working', desc: 'Click a demo account button on the login screen. If the backend is sleeping, wait 30s and retry.' },
    ]
  },
]

function Section({ section }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="card mb-16">
      <button className="card-header"
        style={{ width: '100%', background: 'none', border: 'none',
          cursor: 'pointer', color: 'inherit', textAlign: 'left' }}
        onClick={() => setOpen(o => !o)}>
        <div className="flex gap-12" style={{ alignItems: 'center' }}>
          <div style={{
            width: 36, height: 36, borderRadius: 'var(--radius-md)',
            background: section.color + '20', color: section.color,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>{section.icon}</div>
          <span className="card-title">{section.title}</span>
        </div>
        {open ? <ChevronUp size={15} style={{ color: 'var(--text-muted)' }} />
               : <ChevronDown size={15} style={{ color: 'var(--text-muted)' }} />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} style={{ overflow: 'hidden' }}>
            <div className="card-body">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {section.steps.map((s, i) => (
                  <div key={i} style={{ display: 'flex', gap: 14 }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                      background: section.color + '20', color: section.color,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, fontWeight: 700,
                    }}>{s.step}</div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 3 }}>{s.title}</div>
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.65 }}>
                        {s.desc}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function HelpPage() {
  return (
    <div>
      <div className="page-header">
        <div style={{ paddingBottom: 20 }}>
          <div className="flex gap-8" style={{ alignItems: 'center', marginBottom: 6 }}>
            <HelpCircle size={18} color="var(--brand)" />
            <h1 className="page-title" style={{ margin: 0 }}>Help & Documentation</h1>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            Complete guide to using MediSure AI — step by step instructions for every feature
          </p>
        </div>
      </div>

      <div className="page-content" style={{ maxWidth: 800 }}>
        {/* Quick links */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 24 }}>
          {[
            { label: 'Submit Claim', icon: '📤', href: '#getting-started' },
            { label: 'HITL Review', icon: '🔍', href: '#hitl' },
            { label: 'Medical AI', icon: '🩺', href: '#medical-ai' },
            { label: 'Admin Panel', icon: '🛡', href: '#admin' },
            { label: 'Troubleshoot', icon: '⚠️', href: '#troubleshooting' },
            { label: 'Policy Admin', icon: '📚', href: '#policy-admin' },
          ].map(q => (
            <a key={q.label} href={q.href}
              style={{
                background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)', padding: '10px 14px',
                textDecoration: 'none', color: 'var(--text-secondary)',
                fontSize: 12, fontWeight: 500,
                display: 'flex', alignItems: 'center', gap: 8,
                transition: 'all var(--transition)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'var(--brand)'
                e.currentTarget.style.color = 'var(--brand)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = ''
                e.currentTarget.style.color = ''
              }}>
              <span>{q.icon}</span> {q.label}
            </a>
          ))}
        </div>

        {/* Info banner */}
        <div style={{
          background: 'var(--brand-dim)', border: '1px solid var(--brand-glow)',
          borderRadius: 'var(--radius-lg)', padding: '14px 18px', marginBottom: 24,
          display: 'flex', gap: 12, alignItems: 'flex-start',
        }}>
          <Info size={16} color="var(--brand)" style={{ flexShrink: 0, marginTop: 1 }} />
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.65 }}>
            <strong style={{ color: 'var(--brand)' }}>AI Support available 24/7</strong> — 
            Click the <strong>chat bubble</strong> (bottom right) to ask MediSure AI Assistant any question.
            The assistant knows all platform features and can guide you step by step.
          </div>
        </div>

        {/* Sections */}
        {SECTIONS.map(s => <Section key={s.id} section={s} />)}
      </div>
    </div>
  )
}
