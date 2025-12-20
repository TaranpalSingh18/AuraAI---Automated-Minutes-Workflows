"use client"

import { Suspense } from "react"
import dynamic from "next/dynamic"
import { AuthProvider } from "./components/AuthContext"

// Dynamic imports for code splitting
const App = dynamic(() => import("./components/App"), { ssr: false })

export default function Home() {
  return (
    <AuthProvider>
      <Suspense
        fallback={
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
            Loading...
          </div>
        }
      >
        <App />
      </Suspense>
    </AuthProvider>
  )
}
