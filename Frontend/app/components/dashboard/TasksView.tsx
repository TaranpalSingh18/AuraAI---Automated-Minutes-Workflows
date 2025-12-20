"use client"

import { useState } from "react"
import TaskCard from "../TaskCard"
import { mockTasks } from "../../utils/mockData"
import "../styles/TasksView.css"

export default function TasksView() {
  const [tasks, setTasks] = useState(mockTasks)
  const [filter, setFilter] = useState("all")

  const filteredTasks = tasks.filter((task) => {
    if (filter === "open") return task.status === "open"
    if (filter === "done") return task.status === "done"
    return true
  })

  const toggleTaskStatus = (id: string) => {
    setTasks(
      tasks.map((task) => (task.id === id ? { ...task, status: task.status === "done" ? "open" : "done" } : task)),
    )
  }

  return (
    <div className="tasks-view">
      <div className="view-header">
        <h1>Tasks</h1>
        <p className="view-subtitle">Manage your assigned tasks and action items</p>
      </div>

      <div className="view-controls">
        <div className="filter-buttons">
          <button className={`filter-btn ${filter === "all" ? "active" : ""}`} onClick={() => setFilter("all")}>
            All ({tasks.length})
          </button>
          <button className={`filter-btn ${filter === "open" ? "active" : ""}`} onClick={() => setFilter("open")}>
            Open ({tasks.filter((t) => t.status === "open").length})
          </button>
          <button className={`filter-btn ${filter === "done" ? "active" : ""}`} onClick={() => setFilter("done")}>
            Done ({tasks.filter((t) => t.status === "done").length})
          </button>
        </div>
      </div>

      <div className="tasks-list">
        {filteredTasks.length > 0 ? (
          filteredTasks.map((task) => (
            <TaskCard key={task.id} task={task} onToggleStatus={() => toggleTaskStatus(task.id)} />
          ))
        ) : (
          <div className="empty-state">
            <p>No tasks yet. Join a meeting or assign an action item.</p>
          </div>
        )}
      </div>
    </div>
  )
}
