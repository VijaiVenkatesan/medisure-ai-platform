import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, FileText, CheckCircle, Loader, AlertCircle, ArrowRight, X } from 'lucide-react'
import toast from 'react-hot-toast'
import { submitClaim, getClaim } from '../utils/api'
import { statusConfig, PIPELINE_STEPS, statusToStepIndex } from '../utils/helpers'

const ACCEPTED = { 'application/pdf': ['.pdf'], 'image/png': ['.png'], 'image/jpeg': ['.jpg','.jpeg'], 'image/tiff': ['.tiff','.tif'] }
const MAX_SIZE = 10 * 1024 * 1024 // 10MB

export default function Submit() {
  const navigate = useNavigate()
  const [file,      setFile]      = useState(null)
  const [stage,     setStage]     = useState('idle') // idle | uploading | processing | done | error
  const [claimId,   setClaimId]   = useState(null)
  const [status,    setStatus]    = useState(null)
  const [pollCount, setPollCount] = useState(0)
  const [error,     setError]     = useState(null)

  const onDrop = useCallback((accepted, rejected) => {
    if (rejected.length > 0) {
      const err = rejected[0].errors[0]
      toast.error(err.code === 'file-too-large' ? 'File exceeds 10MB limit' : 'Invalid file type. Use PDF, PNG, JPG, or TIFF.')
      return
    }
    if (accepted.length > 0) {
      setFile(accepted[0])
      setStage('idle')
      setError(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: ACCEPTED, maxSize: MAX_SIZE, maxFiles: 1,
  })

  const handleSubmit = async () => {
    if (!file) return
    setStage('uploading')
    setError(null)

    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await submitClaim(fd)
      setClaimId(res.claim_id)
      setStage('processing')
      toast.success(`Claim ${res.claim_id} submitted`)
      pollStatus(res.claim_id)
    } catch (e) {
      setStage('error')
      setError(e.message)
      toast.error(e.message)
    }
  }

  const pollStatus = (id) => {
    let count = 0
    const interval = setInterval(async () => {
      count++
      setPollCount(count)
      try {
        const data = await getClaim(id)
        setStatus(data.status)
        const terminal = ['APPROVED','REJECTED','INVESTIGATING','HITL_REVIEW','ERROR']
        if (terminal.includes(data.status)) {
          clearInterval(interval)
          setStage('done')
        }
        if (count > 60) { clearInterval(interval); setStage('done') }
      } catch {
        clearInterval(interval)
      }
    }, 3000)
  }

  const reset = () => {
    setFile(null); setStage('idle'); setClaimId(null)
    setStatus(null); setPollCount(0); setError(null)
  }

  const stepIdx = status ? statusToStepIndex(status) : -1

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Submit Claim</h1>
        <p className="page-subtitle">Upload an insurance claim document for AI processing</p>
      </div>

      <div className="page-content" style={{ maxWidth: 680, margin: '0 auto' }}>
        <AnimatePresence mode="wait">

          {/* ── IDLE / SELECT FILE ── */}
          {stage === 'idle' && (
            <motion.div key="idle" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
                <input {...getInputProps()} />
                <div className="dropzone-icon">
                  {file ? <FileText size={28} color="var(--brand)" /> : <Upload size={28} color="var(--text-muted)" />}
                </div>
                {file ? (
                  <>
                    <div className="dropzone-title" style={{ color: 'var(--brand)' }}>{file.name}</div>
                    <div className="dropzone-sub">{(file.size / 1024).toFixed(0)} KB — click to replace</div>
                  </>
                ) : (
                  <>
                    <div className="dropzone-title">
                      {isDragActive ? 'Drop the file here' : 'Drag & drop your claim document'}
                    </div>
                    <div className="dropzone-sub">or click to browse files</div>
                    <div className="dropzone-types">PDF · PNG · JPG · TIFF — max 10 MB</div>
                  </>
                )}
              </div>

              {file && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-16">
                  <div className="card">
                    <div className="card-body">
                      <div className="flex-between">
                        <div>
                          <div className="font-semibold" style={{ marginBottom: 4 }}>Ready to process</div>
                          <div className="text-sm text-secondary">
                            Your document will be processed through 5 AI agents in sequence.
                          </div>
                        </div>
                        <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); setFile(null) }}>
                          <X size={13} />
                        </button>
                      </div>
                      <div className="divider" />
                      <div className="flex gap-8" style={{ flexWrap: 'wrap', marginBottom: 16 }}>
                        {['OCR Extraction', 'Data Validation', 'Policy Check (RAG)', 'Fraud Analysis', 'Decision Engine'].map(s => (
                          <span key={s} className="badge badge-processing">{s}</span>
                        ))}
                      </div>
                      <button className="btn btn-primary w-full" onClick={handleSubmit}>
                        <Upload size={15} /> Submit for Processing
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}
            </motion.div>
          )}

          {/* ── UPLOADING ── */}
          {stage === 'uploading' && (
            <motion.div key="uploading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card">
              <div className="loading-overlay">
                <div className="spinner" />
                <div className="font-semibold">Uploading document…</div>
                <div className="text-sm text-secondary">Sending {file?.name}</div>
              </div>
            </motion.div>
          )}

          {/* ── PROCESSING ── */}
          {stage === 'processing' && (
            <motion.div key="processing" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">Processing Claim</div>
                  <div className="text-xs text-muted mt-12" style={{ marginTop: 4 }}>
                    <span className="font-mono">{claimId}</span>
                  </div>
                </div>
                <div className="flex gap-8">
                  <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                  <span className="text-sm text-secondary">Poll #{pollCount}</span>
                </div>
              </div>
              <div className="card-body">
                {/* Pipeline */}
                <div className="pipeline">
                  {PIPELINE_STEPS.map((step, i) => {
                    const state = i < stepIdx ? 'completed' : i === stepIdx ? 'active' : 'idle'
                    return (
                      <div key={step.key} className={`pipeline-step ${state}`}>
                        <div className="step-circle">
                          {state === 'completed' ? '✓' : i + 1}
                        </div>
                        <div className="step-label">{step.label}</div>
                      </div>
                    )
                  })}
                </div>
                <div className="text-sm text-secondary" style={{ textAlign: 'center', marginTop: 12 }}>
                  Current stage: <strong style={{ color: 'var(--brand)' }}>{status || 'Starting…'}</strong>
                </div>
              </div>
            </motion.div>
          )}

          {/* ── DONE ── */}
          {stage === 'done' && (
            <motion.div key="done" initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} className="card">
              <div className="card-body" style={{ textAlign: 'center', padding: '40px 24px' }}>
                {status === 'APPROVED' ? (
                  <CheckCircle size={48} color="var(--approve)" style={{ margin: '0 auto 16px' }} />
                ) : status === 'REJECTED' ? (
                  <XCircle size={48} color="var(--reject)" style={{ margin: '0 auto 16px' }} />
                ) : (
                  <AlertCircle size={48} color="var(--investigate)" style={{ margin: '0 auto 16px' }} />
                )}
                <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
                  Processing Complete
                </div>
                <div className="text-secondary text-sm" style={{ marginBottom: 24 }}>
                  Claim <span className="font-mono">{claimId}</span> — Final status:{' '}
                  <strong style={{ color: statusConfig[status]?.dot }}>{status}</strong>
                </div>
                <div className="flex gap-12" style={{ justifyContent: 'center' }}>
                  <button className="btn btn-primary" onClick={() => navigate(`/claims/${claimId}`)}>
                    View Details <ArrowRight size={14} />
                  </button>
                  <button className="btn btn-secondary" onClick={reset}>
                    Submit Another
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {/* ── ERROR ── */}
          {stage === 'error' && (
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card">
              <div className="card-body" style={{ textAlign: 'center', padding: '40px 24px' }}>
                <AlertCircle size={40} color="var(--reject)" style={{ margin: '0 auto 14px' }} />
                <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Submission Failed</div>
                <div className="text-secondary text-sm" style={{ marginBottom: 24 }}>{error}</div>
                <button className="btn btn-secondary" onClick={reset}>Try Again</button>
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  )
}
