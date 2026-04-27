import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authAPI } from '../services/api'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import './AuthPage.css'

export default function LoginPage() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const { login } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.email || !form.password) return toast.error('Fill in all fields')
    setLoading(true)
    try {
      const res = await authAPI.login(form)
      const { access_token, refresh_token } = res.data
      const me = await authAPI.me()
      // set token first so interceptor works for /me
      login(me.data, access_token, refresh_token)
      toast.success(`Welcome back, ${me.data.full_name.split(' ')[0]}!`)
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-bg">
      <div className="auth-glow" />
      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-logo">Can I <span>Trust?</span></div>
          <div className="auth-tagline">AI-powered fake news detection</div>
        </div>

        <div className="auth-tabs">
          <span className="auth-tab active">Login</span>
          <Link to="/register" className="auth-tab">Sign Up</Link>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="field-group">
            <label className="field-label">Email</label>
            <input
              className="field-input"
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            />
          </div>
          <div className="field-group">
            <label className="field-label">Password</label>
            <input
              className="field-input"
              type="password"
              placeholder="••••••••"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
            />
          </div>
          <button className="auth-submit" type="submit" disabled={loading}>
            {loading ? <span className="btn-spinner" /> : 'Login →'}
          </button>
        </form>

        <p className="auth-footer">
          Don't have an account? <Link to="/register">Sign up</Link>
        </p>
      </div>
    </div>
  )
}
