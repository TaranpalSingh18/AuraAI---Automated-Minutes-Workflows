"use client"

import { createContext, useContext, useState, useEffect } from "react"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [token, setToken] = useState(null)

  useEffect(() => {
    // Check localStorage on mount
    const storedToken = localStorage.getItem("auraai_token")
    const storedUser = localStorage.getItem("auraai_user")
    
    if (storedToken && storedUser) {
      setToken(storedToken)
      setUser(JSON.parse(storedUser))
      // Verify token is still valid
      verifyToken(storedToken)
    }
    setIsLoading(false)
  }, [])

  const verifyToken = async (tokenToVerify) => {
    try {
      const response = await fetch(`${API_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${tokenToVerify}`
        }
      })
      if (!response.ok) {
        throw new Error("Token invalid")
      }
      const userData = await response.json()
      setUser(userData)
      localStorage.setItem("auraai_user", JSON.stringify(userData))
    } catch (error) {
      logout()
    }
  }

  const login = async (email, password) => {
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ email, password })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Login failed")
      }

      const data = await response.json()
      setToken(data.access_token)
      setUser(data.user)
      localStorage.setItem("auraai_token", data.access_token)
      localStorage.setItem("auraai_user", JSON.stringify(data.user))
      return data.user
    } catch (error) {
      throw error
    }
  }

  const signup = async (email, password, name, persona) => {
    try {
      const response = await fetch(`${API_URL}/auth/signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ email, password, name, persona })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Signup failed")
      }

      const data = await response.json()
      setToken(data.access_token)
      setUser(data.user)
      localStorage.setItem("auraai_token", data.access_token)
      localStorage.setItem("auraai_user", JSON.stringify(data.user))
      return data.user
    } catch (error) {
      throw error
    }
  }

  const googleAuth = async (googleToken) => {
    try {
      const response = await fetch(`${API_URL}/auth/google`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ token: googleToken })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Google authentication failed")
      }

      const data = await response.json()
      setToken(data.access_token)
      setUser(data.user)
      localStorage.setItem("auraai_token", data.access_token)
      localStorage.setItem("auraai_user", JSON.stringify(data.user))
      return data.user
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem("auraai_token")
    localStorage.removeItem("auraai_user")
    setToken(null)
    setUser(null)
  }

  const getAuthHeader = () => {
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        token,
        login,
        signup,
        googleAuth,
        logout,
        getAuthHeader
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}

