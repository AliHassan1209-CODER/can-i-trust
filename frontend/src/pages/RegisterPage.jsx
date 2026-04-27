import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authAPI } from '../services/api'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import './AuthPage.css'

export default function RegisterPage() {
  const [form, setForm] = useState({ full_name: '', email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const { login } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.full_name || !form.email || !form.password) return toast.error('Fill in all fields')
    if (form.password.length < 8) return toast.error('Password must be at least 8 characters')
    setLoading(true)
    try {
      await authAPI.register(form)
      const res = await authAPI.login({ email: form.email, password: form.password })
      const { access_token, refresh_token } = res.data
      const me = await authAPI.me()
      login(me.data, access_token, refresh_token)
      toast.success('Account created! Welcome 🎉')
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed')
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
          <div className="auth-tagline">Start detecting fake news today</div>
        </div>

        <div className="auth-tabs">
          <Link to="/login" className="auth-tab">Login</Link>
          <span className="auth-tab active">Sign Up</span>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="field-group">
            <label className="field-label">Full Name</label>
            <input
              className="field-input"
              type="text"
              placeholder="Ali Hassan"
              value={form.full_name}
              onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
            />
          </div>
          <div className="field-group">
            <label className="field-label">Email</label>
            <input
              className="field-input"
              type="email"
              placeholder="ali@example.com"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            />
          </div>
          <div className="field-group">
            <label className="field-label">Password</label>
            <input
              className="field-input"
              type="password"
              placeholder="Min. 8 characters"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
            />
          </div>
          <button className="auth-submit" type="submit" disabled={loading}>
            {loading ? <span className="btn-spinner" /> : 'Create Account →'}
          </button>
        </form>

        <p className="auth-footer">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </div>
    </div>
  )
}
