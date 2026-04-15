import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileSearch, ChevronDown, ChevronUp, AlertCircle,
  CheckCircle, XCircle, AlertTriangle, Loader, Info
} from 'lucide-react'
import toast from 'react-hot-toast'
import { underwritingAssess } from '../utils/api'

const RISK_COLORS = {
  PREFERRED:      'var(--approve)',
  STANDARD:       'var(--brand)',
  SUBSTANDARD_1:  'var(--investigate)',
  SUBSTANDARD_2:  '#f97316',
  SUBSTANDARD_3:  '#ef4444',
  DECLINE:        'var(--reject)',
}

const DECISION_COLORS = {
  ACCEPT_STANDARD:       'var(--approve)',
  ACCEPT_WITH_LOADING:   'var(--investigate)',
  ACCEPT_WITH_EXCLUSION: 'var(--info)',
  POSTPONE:              '#f97316',
  DECLINE:               'var(--reject)',
}

const DECISION_ICONS = {
  ACCEPT_STANDARD:       <CheckCircle size={18} />,
  ACCEPT_WITH_LOADING:   <AlertTriangle size={18} />,
  ACCEPT_WITH_EXCLUSION: <Info size={18} />,
  POSTPONE:              <AlertTriangle size={18} />,
  DECLINE:               <XCircle size={18} />,
}

function Collapsible({ title, children, defaultOpen = true, badge }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card mb-12">
      <button className="card-header" style={{ width: '100%', background: 'none',
        border: 'none', cursor: 'pointer', color: 'inherit', textAlign: 'left' }}
        onClick={() => setOpen(o => !o)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="card-title">{title}</span>
          {badge && <span style={{ fontSize: 11, background: 'var(--brand-dim)',
            color: 'var(--brand)', padding: '1px 7px', borderRadius: 10,
            fontWeight: 700 }}>{badge}</span>}
        </div>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} style={{ overflow: 'hidden' }}>
            <div className="card-body">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Row({ label, value, mono }) {
  if (value == null || value === '') return null
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: 8,
      padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
      <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>{label}</span>
      <span style={{ fontSize: 13, color: 'var(--text-primary)',
        fontFamily: mono ? 'var(--font-mono)' : 'inherit' }}>{value}</span>
    </div>
  )
}

