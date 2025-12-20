"use client"

import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useAuth } from "../../context/AuthContext"
import "./MeetingDetail.css"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export default function MeetingDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { getAuthHeader } = useAuth()
  const [meeting, setMeeting] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionItems, setActionItems] = useState([])
  const [summaryExpanded, setSummaryExpanded] = useState(false)
  const [transcriptExpanded, setTranscriptExpanded] = useState(false)
  
  // Character limit for truncation
  const SUMMARY_TRUNCATE_LENGTH = 500
  const TRANSCRIPT_TRUNCATE_LENGTH = 1000

  useEffect(() => {
    loadMeeting()
  }, [id])

  const loadMeeting = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_URL}/meetings/${id}`, {
        headers: {
          ...getAuthHeader(),
        }
      })
      if (response.ok) {
        const data = await response.json()
        // Transform backend data to frontend format
        const transformedMeeting = {
          id: data.id,
          title: data.title,
          date: data.date,
          participants: data.participants.map(name => ({ id: name.toLowerCase(), name })),
          minutesSummary: data.summary,
          transcript_text: data.transcript_text,
          actionItems: data.action_items.map((item, idx) => ({
            id: `action-${idx}`,
            text: item.text,
            assignee: item.assignee,
            assigned_by: item.assigned_by
          }))
        }
        setMeeting(transformedMeeting)
        setActionItems(transformedMeeting.actionItems)
      } else {
        // Meeting not found or access denied
        setMeeting(null)
      }
    } catch (error) {
      console.error("Failed to load meeting:", error)
      setMeeting(null)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="meeting-detail">
        <button onClick={() => navigate("/app/meetings")} className="btn btn-ghost">
          ← Back to Meetings
        </button>
        <div className="empty-state">Loading meeting...</div>
      </div>
    )
  }

  if (!meeting) {
    return (
      <div className="meeting-detail">
        <button onClick={() => navigate("/app/meetings")} className="btn btn-ghost">
          ← Back to Meetings
        </button>
        <div className="empty-state">Meeting not found</div>
      </div>
    )
  }

  const convertActionToTask = async (actionItem) => {
    try {
      console.log("Convert to task:", actionItem)
      
      // Call backend API to convert action item to Trello task
      const response = await fetch(`${API_URL}/meetings/${id}/convert-to-task`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          participant_name: actionItem.assignee,
          task_text: actionItem.text,
          deadline: actionItem.deadline || null
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }
      
      const result = await response.json()
      
      if (result.success) {
        // Remove action item from UI after successful conversion
        setActionItems(actionItems.filter((ai) => ai.id !== actionItem.id))
        alert(`✅ ${result.message || "Action item converted to task successfully!"}`)
      } else {
        const errorMsg = result.error || "Failed to convert action item to task"
        // Check if it's a permission error
        if (errorMsg.toLowerCase().includes("permission") || errorMsg.toLowerCase().includes("unauthorized")) {
          const userAction = confirm(
            `❌ ${errorMsg}\n\n` +
            `This usually means Trello needs to be reconnected with write permissions.\n\n` +
            `Would you like to open Settings to reconnect Trello?`
          )
          if (userAction) {
            navigate("/app/settings")
          }
        } else {
          alert(`❌ ${errorMsg}`)
        }
      }
    } catch (error) {
      console.error("Error converting action item to task:", error)
      alert(`❌ Failed to convert action item to task: ${error.message}`)
    }
  }

  const downloadMinutes = (format) => {
    const content = `
Meeting: ${meeting.title}
Date: ${new Date(meeting.date).toLocaleString()}
Participants: ${meeting.participants.map((p) => p.name).join(", ")}

SUMMARY
${meeting.minutesSummary}

TRANSCRIPT
${meeting.transcript_text || "Transcript not available"}

ACTION ITEMS
${actionItems.map((ai) => `• ${ai.text} (Assigned to: ${ai.assignee}${ai.assigned_by ? `, Assigned by: ${ai.assigned_by}` : ""})`).join("\n")}
    `.trim()

    const blob = new Blob([content], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${meeting.title.replace(/\s+/g, "_")}_minutes.txt`
    a.click()
  }

  return (
    <div className="meeting-detail">
      <button onClick={() => navigate("/app/meetings")} className="btn btn-ghost">
        ← Back to Meetings
      </button>

      <div className="detail-header">
        <div>
          <h1>{meeting.title}</h1>
          <p className="detail-meta">{new Date(meeting.date).toLocaleString()}</p>
        </div>
        <button onClick={() => downloadMinutes("txt")} className="btn btn-secondary">
          Export Minutes
        </button>
      </div>

      <div className="detail-grid">
        {/* Summary */}
        <section className="detail-section">
          <h2>Summary</h2>
          <div className="summary-box">
            <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>
              {summaryExpanded || meeting.minutesSummary.length <= SUMMARY_TRUNCATE_LENGTH
                ? meeting.minutesSummary
                : `${meeting.minutesSummary.substring(0, SUMMARY_TRUNCATE_LENGTH)}...`}
            </p>
            {meeting.minutesSummary.length > SUMMARY_TRUNCATE_LENGTH && (
              <button
                className="read-more-btn"
                onClick={() => setSummaryExpanded(!summaryExpanded)}
              >
                {summaryExpanded ? "Read less" : "Read more"}
              </button>
            )}
          </div>
        </section>

        {/* Participants */}
        <section className="detail-section">
          <h2>Participants</h2>
          <div className="participants-list">
            {meeting.participants.map((p) => (
              <div key={p.id} className="participant-item">
                <span className="participant-avatar">{p.name.charAt(0)}</span>
                <span className="participant-name">{p.name}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Transcript */}
        <section className="detail-section full-width">
          <h2>Transcript</h2>
          <div className="transcript-container">
            <div 
              className="transcript" 
              style={{ 
                whiteSpace: "pre-wrap", 
                padding: "1.5rem", 
                backgroundColor: "#1a1a1a", 
                border: "1px solid #333",
                borderRadius: "var(--radius-lg)",
                color: "#ffffff",
                maxHeight: transcriptExpanded ? "none" : "500px",
                overflowY: transcriptExpanded ? "visible" : "auto"
              }}
            >
              {transcriptExpanded || !meeting.transcript_text || meeting.transcript_text.length <= TRANSCRIPT_TRUNCATE_LENGTH
                ? (meeting.transcript_text || "Transcript not available")
                : `${meeting.transcript_text.substring(0, TRANSCRIPT_TRUNCATE_LENGTH)}...`}
            </div>
            {meeting.transcript_text && meeting.transcript_text.length > TRANSCRIPT_TRUNCATE_LENGTH && (
              <button
                className="read-more-btn"
                onClick={() => setTranscriptExpanded(!transcriptExpanded)}
                style={{ marginTop: "1rem" }}
              >
                {transcriptExpanded ? "Read less" : "Read more"}
              </button>
            )}
          </div>
        </section>

        {/* Action Items */}
        <section className="detail-section full-width">
          <h2>Action Items</h2>
          {actionItems.length > 0 ? (
            <div className="action-items-list">
              {actionItems.map((item) => (
                <div key={item.id} className="action-item">
                  <div className="action-content">
                    <p className="action-text">{item.text}</p>
                    <p className="action-assignee">Assigned to: {item.assignee}</p>
                  </div>
                  <button onClick={() => convertActionToTask(item)} className="btn btn-primary btn-small">
                    Convert to task
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted">No action items</p>
          )}
        </section>
      </div>
    </div>
  )
}
