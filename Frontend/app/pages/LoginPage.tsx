"use client"

import type React from "react"
import { useState } from "react"
import { useAuth } from "../components/AuthContext"
import "../styles/AuthPages.css"

interface LoginPageProps {
  onSuccess: () => void
}

export default function LoginPage({ onSuccess }: LoginPageProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()

  const validateForm = () => {
    const newErrors: Record<string, string> = {}
    if (!email.trim()) newErrors.email = "Email is required"
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = "Please enter a valid email"
    }
    if (!password) newErrors.password = "Password is required"
    return newErrors
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const newErrors = validateForm()

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }

    setLoading(true)
    setErrors({})

    try {
      await new Promise((resolve) => setTimeout(resolve, 500))
      login(email, password)
      onSuccess()
    } catch (err) {
      setErrors({ form: "Login failed. Please try again." })
    } finally {
      setLoading(false)
    }
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
              Don't have an account? <button className="auth-link">Create one</button>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
