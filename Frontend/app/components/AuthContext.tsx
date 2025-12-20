"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"

interface User {
  id: string
  email: string
  name: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => User
  signup: (email: string, password: string, name: string) => User
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Check localStorage on mount
    if (typeof window !== "undefined") {
      const storedUser = localStorage.getItem("auraai_user")
      if (storedUser) {
        setUser(JSON.parse(storedUser))
      }
    }
    setIsLoading(false)
  }, [])

  const login = (email: string, password: string): User => {
    const newUser = { id: "1", email, name: email.split("@")[0] }
    localStorage.setItem("auraai_user", JSON.stringify(newUser))
    setUser(newUser)
    return newUser
  }

  const signup = (email: string, password: string, name: string): User => {
    const newUser = { id: "1", email, name }
    localStorage.setItem("auraai_user", JSON.stringify(newUser))
    setUser(newUser)
    return newUser
  }

  const logout = () => {
    localStorage.removeItem("auraai_user")
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, isLoading, login, signup, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}
