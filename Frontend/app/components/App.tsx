"use client"

import { useState } from "react"
import { useAuth } from "./AuthContext"
import Navbar from "./Navbar"
import Footer from "./Footer"
import LandingPage from "../pages/LandingPage"
import AboutPage from "../pages/AboutPage"
import ProductsPage from "../pages/ProductsPage"
import LoginPage from "../pages/LoginPage"
import SignupPage from "../pages/SignupPage"
import Dashboard from "../pages/Dashboard"
import ProtectedRoute from "./ProtectedRoute"
import "./App.css"

type PageType = "home" | "about" | "products" | "login" | "signup" | "dashboard"

export default function App() {
  const { user } = useAuth()
  const [currentPage, setCurrentPage] = useState<PageType>("home")

  const handleNavigate = (page: PageType) => {
    setCurrentPage(page)
    window.scrollTo(0, 0)
  }

  const handleLoginSuccess = () => {
    handleNavigate("dashboard")
  }

  const handleDashboardBack = () => {
    handleNavigate("home")
  }

  const renderPage = () => {
    switch (currentPage) {
      case "home":
        return <LandingPage onGetStarted={() => handleNavigate(user ? "dashboard" : "signup")} />
      case "about":
        return <AboutPage />
      case "products":
        return <ProductsPage />
      case "login":
        return <LoginPage onSuccess={handleLoginSuccess} />
      case "signup":
        return <SignupPage onSuccess={handleLoginSuccess} />
      case "dashboard":
        return (
          <ProtectedRoute>
            <Dashboard onBack={handleDashboardBack} />
          </ProtectedRoute>
        )
      default:
        return <LandingPage onGetStarted={() => handleNavigate(user ? "dashboard" : "signup")} />
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      {currentPage !== "dashboard" && <Navbar onNavigate={handleNavigate} currentPage={currentPage} user={user} />}
      <main style={{ flex: 1 }}>{renderPage()}</main>
      {currentPage !== "dashboard" && <Footer />}
    </div>
  )
}
