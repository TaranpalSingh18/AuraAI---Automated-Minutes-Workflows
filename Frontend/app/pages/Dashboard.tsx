"use client"

import { useState } from "react"
import { useAuth } from "../components/AuthContext"
import TasksView from "../components/dashboard/TasksView"
import MeetingsView from "../components/dashboard/MeetingsView"
import DashboardNav from "../components/DashboardNav"
import "../styles/Dashboard.css"

interface DashboardProps {
  onBack: () => void
}

export default function Dashboard({ onBack }: DashboardProps) {
  const { user } = useAuth()
  const [currentView, setCurrentView] = useState<"tasks" | "meetings" | "settings">("tasks")
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="dashboard">
      <DashboardNav
        currentView={currentView}
        setCurrentView={setCurrentView}
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        user={user}
        onBack={onBack}
      />
      <div className="dashboard-content">
        {currentView === "tasks" && <TasksView />}
        {currentView === "meetings" && <MeetingsView />}
      </div>
    </div>
  )
}
