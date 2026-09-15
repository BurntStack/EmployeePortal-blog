import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { LogoMark } from '@/components/Logo.jsx'
import Button from '@/components/Button.jsx'
import { useAuth } from '@/context/AuthContext.jsx'

export default function Login() {
  const { user, loading, login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!loading && user) return <Navigate to="/" replace />

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(username, password)
      navigate('/')
    } catch {
      setError('Incorrect username or password.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ivory px-5">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <LogoMark className="h-12 w-12" />
          <h1 className="font-display text-xl font-bold text-ink">Employee Portal</h1>
          <p className="text-sm text-slate">Log in to write and manage your blog posts.</p>
        </div>

        <form onSubmit={onSubmit} className="flex flex-col gap-5 rounded-bento border border-line bg-white p-6 sm:p-8">
          <div className="flex flex-col gap-2">
            <label htmlFor="username" className="text-sm font-medium text-ink">Username</label>
            <input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              className="rounded-xl border border-line-strong bg-canvas px-4 py-3 text-sm text-ink outline-none transition-colors focus:border-orange-400"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="password" className="text-sm font-medium text-ink">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="rounded-xl border border-line-strong bg-canvas px-4 py-3 text-sm text-ink outline-none transition-colors focus:border-orange-400"
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <Button type="submit" size="lg" className="w-full" disabled={submitting}>
            {submitting ? 'Logging in…' : 'Log In'}
          </Button>
        </form>
      </div>
    </div>
  )
}