export default function Underwriting() {
  const [form, setForm] = useState({
    age: '', gender: 'MALE', insurance_type: 'HEALTH',
    sum_assured: '', policy_term_years: '', country: 'IN',
    medical_summary: '', additional_context: '',
  })
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async () => {
    if (!form.medical_summary.trim()) { toast.error('Enter medical summary'); return }
    if (!form.age) { toast.error('Enter applicant age'); return }
    setLoading(true); setResult(null)
    try {
      const payload = {
        ...form,
        age: parseInt(form.age),
        sum_assured: form.sum_assured ? parseFloat(form.sum_assured) : null,
        policy_term_years: form.policy_term_years ? parseInt(form.policy_term_years) : null,
      }
      const r = await underwritingAssess(payload)
      setResult(r)
      toast.success('Underwriting assessment complete')
    } catch (e) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  const decision = result?.underwriting_decision?.decision
  const riskClass = result?.risk_assessment?.overall_risk_class

  return (
    <div>
      <div className="page-header">
        <div style={{ paddingBottom: 0 }}>
          <div className="flex gap-8" style={{ alignItems: 'center', marginBottom: 6 }}>
            <FileSearch size={18} color="var(--brand)" />
            <h1 className="page-title" style={{ margin: 0 }}>Medical Underwriting</h1>
            <span style={{ fontSize: 11, background: 'var(--brand-dim)', color: 'var(--brand)',
              padding: '2px 8px', borderRadius: 12, fontWeight: 700 }}>Phase 3</span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 0 }}>
            AI-powered insurance underwriting — risk class, premium loading, exclusions
          </p>
        </div>
      </div>

      <div className="page-content" style={{ maxWidth: 980, display: 'grid',
        gridTemplateColumns: '400px 1fr', gap: 20, alignItems: 'start' }}>

        {/* ── INPUT FORM ── */}
        <div>
          <div className="card">
            <div className="card-header"><span className="card-title">Applicant Details</span></div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div className="form-group">
                  <label className="form-label">Age *</label>
                  <input className="form-input" type="number" min="1" max="99"
                    placeholder="e.g. 35" value={form.age}
                    onChange={e => set('age', e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Gender</label>
                  <select className="form-select" value={form.gender}
                    onChange={e => set('gender', e.target.value)}>
                    <option value="MALE">Male</option>
                    <option value="FEMALE">Female</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Insurance Type</label>
                <select className="form-select" value={form.insurance_type}
                  onChange={e => set('insurance_type', e.target.value)}>
                  <option value="HEALTH">Health Insurance</option>
                  <option value="LIFE">Life Insurance (Term)</option>
                  <option value="CRITICAL_ILLNESS">Critical Illness</option>
                  <option value="PERSONAL_ACCIDENT">Personal Accident</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div className="form-group">
                  <label className="form-label">Sum Assured (₹)</label>
                  <input className="form-input" type="number"
                    placeholder="e.g. 1000000" value={form.sum_assured}
                    onChange={e => set('sum_assured', e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Policy Term (years)</label>
                  <input className="form-input" type="number" min="1" max="40"
                    placeholder="e.g. 20" value={form.policy_term_years}
                    onChange={e => set('policy_term_years', e.target.value)} />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Country / Jurisdiction</label>
                <select className="form-select" value={form.country}
                  onChange={e => set('country', e.target.value)}>
                  <option value="IN">🇮🇳 India (IRDAI)</option>
                  <option value="US">🇺🇸 USA (NAIC)</option>
                  <option value="GB">🇬🇧 UK (ABI)</option>
                  <option value="AE">🇦🇪 UAE (MOH)</option>
                  <option value="SG">🇸🇬 Singapore</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Medical Summary *</label>
                <textarea className="form-textarea" rows={7}
                  placeholder={`Paste medical history, recent reports, BMI, vitals, diagnoses, current medications, and any pre-existing conditions.\n\nExample:\nBMI: 28.5 (Overweight)\nBP: 140/90 (Hypertension - on Amlodipine 5mg)\nDiabetes Type 2 - diagnosed 2020, controlled on Metformin\nHbA1c: 7.2% (last test 3 months ago)\nNo history of heart disease or cancer\nNon-smoker, occasional alcohol`}
                  value={form.medical_summary}
                  onChange={e => set('medical_summary', e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">Additional Context (optional)</label>
                <textarea className="form-textarea" rows={2}
                  placeholder="Occupation, lifestyle, family history, recent travel, etc."
                  value={form.additional_context}
                  onChange={e => set('additional_context', e.target.value)} />
              </div>

              <button className="btn btn-primary" onClick={handleSubmit}
                disabled={loading} style={{ height: 42 }}>
                {loading
                  ? <><Loader size={15} style={{ animation: 'spin 0.7s linear infinite' }} /> Assessing Risk…</>
                  : <><FileSearch size={15} /> Run Underwriting Assessment</>}
              </button>
            </div>
          </div>

          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10,
            padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 8 }}>
            ⚠ For decision support only. All underwriting decisions must be reviewed and approved by
            a licensed underwriter. Not a substitute for professional judgment.
          </div>
        </div>

        {/* ── RESULTS ── */}
        <div>
          {!result && !loading && (
            <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
              <FileSearch size={40} style={{ color: 'var(--text-disabled)', margin: '0 auto 16px' }} />
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)' }}>
                Underwriting results appear here
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6 }}>
                Fill in applicant details and medical summary, then run assessment
              </div>
            </div>
          )}

          {loading && (
            <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
              <div className="spinner" style={{ margin: '0 auto 16px', width: 32, height: 32, borderWidth: 3 }} />
              <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                Analyzing medical history and assessing risk…
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                This takes 10–20 seconds
              </div>
            </div>
          )}

          {result && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>

              {/* Decision Banner */}
              <div style={{
                background: (DECISION_COLORS[decision] || 'var(--brand)') + '18',
                border: `1px solid ${(DECISION_COLORS[decision] || 'var(--brand)') + '50'}`,
                borderRadius: 'var(--radius-xl)', padding: '18px 22px', marginBottom: 16,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ color: DECISION_COLORS[decision] || 'var(--brand)' }}>
                    {DECISION_ICONS[decision]}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.07em',
                      textTransform: 'uppercase',
                      color: DECISION_COLORS[decision] || 'var(--brand)', marginBottom: 3 }}>
                      Underwriting Decision
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: -0.5 }}>
                      {(decision || '').replace(/_/g, ' ')}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                      Risk Class
                    </div>
                    <div style={{ fontSize: 15, fontWeight: 800,
                      color: RISK_COLORS[riskClass] || 'var(--text-primary)',
                      fontFamily: 'var(--font-mono)' }}>
                      {(riskClass || '').replace(/_/g, ' ')}
                    </div>
                  </div>
                </div>
              </div>

              {/* Risk Assessment */}
              <Collapsible title="Risk Assessment">
                <Row label="Overall Risk Class"
                  value={<span style={{ color: RISK_COLORS[riskClass], fontWeight: 700 }}>
                    {(riskClass || '').replace(/_/g, ' ')}
                  </span>} />
                <Row label="Mortality Risk"
                  value={result.risk_assessment?.mortality_risk} />
                <Row label="Morbidity Risk"
                  value={result.risk_assessment?.morbidity_risk} />
                <Row label="Risk Score"
                  value={`${result.risk_assessment?.risk_score} / 1000 (Standard = 100)`} />
                {result.risk_assessment?.risk_narrative && (
                  <div style={{ marginTop: 10, padding: '10px 14px',
                    background: 'var(--bg-elevated)', borderRadius: 8,
                    fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)' }}>
                    {result.risk_assessment.risk_narrative}
                  </div>
                )}
              </Collapsible>

              {/* Premium Loading */}
              {result.underwriting_decision && (
                <Collapsible title="Premium & Terms"
                  badge={result.underwriting_decision.premium_loading_percent
                    ? `+${result.underwriting_decision.premium_loading_percent}% loading` : null}>
                  <Row label="Decision"
                    value={(result.underwriting_decision.decision || '').replace(/_/g, ' ')} />
                  <Row label="Standard Premium" value="Base rate applies" />
                  {result.underwriting_decision.premium_loading_percent > 0 && (
                    <Row label="Premium Loading"
                      value={`+${result.underwriting_decision.premium_loading_percent}%`} />
                  )}
                  <Row label="Policy Term Restriction"
                    value={result.underwriting_decision.term_restriction || 'None'} />
                  {result.underwriting_decision.decision_rationale && (
                    <div style={{ marginTop: 10, padding: '10px 14px',
                      background: 'var(--bg-elevated)', borderRadius: 8,
                      fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)' }}>
                      {result.underwriting_decision.decision_rationale}
                    </div>
                  )}
                </Collapsible>
              )}

              {/* Exclusions */}
              {result.exclusions?.length > 0 && (
                <Collapsible title="Exclusions"
                  badge={`${result.exclusions.length} exclusion${result.exclusions.length > 1 ? 's' : ''}`}>
                  {result.exclusions.map((ex, i) => (
                    <div key={i} style={{
                      padding: '10px 14px', marginBottom: 8,
                      background: 'var(--investigate-dim, rgba(245,158,11,0.08))',
                      border: '1px solid rgba(245,158,11,0.2)',
                      borderRadius: 8,
                    }}>
                      <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 3 }}>
                        {ex.condition}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 3 }}>
                        {ex.exclusion_type} · Duration: {ex.duration || 'Permanent'}
                      </div>
                      {ex.rationale && (
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{ex.rationale}</div>
                      )}
                    </div>
                  ))}
                </Collapsible>
              )}

              {/* Additional Requirements */}
              {result.additional_requirements?.length > 0 && (
                <Collapsible title="Additional Requirements" defaultOpen={false}>
                  {result.additional_requirements.map((req, i) => (
                    <div key={i} style={{ padding: '8px 0',
                      borderBottom: '1px solid var(--border-subtle)',
                      display: 'flex', gap: 10 }}>
                      <div style={{ width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                        background: 'var(--brand)', marginTop: 7 }} />
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{req.requirement}</div>
                        {req.reason && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                          {req.reason}</div>}
                      </div>
                    </div>
                  ))}
                </Collapsible>
              )}

              {/* Medical Findings */}
              {result.medical_findings?.length > 0 && (
                <Collapsible title={`Medical Findings (${result.medical_findings.length})`}
                  defaultOpen={false}>
                  {result.medical_findings.map((f, i) => {
                    const sev = f.risk_impact
                    const sevColor = sev === 'HIGH' || sev === 'DECLINE' ? 'var(--reject)'
                      : sev === 'MODERATE' ? 'var(--investigate)' : 'var(--approve)'
                    return (
                      <div key={i} style={{ padding: '10px 0',
                        borderBottom: '1px solid var(--border-subtle)',
                        display: 'flex', gap: 12 }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 3 }}>
                            <span style={{ fontSize: 13, fontWeight: 700 }}>{f.condition}</span>
                            {f.icd10_code && <span style={{ fontFamily: 'var(--font-mono)',
                              fontSize: 11, color: 'var(--brand)',
                              background: 'var(--brand-dim)', padding: '1px 6px',
                              borderRadius: 5 }}>{f.icd10_code}</span>}
                            <span style={{ fontSize: 10, fontWeight: 700,
                              color: sevColor }}>{f.severity}</span>
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                            Controlled: {f.controlled ? '✓ Yes' : '✗ No'} ·
                            Risk impact: <span style={{ color: sevColor, fontWeight: 600 }}>
                              {f.risk_impact}</span>
                          </div>
                          {f.notes && <div style={{ fontSize: 12, color: 'var(--text-muted)',
                            marginTop: 3 }}>{f.notes}</div>}
                        </div>
                      </div>
                    )
                  })}
                </Collapsible>
              )}

              {/* Applicant Summary */}
              <Collapsible title="Applicant Summary" defaultOpen={false}>
                <Row label="Age" value={result.applicant_summary?.age} />
                <Row label="Gender" value={result.applicant_summary?.gender} />
                <Row label="BMI" value={result.applicant_summary?.bmi
                  ? `${result.applicant_summary.bmi} (${result.applicant_summary.bmi_category})` : null} />
                <Row label="Smoking" value={result.applicant_summary?.smoking_status} />
                <Row label="Occupation Risk" value={result.applicant_summary?.occupation_risk} />
              </Collapsible>

            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}
