import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Stethoscope, Pill, Activity, ChevronDown, ChevronUp,
  Plus, X, Loader, AlertTriangle, Info
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  clinicalDiagnose,
  clinicalDrugInteractions,
  clinicalRiskStratify
} from '../utils/api'

const TABS = [
  { id: 'diagnose',  icon: <Stethoscope size={15} />, label: 'Diagnosis Assist' },
  { id: 'drugs',     icon: <Pill size={15} />,         label: 'Drug Interactions' },
  { id: 'risk',      icon: <Activity size={15} />,     label: 'Risk Stratification' },
]

const SEVERITY_COLORS = {
  CONTRAINDICATED: 'var(--reject)',
  MAJOR:           '#f97316',
  MODERATE:        'var(--investigate)',
  MINOR:           'var(--info)',
  NONE:            'var(--approve)',
}

function Collapsible({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card mb-12">
      <button className="card-header" style={{ width: '100%', background: 'none',
        border: 'none', cursor: 'pointer', color: 'inherit', textAlign: 'left' }}
        onClick={() => setOpen(o => !o)}>
        <span className="card-title">{title}</span>
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

// ── TagInput: type and press Enter to add items ──────────────────────
function TagInput({ items, setItems, placeholder, color = 'var(--brand)' }) {
  const [val, setVal] = useState('')
  const add = () => {
    const t = val.trim()
    if (t && !items.includes(t)) setItems([...items, t])
    setVal('')
  }
  const remove = (i) => setItems(items.filter((_, idx) => idx !== i))
  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <input className="form-input" placeholder={placeholder}
          value={val} onChange={e => setVal(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
          style={{ flex: 1 }} />
        <button type="button" className="btn btn-secondary btn-sm"
          onClick={add} disabled={!val.trim()}>
          <Plus size={13} /> Add
        </button>
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {items.map((item, i) => (
          <span key={i} style={{
            background: color + '15', border: `1px solid ${color}40`,
            color, borderRadius: 20, padding: '3px 10px',
            fontSize: 12, display: 'flex', alignItems: 'center', gap: 5,
          }}>
            {item}
            <button onClick={() => remove(i)}
              style={{ background: 'none', border: 'none', cursor: 'pointer',
                color, padding: 0, lineHeight: 1 }}>
              <X size={11} />
            </button>
          </span>
        ))}
      </div>
    </div>
  )
}

// ── DIAGNOSIS TAB ────────────────────────────────────────────────────
function DiagnosisTab() {
  const [symptoms, setSymptoms] = useState([])
  const [age,     setAge]     = useState('')
  const [gender,  setGender]  = useState('MALE')
  const [duration, setDuration] = useState('')
  const [history, setHistory] = useState('')
  const [labs,    setLabs]    = useState('')
  const [country, setCountry] = useState('IN')
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)

  const handleSubmit = async () => {
    if (!symptoms.length) { toast.error('Add at least one symptom'); return }
    if (!age) { toast.error('Enter patient age'); return }
    setLoading(true); setResult(null)
    try {
      const r = await clinicalDiagnose({
        symptoms, patient_age: parseInt(age), patient_gender: gender,
        duration, medical_history: history, lab_results: labs, country,
      })
      setResult(r)
    } catch (e) { toast.error(e.message) }
    finally { setLoading(false) }
  }

  const urgency = result?.urgency_level
  const urgencyColor = urgency === 'EMERGENCY' ? 'var(--reject)'
    : urgency === 'URGENT' ? '#f97316'
    : urgency === 'SEMI_URGENT' ? 'var(--investigate)'
    : 'var(--approve)'

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 20 }}>
      <div>
        <div className="card">
          <div className="card-header"><span className="card-title">Clinical Presentation</span></div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label className="form-label">Symptoms * (press Enter to add)</label>
              <TagInput items={symptoms} setItems={setSymptoms}
                placeholder="e.g. fever, headache, cough…" color="var(--brand)" />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div className="form-group">
                <label className="form-label">Age *</label>
                <input className="form-input" type="number" min="0" max="120"
                  placeholder="years" value={age} onChange={e => setAge(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Gender</label>
                <select className="form-select" value={gender}
                  onChange={e => setGender(e.target.value)}>
                  <option value="MALE">Male</option>
                  <option value="FEMALE">Female</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Duration</label>
              <input className="form-input" placeholder="e.g. 3 days, 2 weeks…"
                value={duration} onChange={e => setDuration(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Medical History</label>
              <textarea className="form-textarea" rows={3}
                placeholder="Relevant past medical history, medications, allergies…"
                value={history} onChange={e => setHistory(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Lab Results (optional)</label>
              <textarea className="form-textarea" rows={2}
                placeholder="CBC, LFT, RFT, blood sugar, etc…"
                value={labs} onChange={e => setLabs(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Country / Guidelines</label>
              <select className="form-select" value={country}
                onChange={e => setCountry(e.target.value)}>
                <option value="IN">🇮🇳 India (ICMR + Tropical diseases)</option>
                <option value="US">🇺🇸 USA (CDC guidelines)</option>
                <option value="GB">🇬🇧 UK (NICE guidelines)</option>
                <option value="AE">🇦🇪 UAE</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={handleSubmit}
              disabled={loading || !symptoms.length} style={{ height: 42 }}>
              {loading
                ? <><Loader size={15} style={{ animation: 'spin 0.7s linear infinite' }} /> Analyzing…</>
                : <><Stethoscope size={15} /> Get Differential Diagnoses</>}
            </button>
          </div>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8,
          padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 8 }}>
          ⚠ Decision support only. Not a substitute for clinical examination and professional judgment.
        </div>
      </div>

      <div>
        {!result && !loading && (
          <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
            <Stethoscope size={40} style={{ color: 'var(--text-disabled)', margin: '0 auto 16px' }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)' }}>
              Add symptoms and run analysis
            </div>
          </div>
        )}

        {loading && (
          <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
            <div className="spinner" style={{ margin: '0 auto 16px', width: 32, height: 32, borderWidth: 3 }} />
            <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
              Analyzing clinical presentation…
            </div>
          </div>
        )}

        {result && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            {/* Urgency banner */}
            {urgency && (
              <div style={{
                background: urgencyColor + '15', border: `1px solid ${urgencyColor}40`,
                borderRadius: 'var(--radius-lg)', padding: '12px 16px', marginBottom: 14,
                display: 'flex', alignItems: 'center', gap: 10,
              }}>
                <AlertTriangle size={16} color={urgencyColor} />
                <div>
                  <span style={{ fontWeight: 700, color: urgencyColor, fontSize: 13 }}>
                    Urgency: {urgency?.replace(/_/g, ' ')}
                  </span>
                  {result.clinical_summary && (
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                      {result.clinical_summary}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Differentials */}
            <Collapsible title={`Differential Diagnoses (${result.differential_diagnoses?.length || 0})`}>
              {result.differential_diagnoses?.map((d, i) => {
                const probColor = d.probability >= 70 ? 'var(--brand)'
                  : d.probability >= 40 ? 'var(--investigate)' : 'var(--text-muted)'
                return (
                  <div key={i} style={{ padding: '12px 0',
                    borderBottom: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                      <span style={{ fontSize: 22, fontFamily: 'var(--font-mono)',
                        fontWeight: 800, color: probColor, minWidth: 42 }}>
                        #{i + 1}
                      </span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 14, fontWeight: 700 }}>{d.diagnosis}</div>
                        {d.icd10_code && (
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11,
                            color: 'var(--brand)', background: 'var(--brand-dim)',
                            padding: '1px 6px', borderRadius: 5 }}>{d.icd10_code}</span>
                        )}
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 18, fontWeight: 800, color: probColor,
                          fontFamily: 'var(--font-mono)' }}>{d.probability}%</div>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>probability</div>
                      </div>
                    </div>
                    {d.supporting_features?.length > 0 && (
                      <div style={{ marginLeft: 52 }}>
                        <div style={{ fontSize: 11, color: 'var(--approve)', fontWeight: 600,
                          marginBottom: 2 }}>Supporting:</div>
                        {d.supporting_features.map((f, j) => (
                          <div key={j} style={{ fontSize: 12, color: 'var(--text-secondary)',
                            paddingLeft: 8 }}>✓ {f}</div>
                        ))}
                      </div>
                    )}
                    {d.against_features?.length > 0 && (
                      <div style={{ marginLeft: 52, marginTop: 4 }}>
                        <div style={{ fontSize: 11, color: 'var(--reject)', fontWeight: 600,
                          marginBottom: 2 }}>Against:</div>
                        {d.against_features.map((f, j) => (
                          <div key={j} style={{ fontSize: 12, color: 'var(--text-secondary)',
                            paddingLeft: 8 }}>✗ {f}</div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </Collapsible>

            {/* Recommended Investigations */}
            {result.recommended_investigations?.length > 0 && (
              <Collapsible title="Recommended Investigations">
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {result.recommended_investigations.map((inv, i) => (
                    <span key={i} style={{
                      background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
                      borderRadius: 20, padding: '4px 12px', fontSize: 12,
                    }}>{inv}</span>
                  ))}
                </div>
              </Collapsible>
            )}

            {/* Red Flags */}
            {result.red_flags?.length > 0 && (
              <Collapsible title="⚠ Red Flags">
                {result.red_flags.map((f, i) => (
                  <div key={i} style={{ fontSize: 13, color: 'var(--reject)',
                    padding: '5px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                    {f}
                  </div>
                ))}
              </Collapsible>
            )}

            {/* Management */}
            {result.immediate_management && (
              <Collapsible title="Immediate Management" defaultOpen={false}>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                  {result.immediate_management}
                </p>
                {result.referral_needed && (
                  <div style={{ marginTop: 8, fontSize: 13, fontWeight: 600,
                    color: 'var(--investigate)' }}>
                    → Referral recommended: {result.referral_specialty || 'specialist'}
                  </div>
                )}
              </Collapsible>
            )}
          </motion.div>
        )}
      </div>
    </div>
  )
}

// ── DRUG INTERACTIONS TAB ─────────────────────────────────────────────
function DrugTab() {
  const [meds,       setMeds]       = useState([])
  const [conditions, setConditions] = useState([])
  const [age,        setAge]        = useState('')
  const [renal,      setRenal]      = useState('')
  const [hepatic,    setHepatic]    = useState('')
  const [loading,    setLoading]    = useState(false)
  const [result,     setResult]     = useState(null)

  const handleSubmit = async () => {
    if (meds.length < 1) { toast.error('Add at least one medication'); return }
    setLoading(true); setResult(null)
    try {
      const r = await clinicalDrugInteractions({
        medications: meds, patient_age: parseInt(age) || 40,
        conditions: conditions.length ? conditions : null,
        renal_function: renal || null,
        hepatic_function: hepatic || null,
      })
      setResult(r)
    } catch (e) { toast.error(e.message) }
    finally { setLoading(false) }
  }

  const worstSeverity = result?.interactions?.reduce((worst, ix) => {
    const order = ['NONE','MINOR','MODERATE','MAJOR','CONTRAINDICATED']
    return order.indexOf(ix.severity) > order.indexOf(worst) ? ix.severity : worst
  }, 'NONE')

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 20 }}>
      <div>
        <div className="card">
          <div className="card-header"><span className="card-title">Medications</span></div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label className="form-label">Medications * (press Enter to add)</label>
              <TagInput items={meds} setItems={setMeds}
                placeholder="e.g. Metformin 500mg, Amlodipine 5mg…"
                color="var(--info)" />
            </div>
            <div>
              <label className="form-label">Medical Conditions (optional)</label>
              <TagInput items={conditions} setItems={setConditions}
                placeholder="e.g. Diabetes, CKD, Hypertension…"
                color="var(--text-secondary)" />
            </div>
            <div className="form-group">
              <label className="form-label">Patient Age</label>
              <input className="form-input" type="number" placeholder="years"
                value={age} onChange={e => setAge(e.target.value)} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div className="form-group">
                <label className="form-label">Renal Function</label>
                <select className="form-select" value={renal}
                  onChange={e => setRenal(e.target.value)}>
                  <option value="">Normal</option>
                  <option value="MILD_CKD">Mild CKD (GFR 60-89)</option>
                  <option value="MODERATE_CKD">Moderate CKD (GFR 30-59)</option>
                  <option value="SEVERE_CKD">Severe CKD (GFR &lt;30)</option>
                  <option value="ESRD">ESRD / Dialysis</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Hepatic Function</label>
                <select className="form-select" value={hepatic}
                  onChange={e => setHepatic(e.target.value)}>
                  <option value="">Normal</option>
                  <option value="MILD">Mild impairment</option>
                  <option value="MODERATE">Moderate impairment</option>
                  <option value="SEVERE">Severe impairment</option>
                </select>
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleSubmit}
              disabled={loading || meds.length < 1} style={{ height: 42 }}>
              {loading
                ? <><Loader size={15} style={{ animation: 'spin 0.7s linear infinite' }} /> Checking…</>
                : <><Pill size={15} /> Check Drug Interactions</>}
            </button>
          </div>
        </div>
      </div>

      <div>
        {!result && !loading && (
          <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
            <Pill size={40} style={{ color: 'var(--text-disabled)', margin: '0 auto 16px' }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)' }}>
              Add medications to check for interactions
            </div>
          </div>
        )}
        {loading && (
          <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
            <div className="spinner" style={{ margin: '0 auto 16px', width: 32, height: 32, borderWidth: 3 }} />
            <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>Checking interactions…</div>
          </div>
        )}
        {result && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            {worstSeverity && worstSeverity !== 'NONE' && (
              <div style={{
                background: (SEVERITY_COLORS[worstSeverity] || 'var(--brand)') + '15',
                border: `1px solid ${(SEVERITY_COLORS[worstSeverity] || 'var(--brand)') + '40'}`,
                borderRadius: 'var(--radius-lg)', padding: '12px 16px', marginBottom: 14,
                display: 'flex', gap: 10, alignItems: 'center',
              }}>
                <AlertTriangle size={16} color={SEVERITY_COLORS[worstSeverity]} />
                <span style={{ fontSize: 14, fontWeight: 700,
                  color: SEVERITY_COLORS[worstSeverity] }}>
                  {worstSeverity} interaction detected
                </span>
              </div>
            )}

            <Collapsible title={`Interactions Found (${result.interactions?.length || 0})`}>
              {result.interactions?.length === 0 ? (
                <div style={{ color: 'var(--approve)', fontSize: 13 }}>
                  ✓ No significant interactions detected
                </div>
              ) : (
                result.interactions?.map((ix, i) => (
                  <div key={i} style={{ padding: '12px 0',
                    borderBottom: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start',
                      marginBottom: 6 }}>
                      <span style={{
                        background: (SEVERITY_COLORS[ix.severity] || 'var(--brand)') + '20',
                        color: SEVERITY_COLORS[ix.severity] || 'var(--brand)',
                        padding: '2px 8px', borderRadius: 10, fontSize: 10,
                        fontWeight: 700, flexShrink: 0, marginTop: 1,
                      }}>{ix.severity}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: 700 }}>
                          {ix.drug1} + {ix.drug2}
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)',
                          marginTop: 3, lineHeight: 1.6 }}>{ix.description}</div>
                        {ix.management && (
                          <div style={{ fontSize: 12, color: 'var(--brand)', marginTop: 4,
                            fontWeight: 600 }}>→ {ix.management}</div>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </Collapsible>

            {result.renal_adjustments?.length > 0 && (
              <Collapsible title="Renal Dose Adjustments" defaultOpen={false}>
                {result.renal_adjustments.map((r, i) => (
                  <div key={i} style={{ padding: '8px 0',
                    borderBottom: '1px solid var(--border-subtle)', fontSize: 13 }}>
                    <strong>{r.drug}</strong>: {r.recommendation}
                  </div>
                ))}
              </Collapsible>
            )}

            {result.overall_safety_assessment && (
              <div className="card" style={{ background: 'var(--bg-elevated)' }}>
                <div className="card-body">
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)',
                    textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
                    Overall Assessment
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                    {result.overall_safety_assessment}
                  </p>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  )
}

// ── RISK STRATIFICATION TAB ──────────────────────────────────────────
function RiskTab() {
  const [riskType, setRiskType]  = useState('CARDIOVASCULAR')
  const [loading,  setLoading]   = useState(false)
  const [result,   setResult]    = useState(null)
  const [patientData, setPatientData] = useState({
    age: '', gender: 'MALE', smoking: false, diabetes: false,
    hypertension: false, bmi: '', systolic_bp: '', total_cholesterol: '',
    hdl_cholesterol: '', family_history: false,
  })
  const set = (k, v) => setPatientData(p => ({ ...p, [k]: v }))

  const handleSubmit = async () => {
    if (!patientData.age) { toast.error('Enter age'); return }
    setLoading(true); setResult(null)
    try {
      const r = await clinicalRiskStratify({
        patient_data: { ...patientData, age: parseInt(patientData.age) || 40 },
        risk_type: riskType,
      })
      setResult(r)
    } catch (e) { toast.error(e.message) }
    finally { setLoading(false) }
  }

  const riskCategory = result?.risk_category
  const catColor = riskCategory === 'VERY_HIGH' ? 'var(--reject)'
    : riskCategory === 'HIGH' ? '#f97316'
    : riskCategory === 'MODERATE' ? 'var(--investigate)'
    : 'var(--approve)'

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 20 }}>
      <div>
        <div className="card">
          <div className="card-header"><span className="card-title">Patient Risk Profile</span></div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Risk Type</label>
              <select className="form-select" value={riskType}
                onChange={e => setRiskType(e.target.value)}>
                <option value="CARDIOVASCULAR">Cardiovascular Risk</option>
                <option value="DIABETES">Diabetes Risk</option>
                <option value="CANCER">Cancer Risk</option>
                <option value="READMISSION">Hospital Readmission</option>
              </select>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div className="form-group">
                <label className="form-label">Age *</label>
                <input className="form-input" type="number" placeholder="years"
                  value={patientData.age} onChange={e => set('age', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Gender</label>
                <select className="form-select" value={patientData.gender}
                  onChange={e => set('gender', e.target.value)}>
                  <option value="MALE">Male</option>
                  <option value="FEMALE">Female</option>
                </select>
              </div>
            </div>
            {[
              ['bmi', 'BMI', 'e.g. 27.5'],
              ['systolic_bp', 'Systolic BP (mmHg)', 'e.g. 130'],
              ['total_cholesterol', 'Total Cholesterol (mg/dL)', 'e.g. 200'],
              ['hdl_cholesterol', 'HDL Cholesterol (mg/dL)', 'e.g. 50'],
            ].map(([key, label, ph]) => (
              <div key={key} className="form-group">
                <label className="form-label">{label}</label>
                <input className="form-input" type="number" placeholder={ph}
                  value={patientData[key]}
                  onChange={e => set(key, e.target.value)} />
              </div>
            ))}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[
                ['smoking', '🚬 Smoker'],
                ['diabetes', '🩸 Diabetes'],
                ['hypertension', '💊 Hypertension'],
                ['family_history', '🧬 Family History'],
              ].map(([key, label]) => (
                <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 8,
                  cursor: 'pointer', fontSize: 13, padding: '6px 10px',
                  background: patientData[key] ? 'var(--brand-dim)' : 'var(--bg-elevated)',
                  border: `1px solid ${patientData[key] ? 'var(--brand-glow)' : 'var(--border-subtle)'}`,
                  borderRadius: 8, transition: 'all var(--transition)',
                }}>
                  <input type="checkbox" checked={patientData[key]}
                    onChange={e => set(key, e.target.checked)}
                    style={{ accentColor: 'var(--brand)' }} />
                  {label}
                </label>
              ))}
            </div>
            <button className="btn btn-primary" onClick={handleSubmit}
              disabled={loading} style={{ height: 42, marginTop: 4 }}>
              {loading
                ? <><Loader size={15} style={{ animation: 'spin 0.7s linear infinite' }} /> Calculating…</>
                : <><Activity size={15} /> Calculate Risk Score</>}
            </button>
          </div>
        </div>
      </div>

      <div>
        {!result && !loading && (
          <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
            <Activity size={40} style={{ color: 'var(--text-disabled)', margin: '0 auto 16px' }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)' }}>
              Risk stratification results appear here
            </div>
          </div>
        )}
        {loading && (
          <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
            <div className="spinner" style={{ margin: '0 auto 16px', width: 32, height: 32, borderWidth: 3 }} />
            <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>Calculating risk score…</div>
          </div>
        )}
        {result && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <div style={{
              background: catColor + '15', border: `1px solid ${catColor}40`,
              borderRadius: 'var(--radius-xl)', padding: '20px 24px', marginBottom: 16,
              display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, textAlign: 'center',
            }}>
              {[
                { label: 'Risk Category', value: (riskCategory || '').replace(/_/g, ' '),
                  color: catColor, big: true },
                { label: 'Risk Score', value: result.risk_score != null
                    ? `${result.risk_score}/100` : '—', color: catColor },
                { label: '10-Year Risk', value: result.ten_year_risk_percent != null
                    ? `${result.ten_year_risk_percent}%` : '—', color: catColor },
              ].map(s => (
                <div key={s.label}>
                  <div style={{ fontSize: s.big ? 20 : 24, fontWeight: 800,
                    color: s.color, fontFamily: 'var(--font-mono)',
                    letterSpacing: -0.5, marginBottom: 4 }}>{s.value}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.label}</div>
                </div>
              ))}
            </div>

            {result.risk_narrative && (
              <div className="card" style={{ marginBottom: 12 }}>
                <div className="card-body">
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                    {result.risk_narrative}
                  </p>
                </div>
              </div>
            )}

            {result.modifiable_factors?.length > 0 && (
              <Collapsible title="Modifiable Risk Factors">
                {result.modifiable_factors.map((f, i) => (
                  <div key={i} style={{ padding: '8px 0',
                    borderBottom: '1px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{f.factor}</div>
                    {f.intervention && <div style={{ fontSize: 12,
                      color: 'var(--brand)', marginTop: 2 }}>→ {f.intervention}</div>}
                  </div>
                ))}
              </Collapsible>
            )}

            {result.recommended_interventions?.length > 0 && (
              <Collapsible title="Recommended Interventions" defaultOpen={false}>
                {result.recommended_interventions.map((r, i) => (
                  <div key={i} style={{ padding: '6px 0',
                    borderBottom: '1px solid var(--border-subtle)', fontSize: 13 }}>• {r}</div>
                ))}
              </Collapsible>
            )}
          </motion.div>
        )}
      </div>
    </div>
  )
}

// ── MAIN PAGE ─────────────────────────────────────────────────────────
export default function ClinicalDecisionSupport() {
  const [tab, setTab] = useState(0)

  return (
    <div>
      <div className="page-header">
        <div style={{ paddingBottom: 0 }}>
          <div className="flex gap-8" style={{ alignItems: 'center', marginBottom: 6 }}>
            <Stethoscope size={18} color="var(--brand)" />
            <h1 className="page-title" style={{ margin: 0 }}>Clinical Decision Support</h1>
            <span style={{ fontSize: 11, background: 'var(--brand-dim)', color: 'var(--brand)',
              padding: '2px 8px', borderRadius: 12, fontWeight: 700 }}>Phase 3</span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
            Evidence-based AI assistance for diagnosis, drug safety, and patient risk assessment
          </p>
          <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border-subtle)' }}>
            {TABS.map((t, i) => (
              <button key={t.id} onClick={() => setTab(i)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 7,
                  padding: '10px 20px', background: 'none', border: 'none',
                  borderBottom: tab === i ? '2px solid var(--brand)' : '2px solid transparent',
                  color: tab === i ? 'var(--brand)' : 'var(--text-secondary)',
                  fontWeight: tab === i ? 600 : 400, cursor: 'pointer',
                  fontSize: 13, fontFamily: 'var(--font-sans)',
                  transition: 'all var(--transition)',
                }}>
                {t.icon} {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="page-content">
        <AnimatePresence mode="wait">
          <motion.div key={tab}
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
            {tab === 0 && <DiagnosisTab />}
            {tab === 1 && <DrugTab />}
            {tab === 2 && <RiskTab />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
