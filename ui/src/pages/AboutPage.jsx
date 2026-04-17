import { motion } from 'framer-motion'
import { Github, ExternalLink, Cpu, Database, Globe, Shield } from 'lucide-react'

const PHASES = [
  {
    phase: 'Phase 1', status: 'live', color: 'var(--approve)',
    title: 'Insurance Claims Processing',
    features: ['Multi-agent AI pipeline (LangGraph)', 'OCR + Groq Vision (scanned docs)', 'RAG policy eligibility (ChromaDB)', 'Fraud detection (rule-based + LLM)', 'Human-in-the-loop review', 'India IRDAI compliance', '9 built-in policy templates'],
  },
  {
    phase: 'Phase 2', status: 'live', color: 'var(--approve)',
    title: 'Medical Document Intelligence',
    features: ['Medical document summarization', 'ICD-10/CPT auto-coding', 'SOAP note structuring', 'Groq Whisper transcription (90+ languages)', 'India ABDM FHIR compatibility', 'Multi-country coding standards'],
  },
  {
    phase: 'Phase 3', status: 'live', color: 'var(--approve)',
    title: 'Clinical Decision Support & Underwriting',
    features: ['Differential diagnosis (India tropical diseases)', 'Drug interaction checker (MAJOR/CONTRAINDICATED)', 'Patient risk stratification (CVD, Diabetes, Cancer)', 'Medical underwriting (risk class, loading, exclusions)', 'IRDAI / NAIC / ABI regulatory standards', 'Evidence-based ICMR + WHO guidelines'],
  },
  {
    phase: 'Phase 4', status: 'coming', color: 'var(--text-muted)',
    title: 'Enterprise Healthcare Platform',
    features: ['Multi-tenant architecture', 'Role-based access control', 'HIPAA/GDPR/DPDP compliance', 'Real-time HL7 FHIR streams', 'HIS/EMR connectors', 'WhatsApp patient communication'],
  },
]

const STACK = [
  { category: 'AI / LLM', icon: <Cpu size={16} />, color: 'var(--brand)',
    items: ['Groq llama-3.3-70b-versatile', 'Groq llama-3.1-8b-instant', 'Groq llama-4-scout (Vision OCR)', 'Groq Whisper large-v3 (Audio)', 'LangGraph (Agent Orchestration)', 'ChromaDB (Vector RAG)'] },
  { category: 'Backend', icon: <Database size={16} />, color: 'var(--info)',
    items: ['FastAPI + Uvicorn', 'SQLAlchemy async', 'SQLite → PostgreSQL', 'JWT Authentication', 'Pydantic v2 validation', 'Python 3.11'] },
  { category: 'Frontend', icon: <Globe size={16} />, color: 'var(--approve)',
    items: ['React 18 + Vite', 'Framer Motion animations', 'Recharts data viz', 'React Router v6', 'Lucide React icons', 'Custom design system'] },
  { category: 'Infrastructure', icon: <Shield size={16} />, color: 'var(--investigate)',
    items: ['Render.com (backend free)', 'Netlify (frontend free)', 'GitHub Actions CI/CD', 'Groq Cloud (free tier)', '100% open-source', 'No Docker needed'] },
]

const COUNTRIES = [
  { flag: '🇮🇳', name: 'India', features: 'IRDAI, ABDM, PM-JAY, PMFBY, Hindi OCR' },
  { flag: '🇺🇸', name: 'USA', features: 'ACA, Medicare, ICD-10-CM, CPT codes' },
  { flag: '🇬🇧', name: 'UK', features: 'NHS, PMI, SNOMED CT, ICD-10' },
  { flag: '🇦🇪', name: 'UAE', features: 'DHA, HAAD, MOH ICD-10' },
  { flag: '🇸🇬', name: 'Singapore', features: 'MediShield, MOH ICD-10' },
]

