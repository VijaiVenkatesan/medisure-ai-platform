import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, Plus, CheckCircle, AlertCircle, Loader } from 'lucide-react'
import toast from 'react-hot-toast'
import { indexPolicy } from '../utils/api'

const INSURANCE_TYPES = [
  'HEALTH', 'MOTOR', 'LIFE', 'PROPERTY', 'TRAVEL',
  'CROP', 'PRADHAN_MANTRI', 'AYUSHMAN_BHARAT', 'OTHER'
]

const COUNTRIES = [
  { value: 'IN', label: '🇮🇳 India'     },
  { value: 'US', label: '🇺🇸 USA'       },
  { value: 'GB', label: '🇬🇧 UK'        },
  { value: 'AE', label: '🇦🇪 UAE'       },
  { value: 'SG', label: '🇸🇬 Singapore' },
  { value: 'OTHER', label: '🌐 Other'   },
]

const PRESET_POLICIES = [
  {
    label: 'Standard Indian Health Policy',
    type: 'HEALTH', country: 'IN', company: 'Generic IRDAI Compliant',
    text: `HEALTH INSURANCE POLICY - INDIA
Coverage: Hospitalization, day care procedures, pre/post hospitalization (30/60 days).
Exclusions: Pre-existing diseases (2-year wait), cosmetic surgery, dental unless accidental.
Sum Insured: As specified in schedule. Co-payment: 10% for age 60+.
Claim Procedure: Notify TPA within 24 hours for emergency, 48 hours for planned.
Required Documents: Discharge summary, all bills, investigation reports, Aadhaar/PAN copy.
IRDAI Compliant. Grievance: igms.irda.gov.in | 155255.`,
  },
  {
    label: 'Motor Insurance - India Comprehensive',
    type: 'MOTOR', country: 'IN', company: 'IRDAI Motor Policy',
    text: `MOTOR INSURANCE COMPREHENSIVE POLICY
Own Damage: Accidental damage, theft, fire, natural calamities, transit damage.
Third Party: Unlimited bodily injury liability. Property damage up to INR 7.5 lakh.
Depreciation: As per IRDAI schedule (5% to 50% based on vehicle age).
Exclusions: Unlicensed driver, DUI, mechanical breakdown, outside India.
Claim: Report within 48 hours. Surveyor within 48 hours. FIR mandatory for theft.
Required: Claim form, RC, DL, FIR (theft/TP), repair bills.`,
  },
  {
    label: 'Ayushman Bharat PM-JAY',
    type: 'AYUSHMAN_BHARAT', country: 'IN', company: 'National Health Authority',
    text: `AYUSHMAN BHARAT PRADHAN MANTRI JAN AROGYA YOJANA (PM-JAY)
Coverage: INR 5,00,000 per family per year. No cap on family size.
Beneficiaries: SECC 2011 database families. All pre-existing conditions from Day 1.
Benefits: 1929 treatment packages. Cashless at empaneled hospitals.
Specialties: Oncology, cardiology, neurology, orthopedics, nephrology, neonatology.
Eligibility: Check mera.pmjay.gov.in or call 14555.
Claim: Hospital files directly via NHA portal. Zero payment by beneficiary.
Grievance: 14555 or CPGRAMS portal.`,
  },
  {
    label: 'PMFBY Crop Insurance',
    type: 'CROP', country: 'IN', company: 'Ministry of Agriculture',
    text: `PRADHAN MANTRI FASAL BIMA YOJANA (PMFBY)
Premium: Max 2% kharif, 1.5% rabi, 5% commercial crops (farmer share).
Coverage: Prevented sowing, standing crop, post-harvest 14 days, localized calamities.
Sum Insured: Scale of Finance declared by DLTC.
Enrollment: Loanee mandatory via KCC. Non-loanee voluntary via bank/CSC/pmfby.gov.in.
Loss Notification: Within 72 hours via Crop Insurance App or 14447.
Settlement: Direct NEFT to Aadhaar-linked bank account within 2 months of harvest data.`,
  },
]

