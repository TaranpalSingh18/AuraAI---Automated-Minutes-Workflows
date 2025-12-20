"use client"

import { useState } from "react"
import { Routes, Route } from "react-router-dom"
import DashboardNav from "../components/DashboardNav"
import TasksView from "../components/dashboard/TasksView"
import MeetingsView from "../components/dashboard/MeetingsView"
import MeetingDetail from "../components/dashboard/MeetingDetail"
import Settings from "../components/dashboard/Settings"
import "./Dashboard.css"

export default function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="dashboard">
      <DashboardNav sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="dashboard-content">
        <Routes>
          <Route path="/" element={<TasksView />} />
          <Route path="/tasks" element={<TasksView />} />
          <Route path="/meetings" element={<MeetingsView />} />
          <Route path="/meetings/:id" element={<MeetingDetail />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </div>
  )
}
