import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../utils/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true)

  // Restore session on mount
  useEffect(() => {
    const token = localStorage.getItem('claimiq_token')
    const saved = localStorage.getItem('claimiq_user')
    if (token && saved) {
      try {
        const u = JSON.parse(saved)
        setUser(u)
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      } catch {
        localStorage.removeItem('claimiq_token')
        localStorage.removeItem('claimiq_user')
      }
    }
    setLoading(false)
  }, [])

  const login = useCallback(async (username, password) => {
    const res = await api.post('/auth/login', { username, password })
    const data = res.data
    localStorage.setItem('claimiq_token', data.access_token)
    localStorage.setItem('claimiq_user', JSON.stringify({
      username: data.username,
      full_name: data.full_name,
      role: data.role,
    }))
    api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
    setUser({ username: data.username, full_name: data.full_name, role: data.role })
    return data
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('claimiq_token')
    localStorage.removeItem('claimiq_user')
    delete api.defaults.headers.common['Authorization']
    setUser(null)
  }, [])

  const isAdmin    = user?.role === 'ADMIN'
  const isReviewer = user?.role === 'ADMIN' || user?.role === 'REVIEWER'

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAdmin, isReviewer }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
