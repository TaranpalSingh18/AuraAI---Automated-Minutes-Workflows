import { Routes, Route } from "react-router-dom"
import { GoogleOAuthProvider } from "@react-oauth/google"
import { AuthProvider } from "./context/AuthContext"
import ProtectedRoute from "./components/ProtectedRoute"
import Layout from "./components/Layout"
import LandingPage from "./pages/LandingPage"
import AboutPage from "./pages/AboutPage"
import ProductsPage from "./pages/ProductsPage"
import LoginPage from "./pages/LoginPage"
import SignupPage from "./pages/SignupPage"
import Dashboard from "./pages/Dashboard"
import AuraPointer from "./components/AuraPointer"

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ""

export default function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <AuraPointer />
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/products/:productName" element={<ProductsPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route
              path="/app/*"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
          </Route>
        </Routes>
      </AuthProvider>
    </GoogleOAuthProvider>
  )
}

