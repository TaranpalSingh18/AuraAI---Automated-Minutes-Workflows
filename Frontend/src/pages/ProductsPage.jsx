import { useParams, Link, Navigate } from "react-router-dom"
import { useState, useRef, useEffect } from "react"
import { Sidebar, SidebarBody, useSidebar } from "../components/ui/sidebar"
import { IconFileText, IconUser, IconChartBar } from "@tabler/icons-react"
import { motion } from "motion/react"
import { useAuth } from "../context/AuthContext"
import "./ProductsPage.css"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

const productInfo = {
  Trans2Actions: {
    title: "Transcript to Actions",
    description: "Convert raw meeting transcripts into actionable work items by identifying tasks, assigning them to the correct team members, extracting deadlines, and syncing everything  without manual effort.",
    placeholder: "Ask anything about Trans2Actions. Type @ for mentions."
  },
  "User-Load": {
    title: "User's Workload",
    description: "Fetch your pending tasks, view upcoming deadlines, and update task status instantly using simple natural-language prompts.",
    placeholder: "Ask anything about UserLoad. Type @ for mentions."
  },
  AdminPerspective: {
    title: "Admin's Perspective",
    description: "Assign tasks with deadlines and analyze employee performance through visual insights such as heatmaps, workload distribution charts, and progress timelines.",
    placeholder: "Ask anything about AdminPerspective. Type @ for mentions."
  }
}

