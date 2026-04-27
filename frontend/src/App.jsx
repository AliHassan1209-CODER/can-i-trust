import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './store/authStore'
import LoginPage    from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import CheckerPage  from './pages/CheckerPage'
import HistoryPage  from './pages/HistoryPage'

function ProtectedRoute({ children }) {
  const isAuth = useAuthStore(s => s.isAuth)
  return isAuth ? children : <Navigate to="/login" replace />
}

function GuestRoute({ children }) {
  const isAuth = useAuthStore(s => s.isAuth)
  return !isAuth ? children : <Navigate to="/dashboard" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: { background: '#1a1a2a', color: '#e8e8f4', border: '1px solid rgba(255,255,255,0.08)', fontFamily: 'DM Sans, sans-serif', fontSize: '0.85rem' },
          success: { iconTheme: { primary: '#1de9a5', secondary: '#080810' } },
          error:   { iconTheme: { primary: '#f04f4f', secondary: '#080810' } },
        }}
      />
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/login"    element={<GuestRoute><LoginPage /></GuestRoute>} />
        <Route path="/register" element={<GuestRoute><RegisterPage /></GuestRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/checker"   element={<ProtectedRoute><CheckerPage /></ProtectedRoute>} />
        <Route path="/history"   element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
