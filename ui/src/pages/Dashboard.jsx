import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  TrendingUp, FileText, ShieldCheck, AlertTriangle,
  CheckCircle, XCircle, Clock, Activity, ArrowRight,
  RefreshCw, AlertCircle
} from 'lucide-react'
import { getAnalytics, listClaims } from '../utils/api'
import { fmtCurrency, fmtRelative, statusConfig } from '../utils/helpers'

const stagger = { animate: { transition: { staggerChildren: 0.07 } } }
const item    = { initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0 } }

export default function Dashboard() {
  const navigate = useNavigate()
  const [analytics, setAnalytics] = useState(null)
  const [recent,    setRecent]    = useState([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [a, c] = await Promise.all([
        getAnalytics(),
        listClaims({ page: 1, page_size: 8 })
      ])
      setAnalytics(a)
      setRecent(c.claims || [])
    } catch (e) {
      setError(e.message || 'Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const byStatus = analytics?.by_status || []
  const total    = byStatus.reduce((s, r) => s + r.count, 0)
  const approved = byStatus.find(r => r.status === 'APPROVED')?.count  || 0
  const hitl     = byStatus.find(r => r.status === 'HITL_REVIEW')?.count || 0
  const avgFraud = total > 0
    ? byStatus.reduce((s, r) => s + (r.avg_fraud_score || 0) * r.count, 0) / total
    : 0

  const stats = [
    { icon: <FileText size={16} />, iconBg: 'var(--brand-dim)', iconColor: 'var(--brand)',
      value: total, label: 'Total Claims', delta: null },
    { icon: <CheckCircle size={16} />, iconBg: 'var(--approve-dim)', iconColor: 'var(--approve)',
      value: approved, label: 'Approved',
      delta: total ? `${((approved/total)*100).toFixed(0)}% approval rate` : 'No data yet' },
    { icon: <Clock size={16} />, iconBg: 'var(--pending-dim)', iconColor: 'var(--pending)',
      value: hitl, label: 'Pending Review',
      delta: hitl > 0 ? 'Requires human review' : 'Queue clear ✓' },
    { icon: <AlertTriangle size={16} />, iconBg: 'var(--investigate-dim)', iconColor: 'var(--investigate)',
      value: `${(avgFraud * 100).toFixed(0)}%`, label: 'Avg Fraud Risk',
      delta: avgFraud < 0.3 ? 'Within normal range' : 'Elevated — review flagged' },
  ]

  return (
    <div>
      <div className="page-header">
        <div className="flex-between" style={{ paddingBottom: 20 }}>
          <div>
            <h1 className="page-title">Dashboard</h1>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
              AI-powered claims processing overview
            </p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
            <RefreshCw size={13} style={{ animation: loading ? 'spin 0.7s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>
      </div>

      <div className="page-content">
        {/* ERROR STATE */}
        {error && (
          <div style={{
            background: 'var(--reject-dim)', border: '1px solid rgba(239,68,68,0.3)',
            borderRadius: 'var(--radius-lg)', padding: '16px 20px',
            display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20
          }}>
            <AlertCircle size={18} color="var(--reject)" />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--reject)' }}>Failed to load dashboard</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{error}</div>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={load}>Retry</button>
          </div>
        )}

        {loading ? (
          <div className="loading-overlay"><div className="spinner" /><span>Loading dashboard…</span></div>
        ) : (
          <motion.div variants={stagger} initial="initial" animate="animate">

            {/* KPI GRID */}
            <motion.div variants={item} className="stat-grid">
              {stats.map((s, i) => (
                <div key={i} className="stat-card">
                  <div className="stat-icon" style={{ background: s.iconBg, color: s.iconColor }}>
                    {s.icon}
                  </div>
                  <div className="stat-value">{s.value}</div>
                  <div className="stat-label">{s.label}</div>
                  {s.delta && (
                    <div className="stat-delta" style={{ color: 'var(--text-muted)' }}>
                      <TrendingUp size={10} /> {s.delta}
                    </div>
                  )}
                </div>
              ))}
            </motion.div>

            {/* RECENT CLAIMS */}
            <motion.div variants={item} className="card">
              <div className="card-header">
                <div className="card-title">Recent Claims</div>
                <button className="btn btn-secondary btn-sm" onClick={() => navigate('/claims')}>
                  View all <ArrowRight size={12} />
                </button>
              </div>
              <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
                {recent.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-state-icon">📄</div>
                    <div className="empty-state-title">No claims yet</div>
                    <div className="empty-state-sub">Submit your first claim to get started</div>
                    <button className="btn btn-primary mt-12" onClick={() => navigate('/submit')}>
                      <FileText size={14} /> Submit Claim
                    </button>
                  </div>
                ) : (
                  <table>
                    <thead>
                      <tr>
                        <th>Claim ID</th>
                        <th>Claimant</th>
                        <th>Type</th>
                        <th>Amount</th>
                        <th>Fraud Risk</th>
                        <th>Status</th>
                        <th>Submitted</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recent.map(c => {
                        const sc  = statusConfig[c.status] || { label: c.status, cls: 'badge-pending', dot: '#888' }
                        const score = c.fraud_score
                        const lvl = score != null ? (score >= 0.75 ? 'high' : score >= 0.45 ? 'medium' : 'low') : null
                        return (
                          <tr key={c.claim_id} onClick={() => navigate(`/claims/${c.claim_id}`)}>
                            <td><span className="claim-id">{c.claim_id}</span></td>
                            <td style={{ color: 'var(--text-primary)' }}>{c.claimant_name || <span className="text-muted">Processing…</span>}</td>
                            <td className="text-secondary">{c.policy_type || '—'}</td>
                            <td>{c.claimed_amount ? fmtCurrency(c.claimed_amount, c.currency) : <span className="text-muted">—</span>}</td>
                            <td>
                              {score != null ? (
                                <div className={`fraud-gauge fraud-${lvl}`}>
                                  <div className="fraud-bar">
                                    <div className="fraud-fill" style={{ width: `${score * 100}%` }} />
                                  </div>
                                  <span className="fraud-score-text" style={{
                                    color: lvl === 'high' ? 'var(--risk-high)' :
                                           lvl === 'medium' ? 'var(--risk-medium)' : 'var(--risk-low)'
                                  }}>
                                    {(score * 100).toFixed(0)}%
                                  </span>
                                </div>
                              ) : <span className="text-muted">—</span>}
                            </td>
                            <td>
                              <span className={`badge ${sc.cls}`}>
                                <span className="badge-dot" style={{ background: sc.dot }} />
                                {sc.label}
                              </span>
                            </td>
                            <td className="text-muted text-sm">{fmtRelative(c.created_at)}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            </motion.div>

            {/* QUICK LINKS */}
            <motion.div variants={item} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginTop: 16 }}>
              {[
                { icon: '📤', label: 'Submit New Claim', desc: 'Upload PDF or image document', path: '/submit', color: 'var(--brand)' },
                { icon: '🔍', label: 'HITL Review Queue', desc: `${hitl} claim${hitl !== 1 ? 's' : ''} awaiting review`, path: '/hitl', color: 'var(--info)' },
                { icon: '📊', label: 'Analytics', desc: 'Fraud trends and claim insights', path: '/analytics', color: 'var(--approve)' },
              ].map(q => (
                <div key={q.label} className="card" style={{ cursor: 'pointer', transition: 'border-color var(--transition)' }}
                  onClick={() => navigate(q.path)}
                  onMouseEnter={e => e.currentTarget.style.borderColor = q.color}
                  onMouseLeave={e => e.currentTarget.style.borderColor = ''}>
                  <div className="card-body" style={{ padding: '16px 18px' }}>
                    <div style={{ fontSize: 24, marginBottom: 8 }}>{q.icon}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 3 }}>{q.label}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{q.desc}</div>
                  </div>
                </div>
              ))}
            </motion.div>

          </motion.div>
        )}
      </div>
    </div>
  )
}
