import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft, RefreshCw, User, Shield, AlertTriangle,
  CheckCircle, XCircle, Clock, FileText, Activity,
  ChevronDown, ChevronUp, ExternalLink
} from 'lucide-react'
import { getClaim, getAuditTrail } from '../utils/api'
import {
  fmtCurrency, fmtDate, fmtRelative,
  statusConfig, decisionConfig,
  PIPELINE_STEPS, statusToStepIndex
} from '../utils/helpers'

// ── SECTION COLLAPSE ─────────────────────────
function Section({ title, icon, defaultOpen = true, children, accent }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card mb-16">
      <button
        className="card-header"
        style={{ width: '100%', cursor: 'pointer', background: 'none', border: 'none', color: 'inherit', textAlign: 'left' }}
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex gap-8" style={{ alignItems: 'center' }}>
          <span style={{ color: accent || 'var(--brand)', display: 'flex' }}>{icon}</span>
          <span className="card-title">{title}</span>
        </div>
        {open ? <ChevronUp size={15} style={{ color: 'var(--text-muted)' }} />
               : <ChevronDown size={15} style={{ color: 'var(--text-muted)' }} />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            <div className="card-body">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── FIELD ROW ────────────────────────────────
function Field({ label, value, mono, empty = '—' }) {
  const display = value ?? null
  return (
    <div className="field-row">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? 'mono' : ''} ${!display ? 'empty' : ''}`}>
        {display ?? empty}
      </span>
    </div>
  )
}

// ── FRAUD SCORE VISUAL ────────────────────────
function FraudScore({ score, level, indicators = [], notes }) {
  const color = level === 'CRITICAL' || level === 'HIGH' ? 'var(--risk-high)'
              : level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)'

  return (
    <div>
      {/* Big score */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, marginBottom: 16 }}>
        <div style={{ fontSize: 48, fontWeight: 800, lineHeight: 1, color, fontFamily: 'var(--font-mono)', letterSpacing: -2 }}>
          {score != null ? `${(score * 100).toFixed(0)}%` : '—'}
        </div>
        <div style={{ paddingBottom: 6 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color, letterSpacing: '0.05em', textTransform: 'uppercase' }}>{level}</div>
          <div className="text-sm text-secondary">fraud risk score</div>
        </div>
      </div>

      {/* Bar */}
      {score != null && (
        <div style={{ height: 6, background: 'var(--bg-elevated)', borderRadius: 3, marginBottom: 16, overflow: 'hidden' }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${score * 100}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            style={{ height: '100%', background: color, borderRadius: 3 }}
          />
        </div>
      )}

      {/* Indicators */}
      {indicators.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div className="text-xs" style={{ color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 2 }}>
            Indicators
          </div>
          {indicators.map((ind, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'flex-start', gap: 10,
              padding: '9px 12px', background: 'var(--bg-elevated)',
              borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)'
            }}>
              <div style={{
                width: 6, height: 6, borderRadius: '50%', flexShrink: 0, marginTop: 5,
                background: ind.weight >= 0.3 ? 'var(--risk-high)' : ind.weight >= 0.15 ? 'var(--risk-medium)' : 'var(--risk-low)'
              }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 600, fontFamily: 'var(--font-mono)', marginBottom: 2, color: 'var(--text-primary)' }}>
                  {ind.indicator}
                </div>
                <div className="text-sm text-secondary">{ind.description}</div>
              </div>
              <div style={{
                fontSize: 11, fontFamily: 'var(--font-mono)',
                color: ind.weight >= 0.3 ? 'var(--risk-high)' : ind.weight >= 0.15 ? 'var(--risk-medium)' : 'var(--text-muted)',
                fontWeight: 600, whiteSpace: 'nowrap'
              }}>
                +{(ind.weight * 100).toFixed(0)}
              </div>
            </div>
          ))}
        </div>
      )}

      {notes && (
        <div className="text-sm text-secondary" style={{ marginTop: 12, padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
          {notes}
        </div>
      )}
    </div>
  )
}

// ── DECISION BOX ─────────────────────────────
function DecisionBox({ claim }) {
  const dec = claim.decision
  const cfg = decisionConfig[dec] || decisionConfig.PENDING
  const Icon = dec === 'APPROVE' ? CheckCircle : dec === 'REJECT' ? XCircle : AlertTriangle

  return (
    <div className={`decision-box ${cfg.cls}`}>
      <div className="decision-header">
        <Icon size={20} color={cfg.color} />
        <span className="decision-label" style={{ color: cfg.color }}>{cfg.label}</span>
        {claim.decision_confidence != null && (
          <span className="decision-confidence">
            {(claim.decision_confidence * 100).toFixed(0)}% confidence
          </span>
        )}
      </div>
      {claim.explanation && (
        <p className="decision-explanation">{claim.explanation}</p>
      )}
      {claim.decision === 'APPROVE' && claim.decision_confidence != null && (
        <div style={{ marginTop: 10, fontSize: 13, color: cfg.color, fontWeight: 600 }}>
          Approved Amount: {fmtCurrency(
            claim.extracted_data?.amounts?.claimed_amount,
            claim.extracted_data?.amounts?.currency
          )}
        </div>
      )}
    </div>
  )
}

// ── AUDIT TRAIL ──────────────────────────────
function AuditTrail({ claimId }) {
  const [logs,    setLogs]    = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAuditTrail(claimId)
      .then(setLogs)
      .catch(() => setLogs([]))
      .finally(() => setLoading(false))
  }, [claimId])

  const eventColor = (type) => {
    if (type.includes('APPROVED') || type.includes('APPROVE')) return 'var(--approve)'
    if (type.includes('REJECTED') || type.includes('REJECT'))  return 'var(--reject)'
    if (type.includes('ERROR'))     return 'var(--risk-high)'
    if (type.includes('FRAUD'))     return 'var(--investigate)'
    if (type.includes('HITL'))      return 'var(--info)'
    return 'var(--brand)'
  }

  if (loading) return <div className="loading-overlay" style={{ padding: 24 }}><div className="spinner" /></div>
  if (!logs.length) return <div className="empty-state" style={{ padding: 24 }}>No audit events yet</div>

  return (
    <div className="agent-trace">
      {logs.map((log, i) => (
        <motion.div
          key={log.id}
          className="trace-item"
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.04 }}
        >
          <div className="trace-dot" style={{ background: eventColor(log.event_type) }} />
          <div className="trace-meta">
            <div className="trace-agent">{log.event_type.replace(/_/g, ' ')}</div>
            <div className="trace-detail">
              Actor: <strong>{log.actor}</strong>
              {log.details && Object.keys(log.details).length > 0 && (
                <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>
                  {Object.entries(log.details)
                    .filter(([k]) => !['correlation_id','filename'].includes(k))
                    .slice(0, 3)
                    .map(([k, v]) => `${k}: ${typeof v === 'number' ? (typeof v === 'number' && k.includes('score') ? (v*100).toFixed(0)+'%' : v) : String(v).slice(0,40)}`)
                    .join(' · ')}
                </span>
              )}
            </div>
          </div>
          <div className="trace-time">{fmtDate(log.timestamp)}</div>
        </motion.div>
      ))}
    </div>
  )
}

// ── MAIN PAGE ────────────────────────────────
export default function ClaimDetail() {
  const { id }    = useParams()
  const navigate  = useNavigate()
  const [claim,   setClaim]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getClaim(id)
      setClaim(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
    // Auto-refresh if still processing
    const iv = setInterval(() => {
      if (claim && ['APPROVED','REJECTED','INVESTIGATING','ERROR'].includes(claim.status)) {
        clearInterval(iv)
        return
      }
      load()
    }, 5000)
    return () => clearInterval(iv)
  }, [load])

  if (loading && !claim) return (
    <div className="loading-overlay" style={{ height: '60vh' }}>
      <div className="spinner" /><span>Loading claim…</span>
    </div>
  )

  if (error) return (
    <div className="page-content">
      <div className="empty-state">
        <XCircle size={36} color="var(--reject)" />
        <div className="empty-state-title">Claim not found</div>
        <div className="empty-state-sub">{error}</div>
        <button className="btn btn-secondary mt-12" onClick={() => navigate('/claims')}>← Back to Claims</button>
      </div>
    </div>
  )

  const sc  = statusConfig[claim.status]  || { label: claim.status, cls: 'badge-pending', dot: '#888' }
  const ed  = claim.extracted_data || {}
  const cli = ed.claimant  || {}
  const pol = ed.policy    || {}
  const inc = ed.incident  || {}
  const amt = ed.amounts   || {}

  const stepIdx   = statusToStepIndex(claim.status)
  const isTerminal = ['APPROVED','REJECTED','INVESTIGATING','HITL_REVIEW','ERROR'].includes(claim.status)
  const isProcessing = !isTerminal

  const fraudIndicators = claim.fraud_indicators || []

  return (
    <div>
      {/* ── PAGE HEADER ── */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingBottom: 20 }}>
          <button className="btn btn-secondary btn-sm btn-icon" onClick={() => navigate('/claims')}>
            <ArrowLeft size={15} />
          </button>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
              <h1 style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)', letterSpacing: -0.5 }}>{id}</h1>
              <span className={`badge ${sc.cls}`}>
                <span className="badge-dot" style={{ background: sc.dot }} />{sc.label}
              </span>
              {isProcessing && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--brand)' }}>
                  <div className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }} /> Processing…
                </span>
              )}
            </div>
            <div className="text-sm text-secondary">
              Submitted {fmtRelative(claim.created_at)} · Updated {fmtRelative(claim.updated_at)}
            </div>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
            <RefreshCw size={13} /> Refresh
          </button>
          {claim.status === 'HITL_REVIEW' && (
            <button className="btn btn-primary btn-sm" onClick={() => navigate('/hitl')}>
              <ShieldCheck size={13} /> Review Now
            </button>
          )}
        </div>
      </div>

      <div className="page-content">
        {/* ── PIPELINE ── */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card mb-16">
          <div className="card-body">
            <div className="pipeline">
              {PIPELINE_STEPS.map((step, i) => {
                const state =
                  claim.status === 'ERROR'  ? (i === 2 ? 'error' : i < 2 ? 'completed' : 'idle')
                  : i < stepIdx  ? 'completed'
                  : i === stepIdx ? (isTerminal ? 'completed' : 'active')
                  : 'idle'
                return (
                  <div key={step.key} className={`pipeline-step ${state}`}>
                    <div className="step-circle">
                      {state === 'completed' ? '✓' : state === 'error' ? '✕' : i + 1}
                    </div>
                    <div className="step-label">{step.label}</div>
                  </div>
                )
              })}
            </div>
          </div>
        </motion.div>

        {/* ── DECISION ── */}
        {claim.decision && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mb-16">
            <DecisionBox claim={{ ...claim, explanation: claim.explanation }} />
          </motion.div>
        )}

        {/* ── TWO-COLUMN LAYOUT ── */}
        <div className="detail-grid">
          {/* LEFT */}
          <div>
            {/* CLAIMANT */}
            <Section title="Claimant Information" icon={<User size={15} />}>
              <div className="field-group">
                <Field label="Full Name"       value={cli.name} />
                <Field label="Date of Birth"   value={cli.dob} />
                <Field label="Gender"          value={cli.gender} />
                <Field label="Contact"         value={cli.contact_number} mono />
                <Field label="Email"           value={cli.email} />
                <Field label="Address"         value={cli.address} />
                <Field label="Aadhaar"         value={cli.aadhaar_number} mono />
                <Field label="PAN"             value={cli.pan_number} mono />
                <Field label="National ID"     value={cli.national_id} mono />
              </div>
            </Section>

            {/* POLICY */}
            <Section title="Policy Details" icon={<FileText size={15} />} accent="var(--info)">
              <div className="field-group">
                <Field label="Policy Number"   value={pol.policy_number} mono />
                <Field label="Company"         value={pol.insurance_company} />
                <Field label="Type"            value={pol.policy_type} />
                <Field label="Start Date"      value={pol.policy_start_date} />
                <Field label="End Date"        value={pol.policy_end_date} />
                <Field label="Sum Insured"     value={pol.sum_insured != null ? fmtCurrency(pol.sum_insured, amt.currency) : null} />
                <Field label="Premium"         value={pol.premium_amount != null ? fmtCurrency(pol.premium_amount, amt.currency) : null} />
              </div>
            </Section>

            {/* INCIDENT */}
            <Section title="Incident Details" icon={<AlertTriangle size={15} />} accent="var(--investigate)">
              <div className="field-group">
                <Field label="Incident Date"   value={inc.incident_date} />
                <Field label="Reported Date"   value={inc.reported_date} />
                <Field label="Location"        value={inc.incident_location} />
                <Field label="Description"     value={inc.incident_description} />
                <Field label="Hospital"        value={inc.hospital_name} />
                <Field label="Doctor"          value={inc.doctor_name} />
                <Field label="Diagnosis"       value={inc.diagnosis} />
                <Field label="Vehicle No."     value={inc.vehicle_number} mono />
                <Field label="Treatment"       value={inc.treatment_details} />
              </div>
            </Section>

            {/* AMOUNTS */}
            <Section title="Claim Amounts" icon={<span style={{ fontSize: 14 }}>₹</span>} accent="var(--approve)">
              <div className="field-group">
                <Field label="Claimed Amount"
                  value={amt.claimed_amount != null ? fmtCurrency(amt.claimed_amount, amt.currency) : null} />
                <Field label="Currency" value={amt.currency} />
                {amt.breakdown && Object.keys(amt.breakdown).length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div className="field-label" style={{ marginBottom: 8 }}>Breakdown</div>
                    {Object.entries(amt.breakdown).map(([k, v]) => (
                      <div key={k} className="field-row" style={{ marginBottom: 4 }}>
                        <span className="field-label text-xs">{k}</span>
                        <span className="field-value">{fmtCurrency(v, amt.currency)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Section>
          </div>

          {/* RIGHT */}
          <div>
            {/* FRAUD */}
            <Section title="Fraud Analysis" icon={<Shield size={15} />} accent="var(--risk-high)">
              <FraudScore
                score={claim.fraud_score}
                level={claim.fraud_level || '—'}
                indicators={fraudIndicators}
                notes={null}
              />
            </Section>

            {/* VALIDATION */}
            {ed.extraction_confidence != null && (
              <Section title="Extraction Quality" icon={<Activity size={15} />} defaultOpen={false}>
                <div className="field-group">
                  <Field label="OCR Confidence"       value={ed.extraction_confidence != null ? `${(ed.extraction_confidence * 100).toFixed(0)}%` : null} />
                  <Field label="Country"              value={ed.country} />
                  <Field label="Extraction Notes"     value={ed.extraction_notes} />
                </div>
              </Section>
            )}

            {/* ERRORS */}
            {(claim.errors || []).length > 0 && (
              <Section title="Processing Errors" icon={<XCircle size={15} />} accent="var(--reject)" defaultOpen>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {claim.errors.map((e, i) => (
                    <div key={i} style={{
                      padding: '9px 12px', background: 'var(--reject-dim)',
                      borderRadius: 'var(--radius-md)', fontSize: 12, color: 'var(--reject)',
                      border: '1px solid rgba(239,68,68,0.2)'
                    }}>
                      {e}
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* AUDIT TRAIL */}
            <Section title="Audit Trail" icon={<Clock size={15} />} defaultOpen={false} accent="var(--text-muted)">
              <AuditTrail claimId={id} />
            </Section>
          </div>
        </div>
      </div>
    </div>
  )
}

// Silence unused import warning
function ShieldCheck({ size }) {
  return <Shield size={size} />
}