export default function AboutPage() {
  return (
    <div>
      <div className="page-header">
        <div style={{ paddingBottom: 20 }}>
          <h1 className="page-title">About MediSure AI</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            Enterprise-grade Healthcare AI Platform · India-first · Open Source · Free to Deploy
          </p>
        </div>
      </div>

      <div className="page-content">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>

          {/* Hero */}
          <div style={{
            background: 'linear-gradient(135deg, var(--bg-elevated), var(--bg-surface))',
            border: '1px solid var(--border-default)', borderRadius: 'var(--radius-xl)',
            padding: '28px 32px', marginBottom: 24,
            backgroundImage: 'radial-gradient(circle at 80% 50%, rgba(0,201,167,0.08) 0%, transparent 60%)',
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 20 }}>
              <div style={{
                width: 64, height: 64, borderRadius: 18, flexShrink: 0,
                background: 'linear-gradient(135deg, var(--brand), #007aff)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 28, fontWeight: 800, color: '#000',
                boxShadow: '0 0 32px rgba(0,201,167,0.3)',
              }}>C</div>
              <div>
                <h2 style={{ fontSize: 24, fontWeight: 800, letterSpacing: -0.5, marginBottom: 8 }}>
                  MediSure AI Healthcare AI Platform
                </h2>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: 600 }}>
                  An enterprise-grade, multi-agent AI system for insurance claims processing and medical 
                  document intelligence. Built with India-first design, supporting global standards. 
                  100% open-source, deployable for free.
                </p>
                <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                  <a href="https://github.com/VijaiVenkatesan/insurance-claims-platform"
                    target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
                    <Github size={14} /> GitHub Repository
                  </a>
                  <a href="https://medisure-ai-api.onrender.com/docs"
                    target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-sm">
                    <ExternalLink size={14} /> API Documentation
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* Phases */}
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14 }}>Development Roadmap</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 24 }}>
            {PHASES.map(p => (
              <div key={p.phase} className="card" style={{
                borderColor: p.status === 'live' ? p.color + '40' : 'var(--border-subtle)',
              }}>
                <div className="card-header">
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                      <span style={{
                        fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
                        background: p.color + '20', color: p.color,
                      }}>{p.phase}</span>
                      <span style={{
                        fontSize: 10, fontWeight: 700,
                        color: p.status === 'live' ? 'var(--approve)' : 'var(--text-muted)',
                      }}>{p.status === 'live' ? '✅ LIVE' : '🔜 COMING SOON'}</span>
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 700 }}>{p.title}</div>
                  </div>
                </div>
                <div className="card-body" style={{ paddingTop: 12 }}>
                  {p.features.map((f, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 5,
                      alignItems: 'flex-start' }}>
                      <div style={{ width: 4, height: 4, borderRadius: '50%', flexShrink: 0,
                        background: p.color, marginTop: 7 }} />
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{f}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Tech Stack */}
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14 }}>Technology Stack (100% Free & Open Source)</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 }}>
            {STACK.map(s => (
              <div key={s.category} className="card">
                <div className="card-header">
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <div style={{ color: s.color }}>{s.icon}</div>
                    <span className="card-title" style={{ fontSize: 12 }}>{s.category}</span>
                  </div>
                </div>
                <div className="card-body" style={{ paddingTop: 10 }}>
                  {s.items.map((item, i) => (
                    <div key={i} style={{ fontSize: 11, color: 'var(--text-secondary)',
                      padding: '3px 0', borderBottom: i < s.items.length - 1
                        ? '1px solid var(--border-subtle)' : 'none' }}>
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Countries */}
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14 }}>Multi-Country Support</h2>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
            {COUNTRIES.map(c => (
              <div key={c.name} style={{
                background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)', padding: '10px 14px',
                display: 'flex', gap: 10, alignItems: 'center',
              }}>
                <span style={{ fontSize: 22 }}>{c.flag}</span>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700 }}>{c.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.features}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Architecture */}
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14 }}>System Architecture</h2>
          <div className="card">
            <div className="card-body">
              <pre style={{
                fontFamily: 'var(--font-mono)', fontSize: 11,
                color: 'var(--text-secondary)', lineHeight: 1.7,
                overflow: 'auto', margin: 0,
              }}>{`
USER BROWSER ──────────────────────────────────────────────────
      │
      ▼
NETLIFY (React + Vite) ─── static frontend, CDN-served
  medisure-ai-platform.pages.dev
      │  API calls (HTTPS)
      ▼
RENDER (FastAPI + Python) ─── backend, auto-sleep free tier
  medisure-ai-api.onrender.com
      │
      ├──► GROQ AI CLOUD ─── LLM inference (free 14,400 req/day)
      │     ├── llama-3.3-70b-versatile (main reasoning)
      │     ├── llama-3.1-8b-instant    (fast tasks)
      │     ├── llama-4-scout           (vision OCR)
      │     └── whisper-large-v3        (audio)
      │
      ├──► SQLite DB ─── claims, users, decisions, audit logs
      │
      └──► ChromaDB ─── vector store for policy RAG
              9 built-in policies, 180+ chunks indexed

GITHUB ─── source of truth, CI/CD, auto-deploy both services
  VijaiVenkatesan/insurance-claims-platform
`}</pre>
            </div>
          </div>

          {/* Credits */}
          <div style={{
            marginTop: 24, padding: '16px 20px',
            background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)', fontSize: 12, color: 'var(--text-muted)',
            textAlign: 'center', lineHeight: 1.8,
          }}>
            Built with ❤️ for the Indian healthcare ecosystem · 
            Powered by <a href="https://groq.com" target="_blank" rel="noopener noreferrer"
              style={{ color: 'var(--brand)', textDecoration: 'none' }}>Groq</a> · 
            MIT License · 
            <a href="https://github.com/VijaiVenkatesan/insurance-claims-platform"
              target="_blank" rel="noopener noreferrer"
              style={{ color: 'var(--brand)', textDecoration: 'none' }}>Open Source on GitHub</a>
          </div>

        </motion.div>
      </div>
    </div>
  )
}
