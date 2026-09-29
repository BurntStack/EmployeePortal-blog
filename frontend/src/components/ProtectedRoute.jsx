import { Navigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext.jsx'

/** Gates a portal route behind login, and optionally behind `is_staff`. */
export default function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-orange-500/30 border-t-orange-500" />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && !user.is_staff) return <Navigate to="/" replace />

  return children
}
