import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api from '@/lib/axios.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchMe = useCallback(async () => {
    try {
      const { data } = await api.get('/auth/me/')
      setUser(data)
    } catch {
      setUser(null)
    }
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('burntstack-access')
    if (!token) {
      setLoading(false)
      return
    }
    fetchMe().finally(() => setLoading(false))
  }, [fetchMe])

  const login = async (username, password) => {
    const { data } = await api.post('/auth/token/', { username, password })
    localStorage.setItem('burntstack-access', data.access)
    localStorage.setItem('burntstack-refresh', data.refresh)
    await fetchMe()
  }

  const logout = () => {
    localStorage.removeItem('burntstack-access')
    localStorage.removeItem('burntstack-refresh')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
