import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import './Navbar.css'

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [showMenu, setShowMenu] = useState(false)

  const handleLogout = () => {
    logout()
    toast.success('Logged out')
    navigate('/login')
    setShowMenu(false)
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
        <div className="nav-avatar-wrap">
          <button className="nav-avatar" title={user?.full_name} onClick={() => setShowMenu(!showMenu)}>
            {initials}
          </button>
          {showMenu && (
            <div className="nav-dropdown">
              <div className="nav-dropdown-user">
                <div className="nav-dropdown-name">{user?.full_name}</div>
                <div className="nav-dropdown-email">{user?.email}</div>
              </div>
              <hr className="nav-dropdown-divider" />
              <button className="nav-dropdown-item" onClick={handleLogout}>
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}