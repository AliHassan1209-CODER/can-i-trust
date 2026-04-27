import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import './Navbar.css'

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const { pathname } = useLocation()

  const handleLogout = () => {
    logout()
    toast.success('Logged out')
    navigate('/login')
  }

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0,2)
    : 'U'

  return (
    <nav className="navbar">
      <Link to="/dashboard" className="nav-logo">
        Can I <span>Trust?</span>
      </Link>

      <div className="nav-links">
        <Link to="/dashboard" className={`nav-link ${pathname === '/dashboard' ? 'active' : ''}`}>
          Dashboard
        </Link>
        <Link to="/history" className={`nav-link ${pathname === '/history' ? 'active' : ''}`}>
          History
        </Link>
      </div>

      <div className="nav-right">
        <Link to="/checker" className="nav-check-btn">
          <span className="btn-dot" />
          Fake News Check
        </Link>
        <button className="nav-avatar" title={user?.full_name} onClick={handleLogout}>
          {initials}
        </button>
      </div>
    </nav>
  )
}
