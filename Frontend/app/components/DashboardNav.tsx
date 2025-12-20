"use client"
import "./DashboardNav.css"

interface User {
  id: string
  email: string
  name: string
}

interface DashboardNavProps {
  currentView: string
  setCurrentView: (view: "tasks" | "meetings" | "settings") => void
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  user: User | null
  onBack: () => void
}

export default function DashboardNav({
  currentView,
  setCurrentView,
  sidebarOpen,
  setSidebarOpen,
  user,
  onBack,
}: DashboardNavProps) {
  return (
    <>
      <nav className={`dashboard-nav ${sidebarOpen ? "open" : "closed"}`}>
        <div className="nav-header">
          <button onClick={onBack} className="nav-logo">
            ◆ AuraAI
          </button>
          <button className="nav-toggle" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Toggle sidebar">
            ✕
          </button>
        </div>

        <div className="nav-items">
          {[
            { id: "tasks", label: "Tasks", icon: "☐" },
            { id: "meetings", label: "Meetings", icon: "🎙" },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setCurrentView(item.id as "tasks" | "meetings" | "settings")}
              className={`nav-item ${currentView === item.id ? "active" : ""}`}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
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
        </div>
      </nav>

      {sidebarOpen && <div className="nav-overlay" onClick={() => setSidebarOpen(false)}></div>}
    </>
  )
}
