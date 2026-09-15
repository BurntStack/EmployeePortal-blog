import { useEffect, useRef, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { LogoMark } from '@/components/Logo.jsx'
import { useAuth } from '@/context/AuthContext.jsx'

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

export default function Login() {
  const { user, loading, loginWithGoogle } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const buttonRef = useRef(null)

  if (!loading && user) return <Navigate to="/" replace />

  useEffect(() => {
    if (!CLIENT_ID) return

    let cancelled = false

    const render = () => {
      if (cancelled || !window.google?.accounts?.id || !buttonRef.current) return
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        // A UX hint only — it pre-selects the right Google account chooser,
        // it is not what enforces the domain restriction. The backend's
        // verified `hd` claim check on the ID token is the real boundary.
        hd: 'burntstack.com',
        callback: async ({ credential }) => {
          setError('')
          try {
            await loginWithGoogle(credential)
            navigate('/')
          } catch (err) {
            setError(err.response?.data?.detail || 'Could not sign you in.')
          }
        },
      })
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: 'outline',
        size: 'large',
        width: 320,
      })
    }

    // The GSI script loads async — poll briefly until it's ready.
    const interval = setInterval(() => {
      if (window.google?.accounts?.id) {
        clearInterval(interval)
        render()
      }
    }, 100)

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [loginWithGoogle, navigate])

  return (
    <div className="flex min-h-screen items-center justify-center bg-ivory px-5">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <LogoMark className="h-12 w-12" />
          <h1 className="font-display text-xl font-bold text-ink">Employee Portal</h1>
          <p className="text-sm text-slate">Sign in with your @burntstack.com Google account.</p>
        </div>

        <div className="flex flex-col items-center gap-4 rounded-bento border border-line bg-white p-6 sm:p-8">
          {CLIENT_ID ? (
            <div ref={buttonRef} />
          ) : (
            <p className="text-center text-sm text-red-500">
              Google sign-in isn&apos;t configured yet — set VITE_GOOGLE_CLIENT_ID.
            </p>
          )}
          {error && <p className="text-center text-sm text-red-500">{error}</p>}
        </div>
      </div>
    </div>
  )
}
