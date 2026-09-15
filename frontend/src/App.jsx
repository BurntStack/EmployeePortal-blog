import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext.jsx'
import ProtectedRoute from '@/components/ProtectedRoute.jsx'
import Login from '@/pages/Login.jsx'
import Dashboard from '@/pages/Dashboard.jsx'
import PostEditor from '@/pages/PostEditor.jsx'
import Review from '@/pages/Review.jsx'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/posts/new" element={<ProtectedRoute><PostEditor /></ProtectedRoute>} />
        <Route path="/posts/:slug/edit" element={<ProtectedRoute><PostEditor /></ProtectedRoute>} />
        <Route path="/review" element={<ProtectedRoute adminOnly><Review /></ProtectedRoute>} />
      </Routes>
    </AuthProvider>
  )
}
