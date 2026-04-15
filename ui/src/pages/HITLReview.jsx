import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ShieldCheck, CheckCircle, XCircle, AlertTriangle,
  User, FileText, RefreshCw, ChevronRight, X, ExternalLink
} from 'lucide-react'
import toast from 'react-hot-toast'
import { getPendingHITL, getClaim, submitHITLReview } from '../utils/api'
import { fmtCurrency, fmtRelative, fmtDate } from '../utils/helpers'

// ── REVIEWER PANEL ────────────────────────────
function ReviewPanel({ claim, onComplete, onClose }) {
  const [action,   setAction]   = useState(null)   // APPROVE | REJECT | INVESTIGATE
  const [amount,   setAmount]   = useState('')
  const [notes,    setNotes]    = useState('')
  const [reason,   setReason]   = useState('')
  const [submitting, setSubmitting] = useState(false)

  const ed  = claim.extracted_data || {}
  const cli = ed.claimant  || {}
  const pol = ed.policy    || {}
  const inc = ed.incident  || {}
  const amt = ed.amounts   || {}

  const fraudScore  = claim.fraud_score
  const fraudLevel  = claim.fraud_level
  const fraudColor  = fraudLevel === 'HIGH' || fraudLevel === 'CRITICAL' ? 'var(--risk-high)'
                    : fraudLevel === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)'

  const handleSubmit = async () => {
    if (!action) { toast.error('Select an action first'); return }
    if (action === 'REJECT' && !reason.trim()) { toast.error('Rejection reason is required'); return }
    if (!notes.trim()) { toast.error('Review notes are required'); return }

    setSubmitting(true)
    try {
      await submitHITLReview(claim.claim_id, {
        action,
        reviewer_id: 'reviewer_' + Math.random().toString(36).slice(2, 7),
        reviewer_notes: notes,
        approved_amount: action === 'APPROVE' && amount ? parseFloat(amount) : null,
        rejection_reason: action === 'REJECT' ? reason : null,
      })
      toast.success(`Claim ${action.toLowerCase()}d successfully`)
      onComplete()
    } catch (e) {
      toast.error(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const ACTIONS = [
    {
      key: 'APPROVE', label: 'Approve', icon: <CheckCircle size={16} />,
      cls: 'btn-approve', desc: 'Approve the claim and process payment'
    },
    {
      key: 'REJECT', label: 'Reject', icon: <XCircle size={16} />,
      cls: 'btn-reject', desc: 'Reject the claim with reason'
    },
    {
      key: 'INVESTIGATE', label: 'Investigate', icon: <AlertTriangle size={16} />,
      cls: 'btn-investigate', desc: 'Route to investigation team'
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 24 }}
      style={{
        position: 'fixed', top: 0, right: 0, bottom: 0,
        width: 520, background: 'var(--bg-surface)',
        borderLeft: '1px solid var(--border-default)',
        zIndex: 100, display: 'flex', flexDirection: 'column',
        boxShadow: 'var(--shadow-lg)',
      }}
    >
      {/* Header */}
      <div style={{
        padding: '20px 24px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex', alignItems: 'center', gap: 12,
        background: 'var(--bg-elevated)',
      }}>
        <ShieldCheck size={18} color="var(--brand)" />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>HITL Review Panel</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
            {claim.claim_id}
          </div>
        </div>
        <button className="btn btn-secondary btn-sm btn-icon" onClick={onClose}><X size={14} /></button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>

        {/* CLAIM SUMMARY */}
        <div style={{
          background: 'var(--bg-elevated)', borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)', padding: '16px', marginBottom: 20
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 20px' }}>
            {[
              ['Claimant', cli.name || '—'],
              ['Policy Type', pol.policy_type || '—'],
              ['Company', pol.insurance_company || '—'],
              ['Claimed Amount', amt.claimed_amount ? fmtCurrency(amt.claimed_amount, amt.currency) : '—'],
              ['Incident Date', inc.incident_date || '—'],
              ['Hospital/Location', inc.hospital_name || inc.incident_location || '—'],
              ['Diagnosis', inc.diagnosis || inc.incident_description?.slice(0, 40) || '—'],
              ['Policy No.', pol.policy_number || '—'],
            ].map(([label, value]) => (
              <div key={label}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3 }}>{label}</div>
                <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>{value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* FRAUD SUMMARY */}
        <div style={{
          background: fraudLevel === 'HIGH' || fraudLevel === 'CRITICAL' ? 'var(--reject-dim)' : fraudLevel === 'MEDIUM' ? 'var(--investigate-dim)' : 'var(--approve-dim)',
          borderRadius: 'var(--radius-lg)',
          border: `1px solid ${fraudColor}33`,
          padding: '14px 16px', marginBottom: 20,
          display: 'flex', alignItems: 'center', gap: 14,
        }}>
          <div style={{ fontSize: 32, fontWeight: 800, fontFamily: 'var(--font-mono)', color: fraudColor, lineHeight: 1 }}>
            {fraudScore != null ? `${(fraudScore * 100).toFixed(0)}%` : '—'}
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: fraudColor, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {fraudLevel || 'Unknown'} Fraud Risk
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
              AI risk assessment score
            </div>
          </div>
        </div>

        {/* AI DECISION CONTEXT */}
        {claim.decision && (
          <div style={{
            background: 'var(--bg-elevated)', borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)', padding: '14px 16px', marginBottom: 20
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
              AI Decision Recommendation
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{
                background: claim.decision === 'APPROVE' ? 'var(--approve-dim)' : claim.decision === 'REJECT' ? 'var(--reject-dim)' : 'var(--investigate-dim)',
                color: claim.decision === 'APPROVE' ? 'var(--approve)' : claim.decision === 'REJECT' ? 'var(--reject)' : 'var(--investigate)',
                padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700
              }}>{claim.decision}</span>
              {claim.decision_confidence && (
                <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {(claim.decision_confidence * 100).toFixed(0)}% confident
                </span>
              )}
            </div>
            {claim.explanation && (
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{claim.explanation}</p>
            )}
          </div>
        )}

        {/* ACTION SELECTION */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 10 }}>
            Your Decision
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {ACTIONS.map(a => (
              <button
                key={a.key}
                onClick={() => setAction(a.key)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '12px 16px', borderRadius: 'var(--radius-md)',
                  border: action === a.key
                    ? `2px solid ${a.key === 'APPROVE' ? 'var(--approve)' : a.key === 'REJECT' ? 'var(--reject)' : 'var(--investigate)'}`
                    : '2px solid var(--border-default)',
                  background: action === a.key
                    ? a.key === 'APPROVE' ? 'var(--approve-dim)' : a.key === 'REJECT' ? 'var(--reject-dim)' : 'var(--investigate-dim)'
                    : 'var(--bg-elevated)',
                  cursor: 'pointer', textAlign: 'left', transition: 'all var(--transition)',
                  color: action === a.key
                    ? a.key === 'APPROVE' ? 'var(--approve)' : a.key === 'REJECT' ? 'var(--reject)' : 'var(--investigate)'
                    : 'var(--text-secondary)',
                }}
              >
                {a.icon}
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{a.label}</div>
                  <div style={{ fontSize: 11, opacity: 0.8 }}>{a.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* APPROVE AMOUNT */}
        {action === 'APPROVE' && (
          <div className="form-group" style={{ marginBottom: 16 }}>
            <label className="form-label">Approved Amount (leave blank for full claim)</label>
            <input
              className="form-input"
              type="number"
              placeholder={`₹ ${amt.claimed_amount || '0'}`}
              value={amount}
              onChange={e => setAmount(e.target.value)}
            />
          </div>
        )}

        {/* REJECTION REASON */}
        {action === 'REJECT' && (
          <div className="form-group" style={{ marginBottom: 16 }}>
            <label className="form-label">Rejection Reason <span style={{ color: 'var(--reject)' }}>*</span></label>
            <textarea
              className="form-textarea"
              placeholder="Explain why this claim is being rejected (shown to claimant)…"
              value={reason}
              onChange={e => setReason(e.target.value)}
              rows={3}
            />
          </div>
        )}

        {/* REVIEW NOTES */}
        <div className="form-group" style={{ marginBottom: 20 }}>
          <label className="form-label">Reviewer Notes <span style={{ color: 'var(--reject)' }}>*</span></label>
          <textarea
            className="form-textarea"
            placeholder="Add your observations, verification steps taken, and reasoning…"
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={4}
          />
        </div>
      </div>

      {/* FOOTER */}
      <div style={{
        padding: '16px 24px',
        borderTop: '1px solid var(--border-subtle)',
        background: 'var(--bg-elevated)',
        display: 'flex', gap: 10,
      }}>
        <button className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose} disabled={submitting}>
          Cancel
        </button>
        <button
          className={`btn ${action === 'APPROVE' ? 'btn-approve' : action === 'REJECT' ? 'btn-reject' : action === 'INVESTIGATE' ? 'btn-investigate' : 'btn-primary'}`}
          style={{ flex: 2 }}
          onClick={handleSubmit}
          disabled={!action || submitting}
        >
          {submitting ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Submitting…</>
            : action ? `Submit: ${action}` : 'Select an action'}
        </button>
      </div>
    </motion.div>
  )
}

// ── CLAIM QUEUE ITEM ─────────────────────────
function QueueItem({ claim, isActive, onClick }) {
  const fraudScore = claim.fraud_score
  const fraudLevel = claim.fraud_level || 'LOW'
  const fraudColor = fraudLevel === 'HIGH' || fraudLevel === 'CRITICAL' ? 'var(--risk-high)'
                   : fraudLevel === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)'

  const ed  = claim.extracted_data || {}
  const pol = ed.policy   || {}
  const amt = ed.amounts  || {}

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={onClick}
      style={{
        padding: '14px 16px',
        borderRadius: 'var(--radius-md)',
        border: isActive ? '1.5px solid var(--brand)' : '1.5px solid var(--border-subtle)',
        background: isActive ? 'var(--brand-dim)' : 'var(--bg-surface)',
        cursor: 'pointer',
        marginBottom: 8,
        transition: 'all var(--transition)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: isActive ? 'var(--brand)' : 'var(--text-primary)', fontWeight: 600 }}>
              {claim.claim_id}
            </span>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 500, marginBottom: 2 }}>
            {claim.claimant_name || 'Unknown Claimant'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {pol.policy_type || claim.policy_type || '—'}
            </span>
            <span style={{ fontSize: 10, color: 'var(--text-disabled)' }}>·</span>
            <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>
              {claim.claimed_amount ? fmtCurrency(claim.claimed_amount, claim.currency) : '—'}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          {fraudScore != null && (
            <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-mono)', color: fraudColor }}>
              {(fraudScore * 100).toFixed(0)}%
            </div>
          )}
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{fmtRelative(claim.created_at)}</div>
          <ChevronRight size={12} style={{ color: isActive ? 'var(--brand)' : 'var(--text-muted)' }} />
        </div>
      </div>
    </motion.div>
  )
}

// ── MAIN PAGE ────────────────────────────────
export default function HITLReview() {
  const navigate = useNavigate()
  const [queue,      setQueue]      = useState([])
  const [selected,   setSelected]   = useState(null)
  const [detail,     setDetail]     = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [detailLoad, setDetailLoad] = useState(false)
  const [panelOpen,  setPanelOpen]  = useState(false)

  const loadQueue = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getPendingHITL()
      setQueue(data.claims)
      if (data.claims.length > 0 && !selected) {
        selectClaim(data.claims[0])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadQueue() }, [loadQueue])

  const selectClaim = async (claim) => {
    setSelected(claim)
    setDetailLoad(true)
    try {
      const full = await getClaim(claim.claim_id)
      setDetail(full)
    } catch (e) {
      console.error(e)
    } finally {
      setDetailLoad(false)
    }
  }

  const handleComplete = () => {
    setPanelOpen(false)
    setSelected(null)
    setDetail(null)
    loadQueue()
  }

  const ed  = detail?.extracted_data || {}
  const pol = ed.policy  || {}
  const inc = ed.incident|| {}
  const amt = ed.amounts || {}

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>

      {/* ── LEFT: QUEUE ── */}
      <div style={{
        width: 320, flexShrink: 0,
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex', flexDirection: 'column',
        background: 'var(--bg-surface)',
      }}>
        <div style={{ padding: '20px 16px 14px', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <div style={{ fontSize: 14, fontWeight: 700 }}>Review Queue</div>
            <button className="btn btn-secondary btn-sm btn-icon" onClick={loadQueue} disabled={loading}>
              <RefreshCw size={13} />
            </button>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {queue.length} claim{queue.length !== 1 ? 's' : ''} pending review
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 12px' }}>
          {loading ? (
            <div className="loading-overlay" style={{ padding: 40 }}>
              <div className="spinner" />
            </div>
          ) : queue.length === 0 ? (
            <div className="empty-state" style={{ padding: '48px 16px' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>🎉</div>
              <div className="empty-state-title">Queue clear!</div>
              <div className="empty-state-sub">No claims awaiting review</div>
            </div>
          ) : (
            queue.map(c => (
              <QueueItem
                key={c.claim_id}
                claim={c}
                isActive={selected?.claim_id === c.claim_id}
                onClick={() => selectClaim(c)}
              />
            ))
          )}
        </div>
      </div>

      {/* ── RIGHT: DETAIL ── */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        {!selected ? (
          <div className="flex-center" style={{ flex: 1, flexDirection: 'column', gap: 12, color: 'var(--text-muted)' }}>
            <ShieldCheck size={40} style={{ opacity: 0.3 }} />
            <div style={{ fontSize: 14 }}>Select a claim to review</div>
          </div>
        ) : detailLoad ? (
          <div className="loading-overlay" style={{ flex: 1 }}>
            <div className="spinner" /><span>Loading claim details…</span>
          </div>
        ) : detail && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ flex: 1 }}>
            {/* DETAIL HEADER */}
            <div style={{
              padding: '20px 24px',
              borderBottom: '1px solid var(--border-subtle)',
              background: 'var(--bg-elevated)',
              display: 'flex', alignItems: 'flex-start', gap: 16,
            }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                  <span style={{ fontSize: 15, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                    {detail.claim_id}
                  </span>
                  <span className="badge badge-hitl">HITL Review</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  Submitted {fmtRelative(detail.created_at)} · {ed.country || 'IN'}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/claims/${detail.claim_id}`)}>
                  <ExternalLink size={13} /> Full View
                </button>
                <button className="btn btn-primary btn-sm" onClick={() => setPanelOpen(true)}>
                  <ShieldCheck size={13} /> Review
                </button>
              </div>
            </div>

            {/* SUMMARY CARDS */}
            <div style={{ padding: '20px 24px', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
              {[
                { label: 'Claimant', value: ed.claimant?.name || '—', icon: <User size={14} /> },
                { label: 'Claimed Amount', value: amt.claimed_amount ? fmtCurrency(amt.claimed_amount, amt.currency) : '—', icon: <span style={{ fontSize: 13 }}>₹</span> },
                { label: 'Policy Type', value: pol.policy_type || '—', icon: <FileText size={14} /> },
              ].map(s => (
                <div key={s.label} style={{
                  background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)', padding: '12px 14px',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, color: 'var(--text-muted)', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {s.icon} {s.label}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{s.value}</div>
                </div>
              ))}
            </div>

            {/* FRAUD + DECISION */}
            <div style={{ padding: '0 24px 20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>

              {/* Fraud box */}
              <div style={{
                background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)', padding: '16px',
              }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
                  Fraud Risk
                </div>
                {detail.fraud_score != null ? (
                  <>
                    <div style={{
                      fontSize: 40, fontWeight: 800, fontFamily: 'var(--font-mono)', lineHeight: 1, marginBottom: 6,
                      color: detail.fraud_level === 'HIGH' || detail.fraud_level === 'CRITICAL' ? 'var(--risk-high)'
                           : detail.fraud_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)'
                    }}>
                      {(detail.fraud_score * 100).toFixed(0)}%
                    </div>
                    <div style={{ height: 4, background: 'var(--bg-elevated)', borderRadius: 2, marginBottom: 8, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', borderRadius: 2,
                        width: `${detail.fraud_score * 100}%`,
                        background: detail.fraud_level === 'HIGH' || detail.fraud_level === 'CRITICAL' ? 'var(--risk-high)'
                                  : detail.fraud_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)',
                        transition: 'width 0.8s ease',
                      }} />
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em',
                      color: detail.fraud_level === 'HIGH' || detail.fraud_level === 'CRITICAL' ? 'var(--risk-high)'
                           : detail.fraud_level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)'
                    }}>
                      {detail.fraud_level} RISK
                    </div>
                  </>
                ) : <div className="text-muted">Not analysed yet</div>}
              </div>

              {/* Decision box */}
              <div style={{
                background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)', padding: '16px',
              }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
                  AI Recommendation
                </div>
                {detail.decision ? (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      {detail.decision === 'APPROVE'
                        ? <CheckCircle size={20} color="var(--approve)" />
                        : detail.decision === 'REJECT'
                        ? <XCircle size={20} color="var(--reject)" />
                        : <AlertTriangle size={20} color="var(--investigate)" />}
                      <span style={{
                        fontSize: 16, fontWeight: 700,
                        color: detail.decision === 'APPROVE' ? 'var(--approve)' : detail.decision === 'REJECT' ? 'var(--reject)' : 'var(--investigate)'
                      }}>{detail.decision}</span>
                      {detail.decision_confidence && (
                        <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                          {(detail.decision_confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    {detail.explanation && (
                      <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                        {detail.explanation.slice(0, 200)}{detail.explanation.length > 200 ? '…' : ''}
                      </p>
                    )}
                  </>
                ) : <div className="text-muted">No AI decision yet</div>}
              </div>
            </div>

            {/* INCIDENT DESCRIPTION */}
            {inc.incident_description && (
              <div style={{ padding: '0 24px 24px' }}>
                <div style={{
                  background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-lg)', padding: '16px',
                }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                    Incident Description
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                    {inc.incident_description}
                  </p>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </div>

      {/* ── SLIDE-IN REVIEW PANEL ── */}
      <AnimatePresence>
        {panelOpen && detail && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setPanelOpen(false)}
              style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 99 }}
            />
            <ReviewPanel
              claim={detail}
              onComplete={handleComplete}
              onClose={() => setPanelOpen(false)}
            />
          </>
        )}
      </AnimatePresence>
    </div>
  )
}


