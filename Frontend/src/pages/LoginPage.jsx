"use client"

import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import GoogleAuthButton from "../components/GoogleAuthButton"
import "./AuthPages.css"

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const { user, login, isLoading } = useAuth()
  const navigate = useNavigate()

  // Redirect if already logged in
  useEffect(() => {
    if (!isLoading && user) {
      navigate("/app", { replace: true })
    }
  }, [user, isLoading, navigate])

  const validateForm = () => {
    const newErrors = {}
    if (!email.trim()) newErrors.email = "Email is required"
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = "Please enter a valid email"
    }
    if (!password) newErrors.password = "Password is required"
    return newErrors
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const newErrors = validateForm()

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }

    setLoading(true)
    setErrors({})

    try {
      await login(email, password)
      // Small delay to ensure state updates
      setTimeout(() => {
        navigate("/app", { replace: true })
      }, 100)
    } catch (err) {
      setErrors({ form: err.message || "Login failed. Please try again." })
      setLoading(false)
    }
  }

  const handleGoogleSuccess = () => {
    // Small delay to ensure state updates
    setTimeout(() => {
      navigate("/app", { replace: true })
    }, 100)
  }

  // Show loading if checking auth state
  if (isLoading) {
    return (
      <div className="auth-page">
        <div className="auth-container">
          <div className="auth-box">
            <div style={{ textAlign: "center", padding: "2rem" }}>Loading...</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-box">
          <div className="auth-header">
            <h1>Welcome back</h1>
            <p>Sign in to your AuraAI account to continue</p>
          </div>

          {errors.form && <div className="error-message">{errors.form}</div>}

          {/* Google Auth Button */}
          <div style={{ marginBottom: "1.5rem" }}>
            <GoogleAuthButton onSuccess={handleGoogleSuccess} />
          </div>

          <div style={{ 
            display: "flex", 
            alignItems: "center", 
            color: "#666"
          }}>
            <div style={{ flex: 1, height: "1px", background: "#e5e5e5" }}></div>
            <span style={{ margin: "0 1rem" }}>or</span>
            <div style={{ flex: 1, height: "1px", background: "#e5e5e5" }}></div>
          </div>

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                aria-invalid={!!errors.email}
                disabled={loading}
              />
              {errors.email && <span className="field-error">{errors.email}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                aria-invalid={!!errors.password}
                disabled={loading}
              />
              {errors.password && <span className="field-error">{errors.password}</span>}
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: "100%" }} disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              Don't have an account?{" "}
              <Link to="/signup" className="auth-link">
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