export default function ProductsPage() {
  const { productName } = useParams()
  const { user, getAuthHeader } = useAuth()
  const [inputValue, setInputValue] = useState("")
  // Separate messages for each product/channel
  const [messagesByProduct, setMessagesByProduct] = useState({
    Trans2Actions: [],
    "User-Load": [],
    AdminPerspective: []
  })
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [documents, setDocuments] = useState([])
  const inputRef = useRef(null)
  const fileInputRef = useRef(null)
  
  const product = productInfo[productName] || productInfo.Trans2Actions
  
  // Get messages for current product
  const currentMessages = messagesByProduct[productName] || []

  // Redirect employees if they try to access AdminPerspective
  if (productName === "AdminPerspective" && user?.persona === "employee") {
    return <Navigate to="/products/Trans2Actions" replace />
  }

  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, 100)
  }

  // Update messages for a specific product
  const updateMessages = (product, newMessages) => {
    setMessagesByProduct(prev => ({
      ...prev,
      [product]: newMessages
    }))
  }

  // Add message to current product
  const addMessage = (message) => {
    setMessagesByProduct(prev => ({
      ...prev,
      [productName]: [...(prev[productName] || []), message]
    }))
  }

  useEffect(() => {
    // Focus input on mount
    if (inputRef.current) {
      inputRef.current.focus()
    }
    
    // Load documents for Trans2Actions
    if (productName === "Trans2Actions") {
      loadDocuments()
    }
    
    // Scroll to bottom when product changes or messages change for current product
    scrollToBottom()
  }, [productName, currentMessages])

  const loadDocuments = async () => {
    try {
      const response = await fetch(`${API_URL}/trans2actions/documents`, {
        headers: {
          ...getAuthHeader()
        }
      })
      if (response.ok) {
        const data = await response.json()
        setDocuments(data.documents || [])
      }
    } catch (error) {
      console.error("Failed to load documents:", error)
    }
  }

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Check file type
    const allowedExtensions = ['.pdf', '.txt', '.docx', '.doc']
    const fileExt = '.' + file.name.split('.').pop().toLowerCase()
    if (!allowedExtensions.includes(fileExt)) {
      const errorMessage = {
        id: Date.now(),
        type: "ai",
        text: `Error: Unsupported file type. Supported formats: PDF, TXT, DOCX`
      }
      addMessage(errorMessage)
      return
    }

    setUploading(true)
    const formData = new FormData()
    formData.append("file", file)

    try {
      // For file uploads, FormData automatically sets Content-Type with boundary
      // So we only include Authorization header
      const authHeaders = getAuthHeader()
      const headers = {}
      if (authHeaders.Authorization) {
        headers.Authorization = authHeaders.Authorization
      }
      
      const response = await fetch(`${API_URL}/trans2actions/upload`, {
        method: "POST",
        headers: headers,
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Failed to upload file")
      }

      const data = await response.json()
      
      // Reload documents
      await loadDocuments()
      
      // Show success message
      const successMessage = {
        id: Date.now(),
        type: "ai",
        text: data.message
      }
      addMessage(successMessage)
      
      // Clear file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now(),
        type: "ai",
        text: `Error: ${error.message}`
      }
      addMessage(errorMessage)
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteDocument = async (documentId) => {
    try {
      const response = await fetch(`${API_URL}/trans2actions/documents/${documentId}`, {
        method: "DELETE",
        headers: {
          ...getAuthHeader()
        }
      })

      if (response.ok) {
        await loadDocuments()
        const successMessage = {
          id: Date.now(),
          type: "ai",
          text: "Document deleted successfully"
        }
        addMessage(successMessage)
      } else {
        const error = await response.json()
        throw new Error(error.detail || "Failed to delete document")
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now(),
        type: "ai",
        text: `Error: ${error.message}`
      }
      addMessage(errorMessage)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!inputValue.trim() || loading) return

    const query = inputValue.trim()

    // Add user message
    const userMessage = {
      id: Date.now(),
      type: "user",
      text: query
    }
    addMessage(userMessage)
    setInputValue("")
    setLoading(true)

    try {
      // Handle different products
      if (productName === "Trans2Actions") {
        // Call Trans2Actions API
        const response = await fetch(`${API_URL}/trans2actions/query`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...getAuthHeader()
          },
          body: JSON.stringify({ query })
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || "Failed to query transcripts")
        }

        const data = await response.json()
        const aiMessage = {
          id: Date.now() + 1,
          type: "ai",
          text: data.answer
        }
        addMessage(aiMessage)
      } else if (productName === "User-Load") {
        // Check if query is about fetching tasks
        const lowerQuery = query.toLowerCase()
        
        if (lowerQuery.includes("fetch") || lowerQuery.includes("get") || lowerQuery.includes("show") || lowerQuery.includes("list")) {
          // Fetch tasks
          const fetchResponse = await fetch(`${API_URL}/userload/tasks`, {
            method: "GET",
            headers: {
              ...getAuthHeader()
            },
            // Note: board_id should be passed as query param or stored in settings
            // For now, we'll need to extract it from workspace or user input
          })
          
          if (fetchResponse.ok) {
            const data = await fetchResponse.json()
            if (data.tasks && data.tasks.length > 0) {
              const tasksText = data.tasks.map((task, idx) => 
                `${idx + 1}. ${task.name} (${task.state === "complete" ? "✓ Done" : "○ Pending"})`
              ).join("\n")
              
              const aiMessage = {
                id: Date.now() + 1,
                type: "ai",
                text: `Here are your tasks:\n\n${tasksText}\n\nYou can update tasks by saying something like "Mark task 1 as complete" or "Uncheck the first task".`
              }
              addMessage(aiMessage)
            } else {
              const aiMessage = {
                id: Date.now() + 1,
                type: "ai",
                text: "No tasks found. Make sure your Trello card '{Your Name}'s Todo' exists in your workspace."
              }
              addMessage(aiMessage)
            }
          } else {
            const error = await fetchResponse.json()
            throw new Error(error.detail || "Failed to fetch tasks")
          }
        } else {
          // Update task status
          const updateResponse = await fetch(`${API_URL}/userload/update-task`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...getAuthHeader()
            },
            body: JSON.stringify({ query })
          })
          
          if (updateResponse.ok) {
            const data = await updateResponse.json()
            const aiMessage = {
              id: Date.now() + 1,
              type: "ai",
              text: data.success ? data.message : `Error: ${data.message}`
            }
            addMessage(aiMessage)
          } else {
            const error = await updateResponse.json()
            throw new Error(error.detail || "Failed to update tasks")
          }
        }
      } else if (productName === "AdminPerspective") {
        // Call AdminPerspective API to assign tasks
        const response = await fetch(`${API_URL}/admin/assign-task`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...getAuthHeader()
          },
          body: JSON.stringify({ query })
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || "Failed to assign task")
        }

        const data = await response.json()
        const aiMessage = {
          id: Date.now() + 1,
          type: "ai",
          text: data.success 
            ? data.message 
            : `Error: ${data.message}`
        }
        addMessage(aiMessage)
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: "ai",
        text: `Error: ${error.message}`
      }
      addMessage(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const allSidebarLinks = [
    {
      label: "Trans2Actions",
      href: "/products/Trans2Actions",
      icon: <IconFileText size={20} />
    },
    {
      label: "User-Load",
      href: "/products/User-Load",
      icon: <IconUser size={20} />
    },
    {
      label: "AdminPerspective",
      href: "/products/AdminPerspective",
      icon: <IconChartBar size={20} />
    }
  ]

  // Filter sidebar links based on user persona
  const sidebarLinks = user?.persona === "employee"
    ? allSidebarLinks.filter((link) => link.label !== "AdminPerspective")
    : allSidebarLinks

  return (
    <div className="products-page">
      <Sidebar>
        <SidebarBody className="products-sidebar">
          <div className="products-sidebar-content">
            <div className="products-sidebar-links">
              {sidebarLinks.map((link) => {
                const ProductSidebarLink = () => {
                  const { open, animate } = useSidebar()
                  const isActive = productName === link.label || 
                                   (link.label === "User-Load" && productName === "User-Load")
                  
                  return (
                    <Link
                      to={link.href}
                      className={`products-sidebar-link ${isActive ? "active" : ""}`}
                    >
                      {link.icon}
                      <motion.span
                        animate={{
                          display: animate ? (open ? "inline-block" : "none") : "inline-block",
                          opacity: animate ? (open ? 1 : 0) : 1,
                        }}
                        className="products-sidebar-link-text"
                      >
                        {link.label}
                      </motion.span>
                    </Link>
                  )
                }
                return <ProductSidebarLink key={link.href} />
              })}
            </div>
          </div>
        </SidebarBody>
      </Sidebar>
      <div className="products-container">
        {/* Main Content Area */}
        <div className="products-main">
          {/* Product Title */}
          <div className="products-title-section">
            <h1 className="products-title">{product.title}</h1>
          </div>
          {/* Empty State - only show when no messages */}
          {currentMessages.length === 0 && !loading && (
            <div className="products-empty-state">
              <p className="products-empty-text">
                {product.description}
              </p>
              {productName === "Trans2Actions" && documents.length > 0 && (
                <div className="products-documents-section">
                  <h3 style={{ color: "var(--color-fg)", marginBottom: "var(--space-4)", fontSize: "1.1rem" }}>
                    Uploaded Documents ({documents.length})
                  </h3>
                  <div className="products-documents-list">
                    {documents.map((doc) => (
                      <div key={doc.id} className="products-document-item">
                        <span className="products-document-name">{doc.filename}</span>
                        <button
                          className="products-delete-btn"
                          onClick={() => handleDeleteDocument(doc.id)}
                          aria-label="Delete document"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 6L6 18M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Messages Area - appears above input */}
          {(currentMessages.length > 0 || loading) && (
            <div className="products-messages">
              {currentMessages.map((message) => (
                <div key={message.id} className={`products-message products-message-${message.type}`}>
                  <div className="products-message-content">
                    {message.text}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="products-message products-message-ai">
                  <div className="products-message-content">
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin">
                        <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                        <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m11.32 11.32l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m11.32-11.32l2.83-2.83" />
                      </svg>
                      <span>Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Search/Input Area - always at the bottom, below messages */}
          <div className="products-input-section">
            <form onSubmit={handleSubmit} className="products-input-form">
              <div className="products-input-wrapper">
                <div className="products-input-left">
                  <div className="products-ai-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 2L2 7l10 5 10-5-10-5z" />
                      <path d="M2 17l10 5 10-5" />
                      <path d="M2 12l10 5 10-5" />
                    </svg>
                  </div>
                  <input
                    ref={inputRef}
                    type="text"
                    className="products-input"
                    placeholder={product.placeholder}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    disabled={loading}
                  />
                </div>
                <div className="products-input-right">
                  {productName === "Trans2Actions" && (
                    <>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf,.txt,.docx,.doc"
                        onChange={handleFileUpload}
                        style={{ display: "none" }}
                        disabled={uploading}
                      />
                      <button 
                        type="button" 
                        className="products-icon-btn" 
                        aria-label="Upload file"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                      >
                        {uploading ? (
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin">
                            <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                            <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m11.32 11.32l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m11.32-11.32l2.83-2.83" />
                          </svg>
                        ) : (
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                          </svg>
                        )}
                      </button>
                    </>
                  )}
                  <button type="submit" className="products-submit-btn" aria-label="Submit" disabled={loading}>
                    {loading ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin">
                        <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                        <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m11.32 11.32l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m11.32-11.32l2.83-2.83" />
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M22 2L11 13" />
                        <path d="M22 2l-7 20-4-9-9-4 20-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>

        </div>
      </div>
    </div>
  )
}

