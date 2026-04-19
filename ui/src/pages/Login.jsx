import { useState } from 'react'
import { motion } from 'framer-motion'
import { Eye, EyeOff, LogIn, AlertCircle, Shield, User, Stethoscope } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import toast from 'react-hot-toast'

const DEMO_ACCOUNTS = [
  {
    role: 'ADMIN',
    username: 'admin',
    password: import.meta.env.VITE_DEMO_ADMIN_PW || 'Admin@MediSure#2026',
    icon: <Shield size={14} />,
    color: 'var(--brand)',
    desc: 'Full system access, admin panel, user management',
  },
  {
    role: 'REVIEWER',
    username: 'reviewer',
    password: import.meta.env.VITE_DEMO_REVIEWER_PW || 'Reviewer@MediSure#2026',
    icon: <User size={14} />,
    color: 'var(--info)',
    desc: 'HITL review, claim processing, read-only admin',
  },
  {
    role: 'USER',
    username: 'user',
    password: import.meta.env.VITE_DEMO_USER_PW || 'User@MediSure#2026',
    icon: <Stethoscope size={14} />,
    color: 'var(--approve)',
    desc: 'Submit claims, view own claims, medical AI tools',
  },
]

export default function LoginPage() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw,   setShowPw]   = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')

  const handleLogin = async (e) => {
    e?.preventDefault()
    if (!username.trim() || !password.trim()) {
      setError('Please enter username and password')
      return
    }
    setLoading(true)
    setError('')
    try {
      const data = await login(username, password)
      toast.success(`Welcome, ${data.full_name || data.username}!`)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const fillDemo = (acc) => {
    setUsername(acc.username)
    setPassword(acc.password)
    setError('')
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-base)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 20,
      backgroundImage:
        'radial-gradient(circle at 30% 20%, rgba(0,201,167,0.06) 0%, transparent 50%), ' +
        'radial-gradient(circle at 70% 80%, rgba(59,130,246,0.06) 0%, transparent 50%)',
    }}>
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        style={{ width: '100%', maxWidth: 440 }}
      >
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            width: 56, height: 56,
            background: 'linear-gradient(135deg, var(--brand), #007aff)',
            borderRadius: 16,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 14px',
            fontSize: 22, fontWeight: 800, color: '#000',
            boxShadow: '0 0 32px rgba(0,201,167,0.3)',
          }}>M</div>
          <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: -1, marginBottom: 4 }}>
            Medi<span style={{ color: 'var(--brand)' }}>Sure AI</span>
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            Healthcare AI Platform · Insurance Intelligence
          </p>
        </div>

        {/* Login card */}
        <div style={{
          background: 'var(--bg-surface)',
          borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--border-default)',
          padding: '28px 28px',
          boxShadow: 'var(--shadow-lg)',
        }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>Sign in</h2>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 20 }}>
            Enter your credentials to access the platform
          </p>

          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              style={{
                background: 'var(--reject-dim)',
                border: '1px solid rgba(239,68,68,0.3)',
                borderRadius: 'var(--radius-md)',
                padding: '10px 14px',
                display: 'flex', alignItems: 'center', gap: 8,
                marginBottom: 16,
                fontSize: 13, color: 'var(--reject)',
              }}
            >
              <AlertCircle size={15} /> {error}
            </motion.div>
          )}

          <form onSubmit={handleLogin}>
            <div className="form-group" style={{ marginBottom: 14 }}>
              <label className="form-label">Username</label>
              <input
                className="form-input"
                type="text"
                placeholder="Enter username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
              />
            </div>

            <div className="form-group" style={{ marginBottom: 20 }}>
              <label className="form-label">Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  className="form-input"
                  type={showPw ? 'text' : 'password'}
                  placeholder="Enter password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete="current-password"
                  style={{ paddingRight: 40 }}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(s => !s)}
                  style={{
                    position: 'absolute', right: 12, top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--text-muted)', padding: 2,
                  }}
                >
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', height: 42, fontSize: 14 }}
              disabled={loading}
            >
              {loading
                ? <><div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> Signing in…</>
                : <><LogIn size={15} /> Sign In</>}
            </button>
          </form>
        </div>

        {/* Demo accounts */}
        <div style={{ marginTop: 20 }}>
          <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
            — Demo accounts (click to fill) —
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {DEMO_ACCOUNTS.map(acc => (
              <motion.button
                key={acc.role}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                onClick={() => fillDemo(acc)}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-md)',
                  padding: '10px 14px',
                  cursor: 'pointer',
                  textAlign: 'left',
                  display: 'flex', alignItems: 'center', gap: 12,
                  transition: 'border-color var(--transition)',
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = acc.color}
                onMouseLeave={e => e.currentTarget.style.borderColor = ''}
              >
                <div style={{
                  width: 32, height: 32, borderRadius: 'var(--radius-md)',
                  background: acc.color + '22', color: acc.color,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>{acc.icon}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: acc.color }}>{acc.role}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 1 }}>
                    {acc.desc}
                  </div>
                </div>
                <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                  {acc.username}
                </div>
              </motion.button>
            ))}
          </div>
        </div>

        <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-muted)', marginTop: 20 }}>
          MediSure AI v2.0 · Powered by Groq AI · MIT License
        </p>
      </motion.div>
    </div>
  )
}
