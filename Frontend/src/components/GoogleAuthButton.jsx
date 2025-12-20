"use client"

import { GoogleLogin } from "@react-oauth/google"
import { useAuth } from "../context/AuthContext"
import { useNavigate } from "react-router-dom"

export default function GoogleAuthButton({ onSuccess }) {
  const { googleAuth } = useAuth()
  const navigate = useNavigate()

  const handleSuccess = async (credentialResponse) => {
    try {
      await googleAuth(credentialResponse.credential)
      // Small delay to ensure state updates propagate
      await new Promise(resolve => setTimeout(resolve, 100))
      if (onSuccess) {
        onSuccess()
      } else {
        navigate("/app", { replace: true })
      }
    } catch (error) {
      console.error("Google authentication failed:", error)
      alert(error.message || "Google authentication failed. Please try again.")
    }
  }

  const handleError = () => {
    console.error("Google authentication failed")
    alert("Google authentication failed. Please try again.")
  }

  return (
    <div className="google-auth-container">
      <GoogleLogin
        onSuccess={handleSuccess}
        onError={handleError}
        useOneTap={false}
        theme="outline"
        size="large"
        text="signin_with"
        shape="rectangular"
        logo_alignment="left"
      />
    </div>
  )
}

