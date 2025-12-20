"use client"

import { useState, useEffect } from "react"
import { useAuth } from "../../context/AuthContext"
import TaskCard from "../TaskCard"
import "./TasksView.css"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export default function TasksView() {
  const { user, getAuthHeader } = useAuth()
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState("all")
  const [lists, setLists] = useState([])

  const filteredTasks = tasks.filter((task) => {
    if (filter === "open") return task.status === "open"
    if (filter === "done") return task.status === "done"
    return true
  })

  useEffect(() => {
    fetchTasks()
  }, [])

  const fetchTasks = async () => {
    try {
      setLoading(true)
      
      // Get board ID from settings
      const settingsResponse = await fetch(`${API_URL}/settings`, {
        headers: {
          ...getAuthHeader(),
        }
      })
      
      if (!settingsResponse.ok) {
        console.error("Failed to fetch settings")
        return
      }
      
      const settings = await settingsResponse.json()
      const boardId = settings.workspace_id
      
      console.log("Settings loaded, boardId:", boardId)
      
      if (!boardId) {
        console.log("No board ID configured in settings")
        return
      }
      
      // Fetch all cards with full details
      const response = await fetch(`${API_URL}/composio/trello/cards?board_id=${boardId}`, {
        headers: {
          ...getAuthHeader(),
        }
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`Failed to fetch tasks: ${response.status}`, errorText)
        let errorMessage = "Failed to fetch tasks"
        try {
          const error = JSON.parse(errorText)
          errorMessage = error.detail || error.message || errorMessage
        } catch (e) {
          errorMessage = `HTTP ${response.status}: ${response.statusText}`
        }
        console.error("Error:", errorMessage)
        return
      }
      
      const data = await response.json()
      console.log("Trello cards response:", data)
      
      if (data && data.cards && data.cards.length > 0) {
        // Group cards by list for display
        const listsMap = new Map()
        data.cards.forEach((card) => {
          if (!listsMap.has(card.list_id)) {
            listsMap.set(card.list_id, {
              id: card.list_id,
              name: card.list_name,
              cards: []
            })
          }
          listsMap.get(card.list_id).cards.push(card)
        })
        setLists(Array.from(listsMap.values()))
        
        // Convert cards to tasks format
        const allTasks = data.cards.map((card) => {
          // Format last activity date
          let lastActivity = "No activity"
          if (card.dateLastActivity) {
            try {
              const date = new Date(card.dateLastActivity)
              lastActivity = date.toLocaleDateString("en-US", { 
                month: "short", 
                day: "numeric",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit"
              })
            } catch (e) {
              lastActivity = card.dateLastActivity
            }
          }
          
          // Format due date
          let dueDate = new Date().toISOString().split('T')[0]
          if (card.due) {
            try {
              dueDate = new Date(card.due).toISOString().split('T')[0]
            } catch (e) {
              // Use current date if parsing fails
            }
          }
          
            return {
              id: card.id,
              title: card.name,
              description: card.desc || "",
              status: card.closed ? "done" : "open",
            dueDate: dueDate,
            assignee: { id: "1", name: "You" },
            meetingIds: [],
            // Trello-specific fields
            closed: card.closed,
            shortUrl: card.shortUrl,
            url: card.url,
            dateLastActivity: lastActivity,
            commentsCount: card.comments_count || 0,
            checklistsCount: card.checklists_count || 0,
            listName: card.list_name,
            listId: card.list_id,
            dueComplete: card.dueComplete || false,
            labels: card.labels || []
          }
        })
        
        setTasks(allTasks)
        console.log(`Loaded ${allTasks.length} cards as tasks`)
      } else {
        console.error("Failed to fetch tasks - no cards data", data)
        if (data && data.cards && data.cards.length === 0) {
          console.log("Cards array is empty - board might have no cards")
        }
      }
    } catch (error) {
      console.error("Error fetching tasks:", error)
    } finally {
      setLoading(false)
    }
  }

  const toggleTaskStatus = async (id) => {
    // Find the task
    const task = tasks.find(t => t.id === id)
    if (!task) return
    
    // Update local state immediately
    const updatedTasks = tasks.map((t) => 
      t.id === id ? { ...t, status: t.status === "done" ? "open" : "done" } : t
    )
    setTasks(updatedTasks)
    
    // TODO: Update task status in Trello via API
    // This would require updating the checklist item status in Trello
  }

  return (
    <div className="tasks-view">
      <div className="view-header">
        <h1>Tasks</h1>
        <p className="view-subtitle">Manage your assigned tasks and action items</p>
        <p className="view-note">
          Tasks are synced with your Trello workspace (configure in Settings)
        </p>
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
        {loading ? (
          <div className="empty-state">
            <p>Loading tasks...</p>
          </div>
        ) : filteredTasks.length > 0 ? (
          filteredTasks.map((task) => (
            <TaskCard key={task.id} task={task} onToggleStatus={() => toggleTaskStatus(task.id)} />
          ))
        ) : (
          <div className="empty-state">
            <p>No cards found. Configure your Trello board ID in Settings and make sure your board has cards.</p>
          </div>
        )}
      </div>
    </div>
  )
}
