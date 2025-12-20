"use client"

import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { useAuth } from "../../context/AuthContext"
import MeetingCard from "../MeetingCard"
import "./MeetingsView.css"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export default function MeetingsView() {
  const { user, getAuthHeader } = useAuth()
  const [meetings, setMeetings] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState({ type: "", text: "" })
  const isAdmin = user?.persona === "admin"

  useEffect(() => {
    loadMeetings()
  }, [])

  const loadMeetings = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_URL}/meetings`, {
        headers: {
          ...getAuthHeader(),
        }
      })
      if (response.ok) {
        const data = await response.json()
        // Transform backend data to match frontend format
        const transformedMeetings = data.map(meeting => ({
          id: meeting.id,
          title: meeting.title,
          date: meeting.date,
          participants: meeting.participants.map(name => ({ id: name.toLowerCase(), name })),
          minutesSummary: meeting.summary,
          actionItems: meeting.action_items.map((item, idx) => ({
            id: `action-${idx}`,
            text: item.text,
            assignee: item.assignee
          })),
          transcript: meeting.transcript_text.split('\n').map((line, idx) => ({
            time: `${idx + 1}`,
            speaker: "Speaker",
            text: line
          }))
        }))
        setMeetings(transformedMeetings)
      }
    } catch (error) {
      console.error("Failed to load meetings:", error)
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    if (!file.name.endsWith('.docx')) {
      setMessage({ type: "error", text: "Only .docx files are supported" })
      setTimeout(() => setMessage({ type: "", text: "" }), 3000)
      return
    }

    try {
      setUploading(true)
      setMessage({ type: "", text: "" })
      
      const formData = new FormData()
      formData.append('file', file)
      
      // Get workspace ID from user settings if available
      const settingsResponse = await fetch(`${API_URL}/settings`, {
        headers: { ...getAuthHeader() }
      })
      let workspaceId = null
      if (settingsResponse.ok) {
        const settings = await settingsResponse.json()
        workspaceId = settings.workspace_id
      }

      if (workspaceId) {
        formData.append('workspace_id', workspaceId)
      }

      const response = await fetch(`${API_URL}/meetings/upload`, {
        method: "POST",
        headers: {
          ...getAuthHeader(),
        },
        body: formData
      })

      if (response.ok) {
        setMessage({ type: "success", text: "Transcript uploaded and processed successfully!" })
        setTimeout(() => {
          setMessage({ type: "", text: "" })
          loadMeetings()
        }, 2000)
      } else {
        const error = await response.json()
        setMessage({ type: "error", text: error.detail || "Failed to upload transcript" })
      }
    } catch (error) {
      setMessage({ type: "error", text: "Failed to upload transcript. Please try again." })
    } finally {
      setUploading(false)
      e.target.value = "" // Reset file input
    }
  }

  return (
    <div className="meetings-view">
      <div className="view-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1>Meetings</h1>
            <p className="view-subtitle">View meeting transcripts, summaries, and action items</p>
          </div>
          {isAdmin && (
            <label className="btn btn-primary" style={{ cursor: "pointer", marginTop: "0.5rem" }}>
              {uploading ? "Uploading..." : "Upload Transcript"}
              <input
                type="file"
                accept=".docx"
                onChange={handleFileUpload}
                disabled={uploading}
                style={{ display: "none" }}
              />
            </label>
          )}
        </div>
      </div>

      {message.text && (
        <div className={`message ${message.type === "success" ? "message-success" : "message-error"}`} style={{
          padding: "1rem",
          marginBottom: "1.5rem",
          borderRadius: "var(--radius-md)",
          backgroundColor: message.type === "success" ? "#d4edda" : "#f8d7da",
          color: message.type === "success" ? "#155724" : "#721c24",
        }}>
          {message.text}
        </div>
      )}

      {loading ? (
        <div className="empty-state">
          <p>Loading meetings...</p>
        </div>
      ) : (
        <div className="meetings-list">
          {meetings.length > 0 ? (
            meetings.map((meeting) => (
              <Link key={meeting.id} to={`/app/meetings/${meeting.id}`} style={{ textDecoration: "none" }}>
                <MeetingCard meeting={meeting} />
              </Link>
            ))
          ) : (
            <div className="empty-state">
              <p>{isAdmin ? "No meetings recorded yet. Upload a transcript to get started." : "No meetings available."}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
