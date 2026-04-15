import { format, formatDistanceToNow, parseISO } from 'date-fns'

export const fmtDate = (iso) => {
  if (!iso) return '—'
  try { return format(parseISO(iso), 'dd MMM yyyy, HH:mm') } catch { return iso }
}

export const fmtDateShort = (iso) => {
  if (!iso) return '—'
  try { return format(parseISO(iso), 'dd MMM yyyy') } catch { return iso }
}

export const fmtRelative = (iso) => {
  if (!iso) return '—'
  try { return formatDistanceToNow(parseISO(iso), { addSuffix: true }) } catch { return iso }
}

export const fmtCurrency = (amount, currency = 'INR') => {
  if (amount == null) return '—'
  if (currency === 'INR') {
    return `₹${Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
  }
  const symbols = { USD: '$', GBP: '£', AED: 'AED ', SGD: 'S$' }
  return `${symbols[currency] || currency + ' '}${Number(amount).toLocaleString()}`
}

export const fmtPercent = (v) => {
  if (v == null) return '—'
  return `${(Number(v) * 100).toFixed(0)}%`
}

export const fraudLevelFromScore = (score) => {
  if (score == null) return 'unknown'
  if (score >= 0.90) return 'critical'
  if (score >= 0.75) return 'high'
  if (score >= 0.45) return 'medium'
  return 'low'
}

export const statusConfig = {
  RECEIVED:         { label: 'Received',        cls: 'badge-processing', dot: 'var(--brand)' },
  OCR_PROCESSING:   { label: 'OCR',             cls: 'badge-processing', dot: 'var(--brand)' },
  EXTRACTING:       { label: 'Extracting',      cls: 'badge-processing', dot: 'var(--brand)' },
  VALIDATING:       { label: 'Validating',      cls: 'badge-processing', dot: 'var(--brand)' },
  POLICY_CHECK:     { label: 'Policy Check',    cls: 'badge-processing', dot: 'var(--brand)' },
  FRAUD_ANALYSIS:   { label: 'Fraud Analysis',  cls: 'badge-processing', dot: 'var(--brand)' },
  DECISION_PENDING: { label: 'Deciding',        cls: 'badge-pending',    dot: 'var(--pending)' },
  HITL_REVIEW:      { label: 'HITL Review',     cls: 'badge-hitl',       dot: 'var(--info)' },
  APPROVED:         { label: 'Approved',        cls: 'badge-approve',    dot: 'var(--approve)' },
  REJECTED:         { label: 'Rejected',        cls: 'badge-reject',     dot: 'var(--reject)' },
  INVESTIGATING:    { label: 'Investigating',   cls: 'badge-investigate', dot: 'var(--investigate)' },
  ERROR:            { label: 'Error',           cls: 'badge-error',       dot: 'var(--risk-critical)' },
}

export const decisionConfig = {
  APPROVE:     { label: 'Approved',      cls: 'approve',      color: 'var(--approve)' },
  REJECT:      { label: 'Rejected',      cls: 'reject',       color: 'var(--reject)' },
  INVESTIGATE: { label: 'Investigating', cls: 'investigate',  color: 'var(--investigate)' },
  PENDING:     { label: 'Pending',       cls: 'pending',      color: 'var(--pending)' },
}

export const PIPELINE_STEPS = [
  { key: 'RECEIVED',         label: 'Received' },
  { key: 'OCR_PROCESSING',   label: 'OCR' },
  { key: 'EXTRACTING',       label: 'Extract' },
  { key: 'VALIDATING',       label: 'Validate' },
  { key: 'POLICY_CHECK',     label: 'Policy' },
  { key: 'FRAUD_ANALYSIS',   label: 'Fraud' },
  { key: 'DECISION_PENDING', label: 'Decision' },
  { key: 'APPROVED',         label: 'Done' },
]

const STATUS_ORDER = PIPELINE_STEPS.map(s => s.key)
export const statusToStepIndex = (status) => {
  const terminalMap = { REJECTED: 7, INVESTIGATING: 7, HITL_REVIEW: 6, ERROR: 2 }
  if (terminalMap[status] !== undefined) return terminalMap[status]
  return STATUS_ORDER.indexOf(status)
}
