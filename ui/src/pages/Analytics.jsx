import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { getAnalytics, listClaims } from '../utils/api'
import { fmtCurrency } from '../utils/helpers'

const STATUS_COLORS = {
  APPROVED:         '#10b981',
  REJECTED:         '#ef4444',
  HITL_REVIEW:      '#3b82f6',
  INVESTIGATING:    '#f59e0b',
  DECISION_PENDING: '#6366f1',
  FRAUD_ANALYSIS:   '#00c9a7',
  POLICY_CHECK:     '#00c9a7',
  VALIDATING:       '#00c9a7',
  EXTRACTING:       '#00c9a7',
  OCR_PROCESSING:   '#00c9a7',
  RECEIVED:         '#4a5568',
  ERROR:            '#dc2626',
}

const FRAUD_BUCKETS = [
  { label: '0–20%',   key: 'low',     color: '#10b981' },
  { label: '20–45%',  key: 'guarded', color: '#84cc16' },
  { label: '45–75%',  key: 'medium',  color: '#f59e0b' },
  { label: '75–90%',  key: 'high',    color: '#ef4444' },
  { label: '90–100%', key: 'critical',color: '#dc2626' },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
      borderRadius: 'var(--radius-md)', padding: '10px 14px', fontSize: 12,
    }}>
      <div style={{ fontWeight: 700, marginBottom: 4, color: 'var(--text-primary)' }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color }} />
          {p.name}: <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  )
}

const PieTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
      borderRadius: 'var(--radius-md)', padding: '8px 12px', fontSize: 12,
    }}>
      <div style={{ color: payload[0].payload.fill, fontWeight: 700 }}>{payload[0].name}</div>
      <div style={{ color: 'var(--text-secondary)' }}>Count: <strong style={{ color: 'var(--text-primary)' }}>{payload[0].value}</strong></div>
    </div>
  )
}

