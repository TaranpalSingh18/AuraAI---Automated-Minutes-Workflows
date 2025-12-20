"use client"

import { useState, useEffect } from "react"
import { useAuth } from "../../context/AuthContext"
import "./Settings.css"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export default function Settings() {
  const { user, getAuthHeader } = useAuth()
  const [settings, setSettings] = useState({
    notifications: true,
    exportFormat: "txt",
    composioApiKey: "",
    geminiApiKey: "",
    workspaceId: "",
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState({ type: "", text: "" })
  const [trelloConnected, setTrelloConnected] = useState(false)
  const [checkingConnection, setCheckingConnection] = useState(false)
  const [trelloBoards, setTrelloBoards] = useState([])
  const [loadingBoards, setLoadingBoards] = useState(false)
  const [showBoardSelector, setShowBoardSelector] = useState(false)
  const [manualBoardInput, setManualBoardInput] = useState(false)

  // Load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_URL}/settings`, {
        headers: {
          ...getAuthHeader(),
        }
      })
      if (response.ok) {
        const data = await response.json()
        setSettings(prev => ({
          ...prev,
          composioApiKey: data.composio_api_key || "",
          geminiApiKey: data.gemini_api_key || "",
          workspaceId: data.workspace_id || "",
        }))
        // Update Trello connection status
        if (data.trello_connection) {
          setTrelloConnected(data.trello_connection.is_connected === true)
        }
      }
    } catch (error) {
      console.error("Failed to load settings:", error)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
  }

  const checkTrelloConnection = async () => {
    try {
      setCheckingConnection(true)
      const response = await fetch(`${API_URL}/composio/trello/status`, {
        headers: {
          ...getAuthHeader(),
        }
      })
      if (response.ok) {
        const data = await response.json()
        const connected = data.is_connected === true
        setTrelloConnected(connected)
        // If connected, fetch boards
        if (connected) {
          fetchTrelloBoards()
        }
      }
    } catch (error) {
      console.error("Failed to check Trello connection:", error)
    } finally {
      setCheckingConnection(false)
    }
  }

  const fetchTrelloBoards = async () => {
    try {
      setLoadingBoards(true)
      const response = await fetch(`${API_URL}/composio/trello/boards`, {
        headers: {
          ...getAuthHeader(),
        }
      })
      if (response.ok) {
        const data = await response.json()
        if (data.boards && data.boards.length > 0) {
          setTrelloBoards(data.boards)
          setShowBoardSelector(true)
        }
      }
    } catch (error) {
      console.error("Failed to fetch Trello boards:", error)
      // If fetch fails, still allow manual input
      setShowBoardSelector(true)
    } finally {
      setLoadingBoards(false)
    }
  }

  const initiateTrelloAuth = async () => {
    try {
      setMessage({ type: "", text: "" })
      const response = await fetch(`${API_URL}/composio/trello/initiate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        // Open OAuth URL in a new window
        window.open(data.redirect_url, "Trello Authorization", "width=600,height=700")
        setMessage({ 
          type: "success", 
          text: "Trello authorization window opened. Please complete the authorization." 
        })
        // Check connection status after a delay
        setTimeout(() => {
          checkTrelloConnection()
        }, 3000)
      } else {
        let errorMessage = "Failed to initiate Trello authorization"
        try {
          const error = await response.json()
          errorMessage = error.detail || error.message || errorMessage
        } catch (e) {
          errorMessage = `HTTP ${response.status}: ${response.statusText}`
        }
        setMessage({ type: "error", text: errorMessage })
      }
    } catch (error) {
      console.error("Trello auth error:", error)
      setMessage({ 
        type: "error", 
        text: `Failed to initiate Trello authorization: ${error.message || "Please ensure the backend server is running and restart it if needed."}` 
      })
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setMessage({ type: "", text: "" })
      
      // Only send fields that have values (not empty strings)
      const payload = {}
      if (settings.composioApiKey.trim()) {
        payload.composio_api_key = settings.composioApiKey.trim()
      }
      if (settings.geminiApiKey.trim()) {
        payload.gemini_api_key = settings.geminiApiKey.trim()
      }
      if (settings.workspaceId.trim()) {
        payload.workspace_id = settings.workspaceId.trim()
      }
      
      const response = await fetch(`${API_URL}/settings`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
        body: JSON.stringify(payload)
      })

      if (response.ok) {
        const data = await response.json()
        setMessage({ type: "success", text: "Settings saved successfully!" })
        setTimeout(() => setMessage({ type: "", text: "" }), 3000)
        
        // If Composio OAuth was initiated, open the redirect URL
        if (data.composio_oauth && data.composio_oauth.redirect_url) {
          if (data.composio_oauth.requires_auth) {
            // Open OAuth URL in a new window
            window.open(data.composio_oauth.redirect_url, "Trello Authorization", "width=600,height=700")
            setMessage({ 
              type: "success", 
              text: "Settings saved! Please complete Trello authorization in the popup window." 
            })
            // Check connection status after a delay
            setTimeout(() => {
              checkTrelloConnection()
            }, 2000)
          } else {
            setTrelloConnected(true)
          }
        }
      } else {
        const error = await response.json()
        setMessage({ type: "error", text: error.detail || "Failed to save settings" })
      }
    } catch (error) {
      setMessage({ type: "error", text: "Failed to save settings. Please try again." })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-page">
      <div className="view-header">
        <h1>Settings</h1>
        <p className="view-subtitle">Manage your account and preferences</p>
      </div>

      <div className="settings-grid">
        <section className="settings-section">
          <h2>Account</h2>
          <div className="setting-item">
            <label>Name</label>
            <input type="text" value={user?.name} disabled />
          </div>
          <div className="setting-item">
            <label>Email</label>
            <input type="email" value={user?.email} disabled />
          </div>
        </section>

        <section className="settings-section">
          <h2>Preferences</h2>
          <div className="setting-item">
            <label>
              <input
                type="checkbox"
                checked={settings.notifications}
                onChange={(e) => handleChange("notifications", e.target.checked)}
              />
              Email notifications for new meetings
            </label>
          </div>
          <div className="setting-item">
            <label>Default export format</label>
            <select value={settings.exportFormat} onChange={(e) => handleChange("exportFormat", e.target.value)}>
              <option value="txt">Text (.txt)</option>
              <option value="pdf">PDF (.pdf)</option>
            </select>
          </div>
        </section>

        <section className="settings-section">
          <h2>API Keys</h2>
          <div className="setting-item">
            <label>Composio API Key</label>
            <input
              type="password"
              placeholder={settings.composioApiKey ? "•••••••• (saved)" : "Enter your Composio API key"}
              value={settings.composioApiKey || ""}
              onChange={(e) => handleChange("composioApiKey", e.target.value)}
            />
            <p className="setting-help">Used to sync and execute workflows with Composio and Trello.</p>
            
            {settings.composioApiKey && (
              <div style={{ marginTop: "0.75rem", display: "flex", alignItems: "center", gap: "1rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <div style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    backgroundColor: trelloConnected ? "#28a745" : "#dc3545"
                  }} />
                  <span style={{ fontSize: "0.875rem", color: "var(--color-fg-muted)" }}>
                    Trello: {trelloConnected ? "Connected" : "Not Connected"}
                  </span>
                  {checkingConnection && (
                    <span style={{ fontSize: "0.875rem", color: "var(--color-fg-muted)" }}>Checking...</span>
                  )}
                </div>
                {!trelloConnected && (
                  <button
                    type="button"
                    onClick={initiateTrelloAuth}
                    className="btn btn-primary"
                    style={{ 
                      padding: "0.375rem 0.75rem", 
                      fontSize: "0.875rem",
                      height: "auto"
                    }}
                  >
                    Connect Trello
                  </button>
                )}
              </div>
            )}
          </div>
          <div className="setting-item">
            <label>Gemini API Key</label>
            <input
              type="password"
              placeholder={settings.geminiApiKey ? "•••••••• (saved)" : "Enter your Gemini API key"}
              value={settings.geminiApiKey || ""}
              onChange={(e) => handleChange("geminiApiKey", e.target.value)}
            />
            <p className="setting-help">Used for AI generation within the dashboard.</p>
          </div>
          <div className="setting-item">
            <label>Board ID / Workspace ID</label>
            {showBoardSelector && trelloBoards.length > 0 && !manualBoardInput ? (
              <select
                value={settings.workspaceId || ""}
                onChange={(e) => {
                  if (e.target.value === "__manual__") {
                    setManualBoardInput(true)
                    handleChange("workspaceId", "")
                  } else {
                    handleChange("workspaceId", e.target.value)
                  }
                }}
                style={{
                  padding: "0.5rem",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-bg)",
                  color: "var(--color-fg)",
                  fontSize: "0.875rem",
                  width: "100%"
                }}
              >
                <option value="">Select a board...</option>
                {trelloBoards.map((board) => (
                  <option key={board.id} value={board.id}>
                    {board.name} {board.organization ? `(${board.organization})` : ""}
                  </option>
                ))}
                <option value="__manual__">Enter manually...</option>
              </select>
            ) : (
              <input
                type="text"
                placeholder="Enter Trello Board ID"
                value={settings.workspaceId || ""}
                onChange={(e) => handleChange("workspaceId", e.target.value)}
              />
            )}
            {trelloConnected && (
              <div style={{ marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                {showBoardSelector && trelloBoards.length > 0 && !manualBoardInput && (
                  <button
                    type="button"
                    onClick={fetchTrelloBoards}
                    disabled={loadingBoards}
                    className="btn btn-secondary"
                    style={{ 
                      padding: "0.375rem 0.75rem", 
                      fontSize: "0.875rem",
                      height: "auto"
                    }}
                  >
                    {loadingBoards ? "Loading..." : "Refresh Boards"}
                  </button>
                )}
                {(!showBoardSelector || manualBoardInput) && trelloConnected && (
                  <button
                    type="button"
                    onClick={() => {
                      setManualBoardInput(false)
                      fetchTrelloBoards()
                    }}
                    disabled={loadingBoards}
                    className="btn btn-secondary"
                    style={{ 
                      padding: "0.375rem 0.75rem", 
                      fontSize: "0.875rem",
                      height: "auto"
                    }}
                  >
                    {loadingBoards ? "Loading..." : "Show Board List"}
                  </button>
                )}
              </div>
            )}
            <p className="setting-help">
              {trelloConnected 
                ? "Select a Trello board or enter the Board ID manually."
                : "Trello Board ID for task synchronization. Connect Trello first to see available boards."}
            </p>
          </div>
        </section>
      </div>

      {message.text && (
        <div className={`message ${message.type === "success" ? "message-success" : "message-error"}`} style={{
          padding: "1rem",
          marginBottom: "1rem",
          borderRadius: "var(--radius-md)",
          backgroundColor: message.type === "success" ? "#d4edda" : "#f8d7da",
          color: message.type === "success" ? "#155724" : "#721c24",
        }}>
          {message.text}
        </div>
      )}

      <div className="settings-actions">
        <button 
          className="btn btn-secondary" 
          onClick={handleSave}
          disabled={saving || loading}
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </div>
  )
}
