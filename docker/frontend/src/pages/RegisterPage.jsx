import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authAPI } from '../services/api'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import './AuthPage.css'

export default function RegisterPage() {
  const [form, setForm] = useState({ full_name: '', email: '', password: '' })
  const [otp, setOtp] = useState('')
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const { login } = useAuthStore()
  const navigate = useNavigate()

  const handleRegister = async (e) => {
    e.preventDefault()
    if (!form.full_name || !form.email || !form.password) return toast.error('Fill in all fields')
    if (form.password.length < 8) return toast.error('Password must be at least 8 characters')
    setLoading(true)
    try {
      await authAPI.register(form)
      toast.success('Verification code sent to your email!')
      setStep(2)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyOtp = async (e) => {
    e.preventDefault()
    if (!otp) return toast.error('Enter verification code')
    setLoading(true)
    try {
      const res = await authAPI.verifyOtp({ email: form.email, otp })
      const { access_token, refresh_token } = res.data
      useAuthStore.getState().login({}, access_token, refresh_token)
      const me = await authAPI.me()
      login(me.data, access_token, refresh_token)
      toast.success('Account created! Welcome 🎉')
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid OTP')
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
          <div className="auth-tagline">
            {step === 1 ? 'Start detecting fake news today' : 'Check your email for the code'}
          </div>
        </div>
        <div className="auth-tabs">
          <Link to="/login" className="auth-tab">Login</Link>
          <span className="auth-tab active">Sign Up</span>
        </div>

        {step === 1 ? (
          <form onSubmit={handleRegister} className="auth-form">
            <div className="field-group">
              <label className="field-label">Full Name</label>
              <input className="field-input" type="text" placeholder="Ali Hassan"
                value={form.full_name} onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} />
            </div>
            <div className="field-group">
              <label className="field-label">Email</label>
              <input className="field-input" type="email" placeholder="ali@gmail.com"
                value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
            </div>
            <div className="field-group">
              <label className="field-label">Password</label>
              <input className="field-input" type="password" placeholder="Min. 8 characters"
                value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
            </div>
            <button className="auth-submit" type="submit" disabled={loading}>
              {loading ? <span className="btn-spinner" /> : 'Create Account →'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerifyOtp} className="auth-form">
            <div className="field-group">
              <label className="field-label">Verification Code</label>
              <input className="field-input" type="text" placeholder="Enter 6-digit code"
                value={otp} onChange={e => setOtp(e.target.value)} maxLength={6} />
              <small style={{color: '#4f8ef7', marginTop: '8px', display: 'block'}}>
                Code sent to {form.email}
              </small>
            </div>
            <button className="auth-submit" type="submit" disabled={loading}>
              {loading ? <span className="btn-spinner" /> : 'Verify & Continue →'}
            </button>
            <button type="button" onClick={() => setStep(1)}
              style={{background: 'none', border: 'none', color: '#666', cursor: 'pointer', marginTop: '8px', width: '100%'}}>
              ← Back
            </button>
          </form>
        )}

        <p className="auth-footer">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </div>
    </div>
  )
}