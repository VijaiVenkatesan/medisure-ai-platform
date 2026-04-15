import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Stethoscope, FileText, Code, Mic, Upload,
  ChevronDown, ChevronUp, CheckCircle, AlertCircle,
  Copy, Loader
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  medicalSummarize, medicalCode, medicalCodeDocument,
  medicalTranscribe, medicalTranscribeAudio
} from '../utils/api'

const TABS = [
  { id: 'summarize',    icon: <FileText size={15} />,    label: 'Summarize Document' },
  { id: 'code',         icon: <Code size={15} />,        label: 'ICD-10 Coding' },
  { id: 'transcribe',   icon: <Mic size={15} />,         label: 'Transcription' },
]

// ── SHARED: FILE DROPZONE ────────────────────────────────────────────
function FileDropzone({ onFile, accept, label, sub }) {
  const [file, setFile] = useState(null)
  const onDrop = useCallback(accepted => {
    if (accepted[0]) { setFile(accepted[0]); onFile(accepted[0]) }
  }, [onFile])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept, maxFiles: 1
  })
  return (
    <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}
      style={{ padding: 32, marginBottom: 16 }}>
      <input {...getInputProps()} />
      <div className="dropzone-icon" style={{ width: 48, height: 48 }}>
        <Upload size={20} color={file ? 'var(--brand)' : 'var(--text-muted)'} />
      </div>
      {file
        ? <div className="dropzone-title" style={{ color: 'var(--brand)' }}>{file.name}</div>
        : <>
            <div className="dropzone-title">{label}</div>
            <div className="dropzone-sub">{sub}</div>
          </>}
    </div>
  )
}

// ── RESULT CARD ──────────────────────────────────────────────────────
function ResultSection({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card mb-16">
      <button className="card-header" style={{
        width: '100%', background: 'none', border: 'none',
        cursor: 'pointer', color: 'inherit', textAlign: 'left'
      }} onClick={() => setOpen(o => !o)}>
        <span className="card-title">{title}</span>
        {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} style={{ overflow: 'hidden' }}>
            <div className="card-body">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function CopyBtn({ text }) {
  return (
    <button className="btn btn-secondary btn-sm btn-icon" title="Copy"
      onClick={() => { navigator.clipboard.writeText(text); toast.success('Copied!') }}>
      <Copy size={13} />
    </button>
  )
}

function Field({ label, value }) {
  if (!value) return null
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: 8,
      padding: '7px 0', borderBottom: '1px solid var(--border-subtle)' }}>
      <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>{label}</span>
      <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{value}</span>
    </div>
  )
}

