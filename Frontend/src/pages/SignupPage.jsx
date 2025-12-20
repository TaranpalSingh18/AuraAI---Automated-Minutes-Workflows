"use client"

import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import GoogleAuthButton from "../components/GoogleAuthButton"
import "./AuthPages.css"

export default function SignupPage() {
  const [formData, setFormData] = useState({ name: "", email: "", password: "", confirmPassword: "", persona: "employee" })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const { user, signup, isLoading } = useAuth()
  const navigate = useNavigate()

  // Redirect if already logged in
  useEffect(() => {
    if (!isLoading && user) {
      navigate("/app", { replace: true })
    }
  }, [user, isLoading, navigate])

  const validateForm = () => {
    const newErrors = {}

    if (!formData.name.trim()) {
      newErrors.name = "Name is required"
    }
    if (!formData.email.trim()) {
      newErrors.email = "Email is required"
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Please enter a valid email"
    }
    if (!formData.password) {
      newErrors.password = "Password is required"
    } else if (formData.password.length < 6) {
      newErrors.password = "Password must be at least 6 characters"
    }
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match"
    }
    if (!formData.persona) {
      newErrors.persona = "Please select a role"
    }

    return newErrors
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
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
      await signup(formData.email, formData.password, formData.name, formData.persona)
      // Small delay to ensure state updates
      setTimeout(() => {
        navigate("/app", { replace: true })
      }, 100)
    } catch (err) {
      setErrors({ form: err.message || "Signup failed. Please try again." })
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
            <h1>Get started</h1>
            <p>Create your AuraAI account and start automating meetings</p>
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
              <label htmlFor="name">Full name</label>
              <input
                id="name"
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="John Doe"
                aria-invalid={!!errors.name}
                disabled={loading}
              />
              {errors.name && <span className="field-error">{errors.name}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
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
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="••••••••"
                aria-invalid={!!errors.password}
                disabled={loading}
              />
              {errors.password && <span className="field-error">{errors.password}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm password</label>
              <input
                id="confirmPassword"
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="••••••••"
                aria-invalid={!!errors.confirmPassword}
                disabled={loading}
              />
              {errors.confirmPassword && <span className="field-error">{errors.confirmPassword}</span>}
            </div>

            <div className="form-group">
              <label>I am signing up as:</label>
              <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem" }}>
                <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
                  <input
                    type="radio"
                    name="persona"
                    value="employee"
                    checked={formData.persona === "employee"}
                    onChange={handleChange}
                    disabled={loading}
                    style={{ marginRight: "0.5rem", cursor: "pointer" }}
                  />
                  <span>Employee</span>
                </label>
                <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
                  <input
                    type="radio"
                    name="persona"
                    value="admin"
                    checked={formData.persona === "admin"}
                    onChange={handleChange}
                    disabled={loading}
                    style={{ marginRight: "0.5rem", cursor: "pointer" }}
                  />
                  <span>Admin</span>
                </label>
              </div>
              {errors.persona && <span className="field-error">{errors.persona}</span>}
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: "100%" }} disabled={loading}>
              {loading ? "Creating account..." : "Get started — Free"}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              Already have an account?{" "}
              <Link to="/login" className="auth-link">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

