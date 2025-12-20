"use client"

import { useState } from "react"
import { useAuth } from "./AuthContext"
import "./Navbar.css"

interface NavbarProps {
  onNavigate: (page: "home" | "about" | "products" | "login" | "signup") => void
  currentPage: string
  user: { id: string; email: string; name: string } | null
}

export default function Navbar({ onNavigate, currentPage, user }: NavbarProps) {
  const { logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    onNavigate("home")
    setMenuOpen(false)
  }

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <button onClick={() => onNavigate("home")} className="navbar-logo">
          <span className="logo-icon">◆</span>
          AuraAI
        </button>

        <button className="menu-toggle" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle menu">
          ☰
        </button>

        <div className={`navbar-menu ${menuOpen ? "open" : ""}`}>
          <button
            onClick={() => {
              onNavigate("home")
              setMenuOpen(false)
            }}
            className="nav-link"
          >
            Home
          </button>
          <button
            onClick={() => {
              onNavigate("about")
              setMenuOpen(false)
            }}
            className="nav-link"
          >
            About
          </button>
          <button
            onClick={() => {
              onNavigate("products")
              setMenuOpen(false)
            }}
            className="nav-link"
          >
            Products
          </button>

          {user ? (
            <>
              <button
                onClick={() => {
                  onNavigate("dashboard" as "home")
                  setMenuOpen(false)
                }}
                className="nav-link"
              >
                Dashboard
              </button>
              <button onClick={handleLogout} className="btn btn-secondary nav-btn">
                Logout
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => {
                  onNavigate("login")
                  setMenuOpen(false)
                }}
                className="nav-link"
              >
                Login
              </button>
              <button
                onClick={() => {
                  onNavigate("signup")
                  setMenuOpen(false)
                }}
                className="btn btn-primary nav-btn"
              >
                Sign up
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