// ── SUMMARIZE TAB ────────────────────────────────────────────────────
function SummarizeTab() {
  const [file,    setFile]    = useState(null)
  const [docType, setDocType] = useState('auto')
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)

  const handleSubmit = async () => {
    if (!file) { toast.error('Select a document first'); return }
    setLoading(true); setResult(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('doc_type', docType)
      const r = await medicalSummarize(fd)
      setResult(r)
    } catch (e) { toast.error(e.message) }
    finally { setLoading(false) }
  }

  return (
    <div>
      <FileDropzone onFile={setFile}
        accept={{ 'application/pdf': ['.pdf'], 'image/*': ['.png','.jpg','.jpeg','.tiff'] }}
        label="Upload medical document" sub="Discharge summary, OPD note, lab report, prescription" />

      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <select className="form-select" value={docType}
          onChange={e => setDocType(e.target.value)} style={{ flex: 1 }}>
          <option value="auto">Auto-detect type</option>
          <option value="DISCHARGE_SUMMARY">Discharge Summary</option>
          <option value="OPD_NOTE">OPD / Consultation Note</option>
          <option value="LAB_REPORT">Lab Report</option>
          <option value="PRESCRIPTION">Prescription</option>
          <option value="RADIOLOGY">Radiology Report</option>
        </select>
        <button className="btn btn-primary" onClick={handleSubmit}
          disabled={!file || loading} style={{ minWidth: 140 }}>
          {loading
            ? <><Loader size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> Analyzing…</>
            : <><Stethoscope size={14} /> Summarize</>}
        </button>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="spinner" style={{ margin: '0 auto 12px' }} />
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            Extracting text and analyzing with Groq AI…
          </div>
        </div>
      )}

      {result && !result.error && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          {/* Summary paragraph */}
          {result.summary_paragraph && (
            <div style={{
              background: 'var(--brand-dim)', border: '1px solid var(--brand-glow)',
              borderRadius: 'var(--radius-lg)', padding: '14px 18px', marginBottom: 16
            }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--brand)',
                textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                AI Summary
              </div>
              <p style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.7 }}>
                {result.summary_paragraph}
              </p>
            </div>
          )}

          {/* Red flags */}
          {result.red_flags?.length > 0 && (
            <div style={{
              background: 'var(--reject-dim)', border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 'var(--radius-lg)', padding: '12px 16px', marginBottom: 16
            }}>
              <div style={{ fontWeight: 700, color: 'var(--reject)', fontSize: 13, marginBottom: 8 }}>
                ⚠ Red Flags / Urgent Findings
              </div>
              {result.red_flags.map((f, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--reject)', marginBottom: 3 }}>• {f}</div>
              ))}
            </div>
          )}

          <ResultSection title="Patient & Facility">
            <Field label="Patient Name" value={result.patient?.name} />
            <Field label="Age / Gender" value={[result.patient?.age, result.patient?.gender].filter(Boolean).join(' / ')} />
            <Field label="ABHA Number" value={result.patient?.abha_number} />
            <Field label="Hospital" value={result.facility?.hospital_name} />
            <Field label="Doctor" value={result.facility?.doctor_name} />
            <Field label="Department" value={result.facility?.department} />
            <Field label="Date" value={result.facility?.date} />
          </ResultSection>

          <ResultSection title={`Diagnoses (${result.diagnoses?.length || 0})`}>
            {result.diagnoses?.map((d, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0',
                borderBottom: '1px solid var(--border-subtle)'
              }}>
                <span style={{
                  background: d.type === 'PRIMARY' ? 'var(--brand-dim)' : 'var(--bg-elevated)',
                  color: d.type === 'PRIMARY' ? 'var(--brand)' : 'var(--text-secondary)',
                  padding: '2px 8px', borderRadius: 12, fontSize: 10, fontWeight: 700, whiteSpace: 'nowrap'
                }}>{d.type}</span>
                <span style={{ flex: 1, fontSize: 13 }}>{d.description}</span>
                {d.icd10_code && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12,
                    color: 'var(--brand)', background: 'var(--brand-dim)',
                    padding: '2px 8px', borderRadius: 6 }}>{d.icd10_code}</span>
                )}
              </div>
            ))}
          </ResultSection>

          {result.medications?.length > 0 && (
            <ResultSection title={`Medications (${result.medications.length})`}>
              <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                    {['Drug', 'Dose', 'Frequency', 'Duration', 'Route'].map(h => (
                      <th key={h} style={{ padding: '6px 8px', textAlign: 'left',
                        fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.medications.map((m, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '6px 8px', fontWeight: 600 }}>{m.drug}</td>
                      <td style={{ padding: '6px 8px', color: 'var(--text-secondary)' }}>{m.dose}</td>
                      <td style={{ padding: '6px 8px', color: 'var(--text-secondary)' }}>{m.frequency}</td>
                      <td style={{ padding: '6px 8px', color: 'var(--text-secondary)' }}>{m.duration}</td>
                      <td style={{ padding: '6px 8px', color: 'var(--text-secondary)' }}>{m.route}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ResultSection>
          )}

          {result.lab_results?.length > 0 && (
            <ResultSection title={`Lab Results (${result.lab_results.length})`}>
              <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                    {['Test', 'Result', 'Unit', 'Flag'].map(h => (
                      <th key={h} style={{ padding: '6px 8px', textAlign: 'left',
                        fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.lab_results.map((l, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '6px 8px', fontWeight: 600 }}>{l.test}</td>
                      <td style={{ padding: '6px 8px' }}>{l.value}</td>
                      <td style={{ padding: '6px 8px', color: 'var(--text-muted)' }}>{l.unit}</td>
                      <td style={{ padding: '6px 8px' }}>
                        {l.flag && (
                          <span style={{
                            color: l.flag === 'HIGH' || l.flag === 'LOW' ? 'var(--reject)' : 'var(--approve)',
                            fontWeight: 700, fontSize: 11
                          }}>{l.flag}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ResultSection>
          )}

          <ResultSection title="Follow-up & Notes" defaultOpen={false}>
            <Field label="Follow-up" value={result.follow_up} />
            <Field label="Treatment" value={result.treatment_summary} />
            <Field label="OCR Engine" value={result.ocr_engine} />
            <Field label="Confidence" value={result.confidence ? `${(result.confidence * 100).toFixed(0)}%` : null} />
          </ResultSection>
        </motion.div>
      )}

      {result?.error && (
        <div style={{ background: 'var(--reject-dim)', borderRadius: 'var(--radius-lg)',
          padding: 16, color: 'var(--reject)', fontSize: 13 }}>
          <AlertCircle size={16} style={{ marginRight: 8 }} />{result.error}
        </div>
      )}
    </div>
  )
}

// ── CODING TAB ───────────────────────────────────────────────────────
function CodingTab() {
  const [mode,    setMode]    = useState('text')  // text | file
  const [text,    setText]    = useState('')
  const [file,    setFile]    = useState(null)
  const [country, setCountry] = useState('IN')
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)

  const handleSubmit = async () => {
    if (mode === 'text' && !text.trim()) { toast.error('Enter clinical text'); return }
    if (mode === 'file' && !file)        { toast.error('Select a file'); return }
    setLoading(true); setResult(null)
    try {
      let r
      if (mode === 'text') {
        r = await medicalCode({ clinical_text: text, country, include_cpt: country === 'US' })
      } else {
        const fd = new FormData()
        fd.append('file', file)
        fd.append('country', country)
        r = await medicalCodeDocument(fd)
      }
      setResult(r)
    } catch (e) { toast.error(e.message) }
    finally { setLoading(false) }
  }

  return (
    <div>
      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {[['text','Type/Paste Text'], ['file','Upload Document']].map(([m, l]) => (
          <button key={m} className={`btn ${mode === m ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setMode(m)} style={{ flex: 1 }}>{l}</button>
        ))}
      </div>

      {mode === 'text' ? (
        <textarea className="form-textarea" rows={6}
          placeholder="Paste clinical documentation, discharge summary, or doctor's notes here…"
          value={text} onChange={e => setText(e.target.value)}
          style={{ marginBottom: 12, fontFamily: 'var(--font-mono)', fontSize: 12 }} />
      ) : (
        <FileDropzone onFile={setFile}
          accept={{ 'application/pdf': ['.pdf'], 'image/*': ['.png','.jpg','.jpeg'] }}
          label="Upload clinical document" sub="PDF, PNG, JPG — scanned docs supported" />
      )}

      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <select className="form-select" value={country}
          onChange={e => setCountry(e.target.value)} style={{ flex: 1 }}>
          <option value="IN">🇮🇳 India (ABDM ICD-10)</option>
          <option value="US">🇺🇸 USA (ICD-10-CM + CPT)</option>
          <option value="GB">🇬🇧 UK (NHS ICD-10)</option>
          <option value="AE">🇦🇪 UAE (MOH ICD-10)</option>
          <option value="SG">🇸🇬 Singapore</option>
        </select>
        <button className="btn btn-primary" onClick={handleSubmit}
          disabled={loading} style={{ minWidth: 140 }}>
          {loading
            ? <><Loader size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> Coding…</>
            : <><Code size={14} /> Assign Codes</>}
        </button>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="spinner" style={{ margin: '0 auto 12px' }} />
          <div className="text-secondary" style={{ fontSize: 13 }}>
            Analyzing clinical text and assigning ICD-10 codes…
          </div>
        </div>
      )}

      {result && !result.error && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          {/* Primary diagnosis */}
          {result.primary_diagnosis && (
            <div style={{
              background: 'var(--brand-dim)', border: '1px solid var(--brand-glow)',
              borderRadius: 'var(--radius-lg)', padding: 16, marginBottom: 16
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--brand)',
                  textTransform: 'uppercase', letterSpacing: '0.06em' }}>Primary Diagnosis</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 800,
                  color: 'var(--brand)' }}>{result.primary_diagnosis.icd10_code}</div>
                <div style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>
                  {result.primary_diagnosis.confidence ? 
                    `${(result.primary_diagnosis.confidence * 100).toFixed(0)}% confident` : ''}
                </div>
                <CopyBtn text={result.primary_diagnosis.icd10_code} />
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
                {result.primary_diagnosis.description}
              </div>
              <div style={{ fontSize: 12, color: 'var(--brand)', fontStyle: 'italic' }}>
                {result.primary_diagnosis.icd10_description}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6 }}>
                {result.primary_diagnosis.specificity}
              </div>
            </div>
          )}

          {/* Secondary diagnoses */}
          {result.secondary_diagnoses?.length > 0 && (
            <ResultSection title="Secondary Diagnoses">
              {result.secondary_diagnoses.map((d, i) => (
                <div key={i} style={{ display: 'flex', gap: 12, padding: '8px 0',
                  borderBottom: '1px solid var(--border-subtle)', alignItems: 'center' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700,
                    color: 'var(--text-primary)', minWidth: 80 }}>{d.icd10_code}</span>
                  <span style={{ flex: 1, fontSize: 13 }}>{d.description}</span>
                  <CopyBtn text={d.icd10_code} />
                </div>
              ))}
            </ResultSection>
          )}

          {/* Procedures */}
          {result.procedures?.length > 0 && (
            <ResultSection title="Procedures">
              {result.procedures.map((p, i) => (
                <div key={i} style={{ display: 'flex', gap: 12, padding: '8px 0',
                  borderBottom: '1px solid var(--border-subtle)', alignItems: 'center' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13 }}>{p.description}</div>
                    <div className="flex gap-8 mt-12" style={{ marginTop: 4 }}>
                      {p.cpt_code && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11,
                        color: 'var(--info)' }}>CPT: {p.cpt_code}</span>}
                      {p.icd10_pcs && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11,
                        color: 'var(--approve)' }}>PCS: {p.icd10_pcs}</span>}
                    </div>
                  </div>
                </div>
              ))}
            </ResultSection>
          )}

          {/* Notes */}
          {(result.coding_notes || result.query_flags?.length > 0) && (
            <ResultSection title="Coding Notes" defaultOpen={false}>
              {result.coding_notes && (
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>
                  {result.coding_notes}
                </p>
              )}
              {result.query_flags?.map((f, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--investigate)',
                  padding: '4px 0' }}>⚠ {f}</div>
              ))}
            </ResultSection>
          )}
        </motion.div>
      )}
    </div>
  )
}

// ── TRANSCRIPTION TAB ────────────────────────────────────────────────
function TranscribeTab() {
  const [mode,    setMode]    = useState('text')
  const [text,    setText]    = useState('')
  const [file,    setFile]    = useState(null)
  const [lang,    setLang]    = useState('en')
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)

  const handleSubmit = async () => {
    setLoading(true); setResult(null)
    try {
      let r
      if (mode === 'text') {
        if (!text.trim()) { toast.error('Enter dictation text'); return }
        r = await medicalTranscribe({ text, language: lang })
      } else {
        if (!file) { toast.error('Select audio file'); return }
        const fd = new FormData()
        fd.append('file', file)
        fd.append('language', lang)
        r = await medicalTranscribeAudio(fd)
      }
      setResult(r)
    } catch (e) { toast.error(e.message) }
    finally { setLoading(false) }
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {[['text','Type/Paste Dictation'], ['audio','Upload Audio File']].map(([m, l]) => (
          <button key={m} className={`btn ${mode === m ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setMode(m)} style={{ flex: 1 }}>{l}</button>
        ))}
      </div>

      {mode === 'text' ? (
        <textarea className="form-textarea" rows={6}
          placeholder="Paste medical dictation, voice note transcript, or doctor's notes here…"
          value={text} onChange={e => setText(e.target.value)}
          style={{ marginBottom: 12, fontFamily: 'var(--font-mono)', fontSize: 12 }} />
      ) : (
        <>
          <FileDropzone onFile={setFile}
            accept={{ 'audio/*': ['.mp3','.wav','.m4a','.ogg','.flac'] }}
            label="Upload audio dictation" sub="MP3, WAV, M4A, OGG — max 25MB · Groq Whisper" />
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
            Supports Hindi, Tamil, Telugu, Kannada, Bengali, Malayalam, and 90+ languages
          </div>
        </>
      )}

      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <select className="form-select" value={lang}
          onChange={e => setLang(e.target.value)} style={{ flex: 1 }}>
          <option value="en">English</option>
          <option value="hi">Hindi (हिंदी)</option>
          <option value="ta">Tamil (தமிழ்)</option>
          <option value="te">Telugu (తెలుగు)</option>
          <option value="kn">Kannada (ಕನ್ನಡ)</option>
          <option value="ml">Malayalam (മലയാളം)</option>
          <option value="bn">Bengali (বাংলা)</option>
          <option value="mr">Marathi (मराठी)</option>
        </select>
        <button className="btn btn-primary" onClick={handleSubmit}
          disabled={loading} style={{ minWidth: 160 }}>
          {loading
            ? <><Loader size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> Structuring…</>
            : <><Mic size={14} /> Structure as SOAP</>}
        </button>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="spinner" style={{ margin: '0 auto 12px' }} />
          <div className="text-secondary" style={{ fontSize: 13 }}>
            {mode === 'audio' ? 'Transcribing with Groq Whisper…' : 'Structuring SOAP note with AI…'}
          </div>
        </div>
      )}

      {result?.soap_note && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          {['subjective', 'objective', 'assessment', 'plan'].map(section => {
            const data = result.soap_note[section]
            if (!data) return null
            return (
              <ResultSection key={section}
                title={`${section.toUpperCase().charAt(0)} — ${section.charAt(0).toUpperCase() + section.slice(1)}`}>
                {typeof data === 'string' ? (
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{data}</p>
                ) : (
                  Object.entries(data).map(([k, v]) => {
                    if (!v || (Array.isArray(v) && !v.length)) return null
                    return (
                      <div key={k} style={{ marginBottom: 10 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)',
                          textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                          {k.replace(/_/g, ' ')}
                        </div>
                        {Array.isArray(v)
                          ? v.map((item, i) => (
                              <div key={i} style={{ fontSize: 13, color: 'var(--text-secondary)',
                                paddingLeft: 12, marginBottom: 2 }}>
                                {typeof item === 'object' ? JSON.stringify(item) : `• ${item}`}
                              </div>
                            ))
                          : typeof v === 'object'
                          ? Object.entries(v).map(([k2, v2]) => v2
                              ? <div key={k2} style={{ fontSize: 13, color: 'var(--text-secondary)',
                                  paddingLeft: 12 }}>{k2}: {v2}</div>
                              : null)
                          : <div style={{ fontSize: 13, color: 'var(--text-secondary)',
                              paddingLeft: 12 }}>{v}</div>}
                      </div>
                    )
                  })
                )}
              </ResultSection>
            )
          })}
        </motion.div>
      )}
    </div>
  )
}

// ── MAIN PAGE ─────────────────────────────────────────────────────────
export default function MedicalAI() {
  const [tab, setTab] = useState(0)

  return (
    <div>
      <div className="page-header">
        <div style={{ paddingBottom: 0 }}>
          <div className="flex gap-8" style={{ marginBottom: 6, alignItems: 'center' }}>
            <Stethoscope size={18} color="var(--brand)" />
            <h1 className="page-title" style={{ margin: 0 }}>Medical AI</h1>
            <span style={{ fontSize: 11, background: 'var(--brand-dim)', color: 'var(--brand)',
              padding: '2px 8px', borderRadius: 12, fontWeight: 700 }}>Phase 2</span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
            AI-powered medical document summarization, ICD-10 coding, and clinical transcription
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

      <div className="page-content" style={{ maxWidth: 900 }}>
        <AnimatePresence mode="wait">
          <motion.div key={tab}
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
            {tab === 0 && <SummarizeTab />}
            {tab === 1 && <CodingTab />}
            {tab === 2 && <TranscribeTab />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
