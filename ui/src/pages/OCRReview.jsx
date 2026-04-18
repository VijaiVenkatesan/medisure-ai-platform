/**
 * OCR Review & Edit Page
 *
 * Workflow:
 *   1. User uploads a document
 *   2. Backend runs OCR + extraction → returns raw data
 *   3. User reviews/corrects every field (catches errors like 5,260 → 61,260)
 *   4. User submits corrected data → full AI pipeline runs (Validate → Policy → Fraud → Decision)
 *
 * This prevents OCR errors from cascading into wrong claim amounts and decisions.
 */
import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload, AlertTriangle, CheckCircle, Edit3, ChevronDown, ChevronUp,
  Loader, Info, Eye, Send, RotateCcw, FileText
} from 'lucide-react'
import toast from 'react-hot-toast'
import { ocrPreview, submitClaimWithData } from '../utils/api'

// ── EDITABLE FIELD ────────────────────────────────────────────────
function Field({ label, value, onChange, type = 'text', hint }) {
  return (
    <div className="form-group">
      <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {label}
        {hint && (
          <span title={hint} style={{ cursor: 'help', color: 'var(--text-muted)' }}>
            <Info size={11} />
          </span>
        )}
      </label>
      <input
        className="form-input"
        type={type}
        value={value || ''}
        onChange={e => onChange(type === 'number' ? (e.target.value === '' ? '' : Number(e.target.value)) : e.target.value)}
        placeholder={`Enter ${label.toLowerCase()}`}
      />
    </div>
  )
}

