"use client"

import { useRef, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import "./Navbar.css"

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [isProductsOpen, setIsProductsOpen] = useState(false)
  const [hoveredProduct, setHoveredProduct] = useState(null)
  const hoverTimer = useRef(null)

  const allProducts = [
    {
      key: "trans2actions",
      name: "Trans2Actions",
      description: "Transcript to Executable actions (assigned work, deadlines etc).",
    },
    {
      key: "userload",
      name: "User-Load",
      description:
        "Fetch pending tasks and deadlines, then update tasks via natural language prompts.",
    },
    {
      key: "adminperspective",
      name: "AdminPerspective",
      description:
        "Admins assign tasks/deadlines and analyze employee progress with heatmaps and more.",
    },
  ]

  // Filter products based on user persona
  const products = user?.persona === "employee"
    ? allProducts.filter((p) => p.key !== "adminperspective") // Employees see only Trans2Actions and User-Load
    : allProducts // Admins and non-logged-in users see all products

  const handleLogout = () => {
    logout()
    navigate("/")
  }

  const clearHoverTimer = () => {
    if (hoverTimer.current) {
      clearTimeout(hoverTimer.current)
      hoverTimer.current = null
    }
  }

  const handleProductItemEnter = (key) => {
    clearHoverTimer()
    hoverTimer.current = setTimeout(() => {
      setHoveredProduct(key)
    }, 1000)
  }

  const handleProductItemLeave = () => {
    clearHoverTimer()
    setHoveredProduct(null)
  }

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          <span className="logo-icon">◆</span>
          AuraAI
        </Link>

        <button className="menu-toggle" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle menu">
          ☰
        </button>

        <div className={`navbar-menu ${menuOpen ? "open" : ""}`}>
          <Link to="/" className="nav-link" onClick={() => setMenuOpen(false)}>
            Home
          </Link>
          <Link to="/about" className="nav-link" onClick={() => setMenuOpen(false)}>
            About
          </Link>
          <div
            className="nav-link products-dropdown"
            onMouseEnter={() => setIsProductsOpen(true)}
            onMouseLeave={() => {
              setIsProductsOpen(false)
              handleProductItemLeave()
            }}
          >
            <span>Products ▾</span>
            <div className={`products-menu ${isProductsOpen ? "open" : ""}`}>
              {products.map((product) => (
                <Link
                  key={product.key}
                  to={`/products/${product.name}`}
                  className="product-item"
                  onMouseEnter={() => handleProductItemEnter(product.key)}
                  onMouseLeave={handleProductItemLeave}
                  onClick={() => setMenuOpen(false)}
                >
                  <span className="product-name">{product.name}</span>
                  {hoveredProduct === product.key && (
                    <div className="product-description">{product.description}</div>
                  )}
                </Link>
              ))}
            </div>
          </div>

          {user ? (
            <>
              <Link to="/app" className="nav-link" onClick={() => setMenuOpen(false)}>
                Dashboard
              </Link>
              <button onClick={handleLogout} className="btn btn-secondary nav-btn">
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="nav-link" onClick={() => setMenuOpen(false)}>
                Login
              </Link>
              <Link to="/signup" className="btn btn-primary nav-btn" onClick={() => setMenuOpen(false)}>
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
