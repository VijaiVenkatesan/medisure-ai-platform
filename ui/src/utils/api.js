import axios from 'axios'

// ─── API URL RESOLUTION ───────────────────────────────────────────
// Priority:
//   1. VITE_API_URL env var (set in Netlify dashboard or .env.production)
//   2. Auto-detect: if running on localhost → use local backend
//   3. Production fallback → Render URL
const getBaseUrl = () => {
  // Explicit override always wins (Netlify env var, .env.production)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  // Local development — frontend on localhost → backend on localhost
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000/api/v1'
  }
  // Production (Netlify, any other host) → always use Render
  return 'https://medisure-api.onrender.com/api/v1'
}

const BASE_URL = getBaseUrl()

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,   // 60s — Render free tier can take 30s to wake from sleep
  headers: { 'Content-Type': 'application/json' },
})

// Response interceptor — extract readable error messages
api.interceptors.response.use(
  r => r,
  err => {
    const msg = err.response?.data?.detail || err.message || 'Request failed'
    // Surface Render sleep wake-up clearly
    if (err.code === 'ECONNABORTED' || msg.includes('timeout')) {
      return Promise.reject(new Error('API is waking up (Render free tier). Please try again in 30 seconds.'))
    }
    return Promise.reject(new Error(msg))
  }
)

// ─── CLAIMS ───────────────────────────────
export const submitClaim = (formData) =>
  api.post('/claims/submit', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)

export const getClaim = (claimId) =>
  api.get(`/claims/${claimId}`).then(r => r.data)

export const listClaims = (params = {}) =>
  api.get('/claims', { params }).then(r => r.data)

export const getAuditTrail = (claimId) =>
  api.get(`/claims/${claimId}/audit`).then(r => r.data)

// ─── HITL ─────────────────────────────────
export const getPendingHITL = () =>
  api.get('/hitl/pending').then(r => r.data)

export const submitHITLReview = (claimId, payload) =>
  api.post(`/hitl/${claimId}/review`, payload).then(r => r.data)

// ─── POLICIES ─────────────────────────────
export const indexPolicy = (payload) =>
  api.post('/policies/index', payload).then(r => r.data)

// ─── ANALYTICS ────────────────────────────
export const getAnalytics = () =>
  api.get('/analytics/summary').then(r => r.data)

// ─── HEALTH ───────────────────────────────
export const getHealth = () =>
  api.get('/health').then(r => r.data)

export default api

// ─── ADMIN ────────────────────────────────
export const adminListClaims = (params = {}) =>
  api.get('/admin/claims', { params }).then(r => r.data)

export const adminUpdateClaim = (claimId, data) =>
  api.patch(`/admin/claims/${claimId}`, data).then(r => r.data)

export const adminDeleteClaim = (claimId) =>
  api.delete(`/admin/claims/${claimId}`).then(r => r.data)

export const adminReprocessClaim = (claimId) =>
  api.post(`/admin/claims/${claimId}/reprocess`).then(r => r.data)

export const adminGetLogs = (params = {}) =>
  api.get('/admin/logs', { params }).then(r => r.data)

export const adminGetStats = () =>
  api.get('/admin/stats').then(r => r.data)

// ─── MEDICAL AI ───────────────────────────
export const medicalSummarize = (formData) =>
  api.post('/medical/summarize', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data)

export const medicalCode = (payload) =>
  api.post('/medical/code', payload).then(r => r.data)

export const medicalCodeDocument = (formData) =>
  api.post('/medical/code-document', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data)

export const medicalTranscribe = (payload) =>
  api.post('/medical/transcribe', payload).then(r => r.data)

export const medicalTranscribeAudio = (formData) =>
  api.post('/medical/transcribe-audio', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data)

// ─── AUTH ─────────────────────────────────
export const authLogin = (username, password) =>
  api.post('/auth/login', { username, password }).then(r => r.data)

export const authMe = () =>
  api.get('/auth/me').then(r => r.data)

export const authListUsers = () =>
  api.get('/auth/users').then(r => r.data)

export const authCreateUser = (payload) =>
  api.post('/auth/users', payload).then(r => r.data)

export const authDeleteUser = (username) =>
  api.delete(`/auth/users/${username}`).then(r => r.data)

// ─── ENTERPRISE / PHASE 3 & 4 ─────────────────────────────────────
export const underwritingAssess = (payload) =>
  api.post('/underwriting/assess', payload).then(r => r.data)

export const clinicalDiagnose = (payload) =>
  api.post('/clinical/diagnose', payload).then(r => r.data)

export const clinicalDrugInteractions = (payload) =>
  api.post('/clinical/drug-interactions', payload).then(r => r.data)

export const clinicalRiskStratify = (payload) =>
  api.post('/clinical/risk-stratify', payload).then(r => r.data)