// ── SECTION WRAPPER ───────────────────────────────────────────────
function Section({ title, icon, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card mb-12">
      <button className="card-header" style={{ width: '100%', background: 'none', border: 'none',
        cursor: 'pointer', color: 'inherit', textAlign: 'left' }}
        onClick={() => setOpen(o => !o)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--brand)' }}>{icon}</span>
          <span className="card-title">{title}</span>
        </div>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} style={{ overflow: 'hidden' }}>
            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 20px' }}>
                {children}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── MAIN PAGE ─────────────────────────────────────────────────────
export default function OCRReview() {
  const navigate = useNavigate()
  const fileRef  = useRef(null)

  // Step 1: upload
  const [file,        setFile]        = useState(null)
  const [uploading,   setUploading]   = useState(false)

  // Step 2: preview data
  const [preview,     setPreview]     = useState(null)   // raw API response
  const [ocrText,     setOcrText]     = useState('')
  const [showRawOCR,  setShowRawOCR]  = useState(false)

  // Editable claim data
  const [data, setData] = useState({})
  const set = (k, v) => setData(d => ({ ...d, [k]: v }))

  // Step 3: submit
  const [submitting, setSubmitting] = useState(false)

  // ── Step 1: upload and OCR ──
  const handleUpload = useCallback(async (f) => {
    if (!f) return
    setFile(f)
    setUploading(true)
    setPreview(null)
    setData({})

    const fd = new FormData()
    fd.append('file', f)

    try {
      const result = await ocrPreview(fd)
      setPreview(result)
      setOcrText(result.ocr_text || '')

      // Populate editable fields from extraction
      const e = result.extracted || {}
      setData({
        claimant_name:     e.claimant_name     || '',
        date_of_birth:     e.date_of_birth     || '',
        gender:            e.gender            || '',
        contact:           e.contact           || '',
        email:             e.email             || '',
        address:           e.address           || '',
        aadhaar_number:    e.aadhaar_number    || '',
        pan_number:        e.pan_number        || '',
        policy_number:     e.policy_number     || '',
        insurance_company: e.insurance_company || '',
        insurance_type:    e.insurance_type    || 'HEALTH',
        policy_start:      e.policy_start_date || '',
        policy_end:        e.policy_end_date   || '',
        sum_insured:       e.sum_insured       || '',
        incident_date:     e.incident_date     || '',
        reported_date:     e.reported_date     || '',
        hospital_name:     e.hospital_name     || '',
        doctor_name:       e.doctor_name       || '',
        diagnosis:         e.diagnosis         || '',
        treatment:         e.treatment         || '',
        claimed_amount:    e.claimed_amount    || '',
        currency:          e.currency          || 'INR',
        country:           e.country           || 'IN',
      })
      toast.success('OCR extraction complete — please review the data below')
    } catch (err) {
      toast.error(err.message)
      setFile(null)
    } finally {
      setUploading(false)
    }
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f) handleUpload(f)
  }, [handleUpload])

  // ── Step 2: submit reviewed data ──
  const handleSubmit = async () => {
    if (!data.claimed_amount) { toast.error('Claimed amount is required'); return }
    if (!data.insurance_type) { toast.error('Insurance type is required'); return }

    setSubmitting(true)
    try {
      const result = await submitClaimWithData({
        original_filename: file?.name || 'document',
        ocr_text: ocrText,
        ...data,
        claimed_amount: data.claimed_amount ? Number(data.claimed_amount) : null,
        sum_insured:    data.sum_insured    ? Number(data.sum_insured)    : null,
      })
      toast.success('Claim submitted successfully!')
      navigate(`/claims/${result.claim_id}`)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const confidence = preview?.ocr_confidence ?? null
  const confColor  = confidence >= 0.9 ? 'var(--approve)' : confidence >= 0.7 ? 'var(--investigate)' : 'var(--reject)'

  return (
    <div>
      <div className="page-header">
        <div style={{ paddingBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <Edit3 size={18} color="var(--brand)" />
            <h1 className="page-title" style={{ margin: 0 }}>OCR Review & Submit</h1>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            Upload → AI extracts data → <strong>you review & correct</strong> → submit to AI pipeline
          </p>
        </div>
      </div>

      <div className="page-content" style={{ maxWidth: 900 }}>

        {/* ── STEP 1: UPLOAD ── */}
        {!preview && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div
              onDrop={handleDrop}
              onDragOver={e => e.preventDefault()}
              onClick={() => !uploading && fileRef.current?.click()}
              style={{
                border: `2px dashed ${uploading ? 'var(--brand)' : 'var(--border-strong)'}`,
                borderRadius: 'var(--radius-xl)', padding: '48px 32px',
                textAlign: 'center', cursor: uploading ? 'wait' : 'pointer',
                background: uploading ? 'var(--brand-dim)' : 'var(--bg-surface)',
                transition: 'all var(--transition)',
              }}
            >
              {uploading ? (
                <>
                  <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3, margin: '0 auto 16px' }} />
                  <div style={{ fontSize: 15, fontWeight: 600 }}>Running OCR extraction…</div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6 }}>
                    AI is reading your document — this takes 10–20 seconds
                  </div>
                </>
              ) : (
                <>
                  <Upload size={40} style={{ color: 'var(--text-disabled)', margin: '0 auto 14px' }} />
                  <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>
                    Drop your document here
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 14 }}>
                    PDF, PNG, JPG, TIFF · Max 10MB · Scanned documents supported
                  </div>
                  <button className="btn btn-primary" style={{ pointerEvents: 'none' }}>
                    <Upload size={14} /> Choose File
                  </button>
                </>
              )}
              <input ref={fileRef} type="file" style={{ display: 'none' }}
                accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
                onChange={e => e.target.files[0] && handleUpload(e.target.files[0])} />
            </div>

            {/* Why review? banner */}
            <div style={{
              marginTop: 16, padding: '12px 16px', borderRadius: 'var(--radius-md)',
              background: 'var(--investigate-dim)', border: '1px solid rgba(245,158,11,0.25)',
              display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 13,
            }}>
              <AlertTriangle size={15} color="var(--investigate)" style={{ flexShrink: 0, marginTop: 1 }} />
              <div style={{ color: 'var(--text-secondary)', lineHeight: 1.65 }}>
                <strong style={{ color: 'var(--investigate)' }}>Why review before submitting?</strong>
                {' '}OCR can misread numbers — for example, ₹5,260 might be extracted as ₹61,260.
                Reviewing lets you correct any errors before the AI makes a decision based on them.
              </div>
            </div>
          </motion.div>
        )}

        {/* ── STEP 2: REVIEW & EDIT ── */}
        {preview && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>

            {/* Status banner */}
            <div style={{
              padding: '14px 18px', borderRadius: 'var(--radius-lg)', marginBottom: 20,
              background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
              display: 'flex', alignItems: 'center', gap: 14,
            }}>
              <CheckCircle size={18} color="var(--approve)" style={{ flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 700 }}>
                  OCR complete — review the extracted data below
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                  {file?.name} · {confidence !== null && (
                    <span style={{ color: confColor }}>
                      {(confidence * 100).toFixed(0)}% OCR confidence
                    </span>
                  )} · Correct any errors before submitting
                </div>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => {
                setPreview(null); setFile(null); setData({})
              }}>
                <RotateCcw size={13} /> New Document
              </button>
            </div>

            {/* ── Claimed Amount — most critical field, shown prominently ── */}
            <div style={{
              padding: '16px 20px', borderRadius: 'var(--radius-lg)', marginBottom: 16,
              background: 'var(--brand-dim)', border: '1px solid var(--brand-glow)',
            }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--brand)',
                marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                <AlertTriangle size={13} /> VERIFY CAREFULLY — Claimed Amount & Currency
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                <Field label="Claimed Amount *" value={data.claimed_amount} type="number"
                  hint="Double-check: OCR can misread numbers. Verify against your document."
                  onChange={v => set('claimed_amount', v)} />
                <Field label="Currency" value={data.currency}
                  onChange={v => set('currency', v)} />
                <div className="form-group">
                  <label className="form-label">Insurance Type</label>
                  <select className="form-select" value={data.insurance_type || 'HEALTH'}
                    onChange={e => set('insurance_type', e.target.value)}>
                    {['HEALTH','LIFE','MOTOR','PROPERTY','TRAVEL','CROP','PERSONAL_ACCIDENT'].map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* ── Claimant ── */}
            <Section title="Claimant Information" icon={<FileText size={15} />}>
              <Field label="Full Name"      value={data.claimant_name}   onChange={v => set('claimant_name', v)} />
              <Field label="Date of Birth"  value={data.date_of_birth}   onChange={v => set('date_of_birth', v)} />
              <Field label="Gender"         value={data.gender}          onChange={v => set('gender', v)} />
              <Field label="Contact"        value={data.contact}         onChange={v => set('contact', v)} />
              <Field label="Email"          value={data.email}           onChange={v => set('email', v)} />
              <Field label="Aadhaar"        value={data.aadhaar_number}  onChange={v => set('aadhaar_number', v)} />
              <Field label="PAN"            value={data.pan_number}      onChange={v => set('pan_number', v)} />
              <Field label="Address"        value={data.address}         onChange={v => set('address', v)} />
            </Section>

            {/* ── Policy ── */}
            <Section title="Policy Details" icon={<FileText size={15} />} defaultOpen={false}>
              <Field label="Policy Number"     value={data.policy_number}      onChange={v => set('policy_number', v)} />
              <Field label="Insurance Company" value={data.insurance_company}  onChange={v => set('insurance_company', v)} />
              <Field label="Policy Start Date" value={data.policy_start}       onChange={v => set('policy_start', v)} />
              <Field label="Policy End Date"   value={data.policy_end}         onChange={v => set('policy_end', v)} />
              <Field label="Sum Insured"       value={data.sum_insured} type="number" onChange={v => set('sum_insured', v)} />
            </Section>

            {/* ── Incident ── */}
            <Section title="Incident Details" icon={<AlertTriangle size={15} />} defaultOpen={false}>
              <Field label="Incident Date"  value={data.incident_date}  onChange={v => set('incident_date', v)} />
              <Field label="Reported Date"  value={data.reported_date}  onChange={v => set('reported_date', v)} />
              <Field label="Hospital"       value={data.hospital_name}  onChange={v => set('hospital_name', v)} />
              <Field label="Doctor"         value={data.doctor_name}    onChange={v => set('doctor_name', v)} />
              <Field label="Diagnosis"      value={data.diagnosis}      onChange={v => set('diagnosis', v)} />
              <Field label="Treatment"      value={data.treatment}      onChange={v => set('treatment', v)} />
              <div className="form-group">
                <label className="form-label">Country</label>
                <select className="form-select" value={data.country || 'IN'}
                  onChange={e => set('country', e.target.value)}>
                  <option value="IN">🇮🇳 India</option>
                  <option value="US">🇺🇸 USA</option>
                  <option value="GB">🇬🇧 UK</option>
                  <option value="AE">🇦🇪 UAE</option>
                  <option value="SG">🇸🇬 Singapore</option>
                </select>
              </div>
            </Section>

            {/* ── Raw OCR text ── */}
            <div className="card mb-12">
              <button className="card-header" style={{ width: '100%', background: 'none', border: 'none',
                cursor: 'pointer', color: 'inherit', textAlign: 'left' }}
                onClick={() => setShowRawOCR(o => !o)}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Eye size={14} color="var(--text-muted)" />
                  <span className="card-title" style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                    Raw OCR Text (for reference)
                  </span>
                </div>
                {showRawOCR ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              <AnimatePresence initial={false}>
                {showRawOCR && (
                  <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }}
                    exit={{ height: 0 }} style={{ overflow: 'hidden' }}>
                    <div className="card-body">
                      <textarea className="form-textarea" rows={10} value={ocrText}
                        onChange={e => setOcrText(e.target.value)}
                        style={{ fontFamily: 'var(--font-mono)', fontSize: 11, lineHeight: 1.7 }} />
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                        You can edit the raw OCR text above if needed. Changes are preserved with the claim.
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* ── Submit ── */}
            <div style={{
              display: 'flex', gap: 12, justifyContent: 'flex-end',
              padding: '16px 0', borderTop: '1px solid var(--border-subtle)',
            }}>
              <button className="btn btn-secondary" onClick={() => {
                setPreview(null); setFile(null); setData({})
              }}>
                <RotateCcw size={14} /> Start Over
              </button>
              <button className="btn btn-primary" onClick={handleSubmit}
                disabled={submitting || !data.claimed_amount}
                style={{ minWidth: 180, height: 42 }}>
                {submitting
                  ? <><Loader size={15} style={{ animation: 'spin 0.7s linear infinite' }} /> Submitting…</>
                  : <><Send size={15} /> Submit to AI Pipeline</>}
              </button>
            </div>

          </motion.div>
        )}
      </div>
    </div>
  )
}
