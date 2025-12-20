"use client"
import "./TaskCard.css"

export default function TaskCard({ task, onToggleStatus }) {
  const isOverdue = new Date(task.dueDate) < new Date() && task.status === "open"
  const isDone = task.status === "done"

  return (
    <div className={`task-card ${isDone ? "done" : ""} ${isOverdue ? "overdue" : ""}`}>
      <div className="task-checkbox">
        <label className="checkbox-wrapper">
          <input
            type="checkbox"
            checked={isDone}
            onChange={onToggleStatus}
            aria-label={`Mark ${task.title} as done`}
          />
          <span className="checkmark"></span>
        </label>
      </div>

      <div className="task-content">
        <div className="task-header">
          <h3 className="task-title">
            {task.title}
            {task.closed && <span className="closed-badge">Closed</span>}
          </h3>
          {isOverdue && !isDone && <span className="overdue-badge">Overdue</span>}
        </div>
        
        {task.description && (
          <p className="task-description">{task.description}</p>
        )}
        
        <div className="task-meta">
          {task.listName && task.listName.trim() && (
            <div className="meta-item meta-list">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                <line x1="3" y1="18" x2="3.01" y2="18"></line>
              </svg>
              <span>{task.listName}</span>
            </div>
          )}
          
          <div className="meta-item meta-date">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="16" y1="2" x2="16" y2="6"></line>
              <line x1="8" y1="2" x2="8" y2="6"></line>
              <line x1="3" y1="10" x2="21" y2="10"></line>
            </svg>
            <span>{new Date(task.dueDate).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
          </div>
          
          {task.commentsCount > 0 && (
            <div className="meta-item meta-comments">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
              <span>{task.commentsCount}</span>
            </div>
          )}
          
          {task.checklistsCount > 0 && (
            <div className="meta-item meta-checklist">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 11 12 14 22 4"></polyline>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
              </svg>
              <span>{task.checklistsCount}</span>
            </div>
          )}
          
          {task.dateLastActivity && (
            <div className="meta-item meta-activity">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
              <span>{task.dateLastActivity}</span>
            </div>
          )}
        </div>
        
        {task.shortUrl && (
          <a 
            href={task.shortUrl || task.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="trello-link"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
              <polyline points="15 3 21 3 21 9"></polyline>
              <line x1="10" y1="14" x2="21" y2="3"></line>
            </svg>
            <span>View on Trello</span>
          </a>
        )}
      </div>
    </div>
  )
}