export default function PolicyAdmin() {
  const [form, setForm] = useState({
    policy_name: '', insurance_type: 'HEALTH', country: 'IN',
    company: '', policy_text: ''
  })
  const [submitting, setSubmitting] = useState(false)
  const [result,     setResult]     = useState(null)
  const [history,    setHistory]    = useState([])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const loadPreset = (p) => {
    setForm({
      policy_name: p.label,
      insurance_type: p.type,
      country: p.country,
      company: p.company,
      policy_text: p.text,
    })
    setResult(null)
  }

  const handleSubmit = async () => {
    const { policy_name, insurance_type, country, policy_text } = form
    if (!policy_name.trim()) { toast.error('Policy name is required'); return }
    if (!policy_text.trim()) { toast.error('Policy text is required'); return }

    setSubmitting(true)
    setResult(null)
    try {
      const res = await indexPolicy({
        policy_text: form.policy_text,
        policy_name: form.policy_name,
        insurance_type: form.insurance_type,
        country: form.country,
        company: form.company || undefined,
      })
      setResult({ success: true, chunks: res.chunks_indexed, name: res.policy_name })
      setHistory(h => [{ ...res, at: new Date().toLocaleTimeString() }, ...h.slice(0, 9)])
      toast.success(`Indexed "${res.policy_name}" — ${res.chunks_indexed} chunks`)
    } catch (e) {
      setResult({ success: false, error: e.message })
      toast.error(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const charCount = form.policy_text.length
  const wordCount = form.policy_text.trim() ? form.policy_text.trim().split(/\s+/).length : 0

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Policy Administration</h1>
        <p className="page-subtitle">Index insurance policy documents into the RAG vector store for AI eligibility checking</p>
      </div>

      <div className="page-content">
        <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20, alignItems: 'start' }}>

          {/* ── LEFT: FORM ── */}
          <div>
            {/* Presets */}
            <div className="card mb-16">
              <div className="card-header">
                <span className="card-title">Quick Presets</span>
                <span className="text-xs text-muted">Indian policies ready to index</span>
              </div>
              <div className="card-body" style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {PRESET_POLICIES.map(p => (
                  <button
                    key={p.label}
                    className="btn btn-secondary btn-sm"
                    onClick={() => loadPreset(p)}
                    style={{ fontSize: 11 }}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Form */}
            <div className="card">
              <div className="card-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <BookOpen size={15} color="var(--brand)" />
                  <span className="card-title">Index New Policy</span>
                </div>
              </div>
              <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

                <div className="form-group">
                  <label className="form-label">Policy Name *</label>
                  <input className="form-input" placeholder="e.g. Star Health Comprehensive 2024"
                    value={form.policy_name} onChange={e => set('policy_name', e.target.value)} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div className="form-group">
                    <label className="form-label">Insurance Type *</label>
                    <select className="form-select" value={form.insurance_type}
                      onChange={e => set('insurance_type', e.target.value)}>
                      {INSURANCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Country</label>
                    <select className="form-select" value={form.country}
                      onChange={e => set('country', e.target.value)}>
                      {COUNTRIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Insurance Company</label>
                  <input className="form-input" placeholder="e.g. Star Health and Allied Insurance"
                    value={form.company} onChange={e => set('company', e.target.value)} />
                </div>

                <div className="form-group">
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <label className="form-label">Policy Text *</label>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {wordCount} words · {charCount} chars
                    </span>
                  </div>
                  <textarea
                    className="form-textarea"
                    rows={14}
                    placeholder="Paste the full policy document text here. Include coverage details, exclusions, claim procedures, and eligibility criteria. The more detail, the better the RAG retrieval."
                    value={form.policy_text}
                    onChange={e => set('policy_text', e.target.value)}
                    style={{ fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.7 }}
                  />
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                    Tip: Include sections on coverage, exclusions, claim procedure, and India-specific regulations for best results.
                  </div>
                </div>

                <AnimatePresence>
                  {result && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      style={{
                        padding: '12px 16px',
                        borderRadius: 'var(--radius-md)',
                        border: `1px solid ${result.success ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
                        background: result.success ? 'var(--approve-dim)' : 'var(--reject-dim)',
                        display: 'flex', alignItems: 'center', gap: 10,
                      }}
                    >
                      {result.success
                        ? <CheckCircle size={16} color="var(--approve)" />
                        : <AlertCircle size={16} color="var(--reject)" />}
                      <div>
                        {result.success ? (
                          <div style={{ fontSize: 13, color: 'var(--approve)', fontWeight: 600 }}>
                            "{result.name}" indexed — {result.chunks} chunks stored in vector DB
                          </div>
                        ) : (
                          <div style={{ fontSize: 13, color: 'var(--reject)' }}>{result.error}</div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <button
                  className="btn btn-primary"
                  style={{ width: '100%' }}
                  onClick={handleSubmit}
                  disabled={submitting || !form.policy_name.trim() || !form.policy_text.trim()}
                >
                  {submitting
                    ? <><Loader size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> Indexing…</>
                    : <><BookOpen size={14} /> Index Policy into Vector Store</>}
                </button>
              </div>
            </div>
          </div>

          {/* ── RIGHT: INFO + HISTORY ── */}
          <div>
            {/* How it works */}
            <div className="card mb-16">
              <div className="card-header">
                <span className="card-title">How RAG Works</span>
              </div>
              <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {[
                  {
                    step: '1', color: 'var(--brand)',
                    title: 'Text Chunking',
                    desc: 'Policy document is split into 500-word overlapping chunks for granular retrieval.'
                  },
                  {
                    step: '2', color: 'var(--info)',
                    title: 'Embedding Generation',
                    desc: 'Each chunk is converted to a 384-dim vector using all-MiniLM-L6-v2 (runs locally, free).'
                  },
                  {
                    step: '3', color: 'var(--approve)',
                    title: 'ChromaDB Storage',
                    desc: 'Vectors and text stored persistently in local ChromaDB with metadata (type, country, company).'
                  },
                  {
                    step: '4', color: 'var(--investigate)',
                    title: 'Semantic Retrieval',
                    desc: 'When a claim is processed, the Policy Agent retrieves the top-6 most relevant chunks and feeds them to the LLM.'
                  },
                ].map(s => (
                  <div key={s.step} style={{ display: 'flex', gap: 12 }}>
                    <div style={{
                      width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
                      background: s.color + '22', color: s.color,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, fontWeight: 700,
                    }}>{s.step}</div>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 2, color: 'var(--text-primary)' }}>{s.title}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{s.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Indexing history */}
            <div className="card">
              <div className="card-header"><span className="card-title">Session History</span></div>
              <div className="card-body">
                {history.length === 0 ? (
                  <div className="empty-state" style={{ padding: '24px 16px' }}>
                    <div className="empty-state-icon">📚</div>
                    <div className="empty-state-sub">No policies indexed this session</div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {history.map((h, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 10,
                          padding: '10px 12px', background: 'var(--bg-elevated)',
                          borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)',
                        }}
                      >
                        <CheckCircle size={14} color="var(--approve)" style={{ flexShrink: 0 }} />
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{h.policy_name}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                            {h.chunks_indexed} chunks · {h.at}
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* India tip */}
            <div style={{
              marginTop: 16, padding: '14px 16px',
              background: 'var(--brand-dim)', borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--brand-glow)',
            }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--brand)', marginBottom: 6 }}>🇮🇳 India Focus</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.65 }}>
                For best results with Indian policies, include IRDAI regulation references, regional language equivalents,
                government scheme details (PM-JAY, PMFBY, ESIC), and CGHS/ECHS terms. The system auto-detects Hindi
                mixed-language documents during OCR.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
