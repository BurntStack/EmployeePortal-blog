import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext.jsx'
import ProtectedRoute from '@/components/ProtectedRoute.jsx'
import Login from '@/pages/Login.jsx'
import Dashboard from '@/pages/Dashboard.jsx'
import Review from '@/pages/Review.jsx'

// The rich text editor (TipTap/ProseMirror) is the heaviest dependency in
// this app — only the two post-editing routes need it, so it's kept out of
// the bundle everyone else (login, dashboard, review) has to download.
const PostEditor = lazy(() => import('@/pages/PostEditor.jsx'))

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route
          path="/posts/new"
          element={
            <ProtectedRoute>
              <Suspense fallback={null}>
                <PostEditor />
              </Suspense>
            </ProtectedRoute>
          }
        />
        <Route
          path="/posts/:slug/edit"
          element={
            <ProtectedRoute>
              <Suspense fallback={null}>
                <PostEditor />
              </Suspense>
            </ProtectedRoute>
          }
        />
        <Route path="/review" element={<ProtectedRoute adminOnly><Review /></ProtectedRoute>} />
      </Routes>
    </AuthProvider>
  )
}
