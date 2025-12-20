"use client"
import { Link, useLocation } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import "./DashboardNav.css"

export default function DashboardNav({ sidebarOpen, setSidebarOpen }) {
  const location = useLocation()
  const { user, logout } = useAuth()
  const pathname = location.pathname

  const isActive = (path) => {
    return pathname === `/app${path}` || pathname.startsWith(`/app${path}/`)
  }

  const navItems = [
    { path: "/tasks", label: "Tasks", icon: "☐" },
    { path: "/meetings", label: "Meetings", icon: "🎙" },
    { path: "/settings", label: "Settings", icon: "⚙" },
  ]

  return (
    <>
      <nav className={`dashboard-nav ${sidebarOpen ? "open" : "closed"}`}>
        <div className="nav-header">
          <Link to="/app" className="nav-logo">
            ◆ AuraAI
          </Link>
          <button className="nav-toggle" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Toggle sidebar">
            ✕
          </button>
        </div>

        <div className="nav-items">
          {navItems.map((item) => (
            <Link key={item.path} to={`/app${item.path}`} className={`nav-item ${isActive(item.path) ? "active" : ""}`}>
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </Link>
          ))}
        </div>

        <div className="nav-footer">
          <div className="user-info">
            <div className="user-avatar">{user?.name?.charAt(0).toUpperCase()}</div>
            <div className="user-details">
              <p className="user-name">{user?.name}</p>
              <p className="user-email">{user?.email}</p>
            </div>
          </div>
          <button onClick={logout} className="btn btn-ghost logout-btn">
            Logout
          </button>
        </div>
      </nav>

      {sidebarOpen && <div className="nav-overlay" onClick={() => setSidebarOpen(false)}></div>}
    </>
  )
}
