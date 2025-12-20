import { Outlet, useLocation } from "react-router-dom"
import Navbar from "./Navbar"
import Footer from "./Footer"

export default function Layout() {
  const location = useLocation()
  const isDashboard = location.pathname.startsWith("/app")
  const isProducts = location.pathname.startsWith("/products")

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <Navbar />
      <main style={{ flex: 1 }}>
        <Outlet />
      </main>
      {!isDashboard && !isProducts && <Footer />}
    </div>
  )
}