export default function Analytics() {
  const [analytics, setAnalytics] = useState(null)
  const [claims,    setClaims]    = useState([])
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    Promise.all([getAnalytics(), listClaims({ page: 1, page_size: 100 })])
      .then(([a, c]) => { setAnalytics(a); setClaims(c.claims) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const byStatus = analytics?.by_status || []
  const total    = byStatus.reduce((s, r) => s + r.count, 0)

  // Terminal status breakdown for pie
  const terminal = ['APPROVED','REJECTED','INVESTIGATING','HITL_REVIEW','ERROR']
  const pieData  = byStatus
    .filter(r => terminal.includes(r.status))
    .map(r => ({ name: r.status, value: r.count, fill: STATUS_COLORS[r.status] || '#888' }))

  // All statuses for bar
  const barData = byStatus
    .sort((a, b) => b.count - a.count)
    .map(r => ({ name: r.status.replace(/_/g, ' '), count: r.count, fill: STATUS_COLORS[r.status] || '#888' }))

  // Fraud bucket distribution
  const fraudBucketData = FRAUD_BUCKETS.map(b => {
    const count = claims.filter(c => {
      if (c.fraud_score == null) return false
      const s = c.fraud_score
      if (b.key === 'low')      return s < 0.20
      if (b.key === 'guarded')  return s >= 0.20 && s < 0.45
      if (b.key === 'medium')   return s >= 0.45 && s < 0.75
      if (b.key === 'high')     return s >= 0.75 && s < 0.90
      if (b.key === 'critical') return s >= 0.90
      return false
    }).length
    return { ...b, count }
  })

  // Average fraud by policy type
  const policyTypes = [...new Set(claims.map(c => c.policy_type).filter(Boolean))]
  const fraudByType = policyTypes.map(pt => {
    const subset = claims.filter(c => c.policy_type === pt && c.fraud_score != null)
    const avg    = subset.length ? subset.reduce((s, c) => s + c.fraud_score, 0) / subset.length : 0
    return { name: pt, avg: parseFloat((avg * 100).toFixed(1)), count: subset.length }
  }).sort((a, b) => b.avg - a.avg)

  // KPI derivations
  const approved   = byStatus.find(r => r.status === 'APPROVED')?.count  || 0
  const rejected   = byStatus.find(r => r.status === 'REJECTED')?.count  || 0
  const hitl       = byStatus.find(r => r.status === 'HITL_REVIEW')?.count || 0
  const approvalRate = total > 0 ? ((approved / total) * 100).toFixed(1) : '—'
  const avgFraud   = claims.filter(c => c.fraud_score != null).length > 0
    ? (claims.filter(c => c.fraud_score != null).reduce((s,c) => s + c.fraud_score, 0) /
       claims.filter(c => c.fraud_score != null).length * 100).toFixed(1)
    : '—'

  if (loading) return (
    <div className="loading-overlay" style={{ height: '60vh' }}>
      <div className="spinner" /><span>Loading analytics…</span>
    </div>
  )

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Analytics</h1>
        <p className="page-subtitle">Claims processing intelligence and fraud risk overview</p>
      </div>

      <div className="page-content">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>

          {/* KPI ROW */}
          <div className="stat-grid" style={{ marginBottom: 24 }}>
            {[
              { label: 'Total Claims', value: total, color: 'var(--brand)' },
              { label: 'Approval Rate', value: `${approvalRate}%`, color: 'var(--approve)' },
              { label: 'Avg Fraud Score', value: `${avgFraud}%`, color: 'var(--investigate)' },
              { label: 'Pending HITL', value: hitl, color: 'var(--info)' },
            ].map(k => (
              <div key={k.label} className="stat-card">
                <div className="stat-value" style={{ color: k.color }}>{k.value}</div>
                <div className="stat-label">{k.label}</div>
              </div>
            ))}
          </div>

          {/* ROW 1: STATUS PIE + BAR */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: 16, marginBottom: 16 }}>

            {/* PIE */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">Decision Breakdown</span>
                <span className="text-sm text-muted">{total} total</span>
              </div>
              <div className="card-body">
                {pieData.length === 0 ? (
                  <div className="empty-state" style={{ padding: 32 }}>No terminal decisions yet</div>
                ) : (
                  <>
                    <ResponsiveContainer width="100%" height={220}>
                      <PieChart>
                        <Pie
                          data={pieData} cx="50%" cy="50%"
                          innerRadius={55} outerRadius={90}
                          paddingAngle={3} dataKey="value"
                        >
                          {pieData.map((e, i) => (
                            <Cell key={i} fill={e.fill} stroke="var(--bg-surface)" strokeWidth={2} />
                          ))}
                        </Pie>
                        <Tooltip content={<PieTooltip />} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 12px', justifyContent: 'center', marginTop: 4 }}>
                      {pieData.map(d => (
                        <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11 }}>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', background: d.fill }} />
                          <span style={{ color: 'var(--text-secondary)' }}>{d.name}</span>
                          <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{d.value}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* STATUS BAR */}
            <div className="card">
              <div className="card-header"><span className="card-title">Claims by Status</span></div>
              <div className="card-body">
                {barData.length === 0 ? (
                  <div className="empty-state" style={{ padding: 32 }}>No data yet</div>
                ) : (
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={barData} layout="vertical" margin={{ left: 8, right: 24, top: 0, bottom: 0 }}>
                      <XAxis type="number" hide />
                      <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                      <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                      <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={16}>
                        {barData.map((e, i) => (
                          <Cell key={i} fill={e.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </div>

          {/* ROW 2: FRAUD BUCKETS + FRAUD BY POLICY TYPE */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

            {/* Fraud Buckets */}
            <div className="card">
              <div className="card-header"><span className="card-title">Fraud Score Distribution</span></div>
              <div className="card-body">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={fraudBucketData} margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                    <Bar dataKey="count" name="Claims" radius={[4, 4, 0, 0]} maxBarSize={36}>
                      {fraudBucketData.map((e, i) => (
                        <Cell key={i} fill={e.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Fraud by Policy Type */}
            <div className="card">
              <div className="card-header"><span className="card-title">Avg Fraud Risk by Policy Type</span></div>
              <div className="card-body">
                {fraudByType.length === 0 ? (
                  <div className="empty-state" style={{ padding: 32 }}>Not enough data yet</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12, paddingTop: 4 }}>
                    {fraudByType.map(pt => {
                      const color = pt.avg >= 75 ? 'var(--risk-high)' : pt.avg >= 45 ? 'var(--risk-medium)' : 'var(--risk-low)'
                      return (
                        <div key={pt.name}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: 12 }}>
                            <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{pt.name}</span>
                            <span style={{ color, fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{pt.avg}%</span>
                          </div>
                          <div style={{ height: 5, background: 'var(--bg-elevated)', borderRadius: 3, overflow: 'hidden' }}>
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${pt.avg}%` }}
                              transition={{ duration: 0.6, ease: 'easeOut' }}
                              style={{ height: '100%', background: color, borderRadius: 3 }}
                            />
                          </div>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>
                            {pt.count} claim{pt.count !== 1 ? 's' : ''}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>

        </motion.div>
      </div>
    </div>
  )
}
