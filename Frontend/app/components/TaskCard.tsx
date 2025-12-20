"use client"
import "./styles/TaskCard.css"

interface Task {
  id: string
  title: string
  description?: string
  status: "open" | "done"
  dueDate: string
  assignee?: { id: string; name: string }
}

interface TaskCardProps {
  task: Task
  onToggleStatus: () => void
}

export default function TaskCard({ task, onToggleStatus }: TaskCardProps) {
  const isOverdue = new Date(task.dueDate) < new Date() && task.status === "open"

  return (
    <div className="task-card">
      <div className="task-header">
        <div className="task-checkbox">
          <input
            type="checkbox"
            checked={task.status === "done"}
            onChange={onToggleStatus}
            id={`task-${task.id}`}
            aria-label={`Mark ${task.title} as ${task.status === "done" ? "open" : "done"}`}
          />
        </div>
        <div className="task-info">
          <h3 className={task.status === "done" ? "done" : ""}>{task.title}</h3>
          {task.description && <p className="task-description">{task.description}</p>}
        </div>
      </div>

      <div className="task-footer">
        <span className={`task-date ${isOverdue ? "overdue" : ""}`}>{new Date(task.dueDate).toLocaleDateString()}</span>
        {task.assignee && <span className="task-assignee">{task.assignee.name}</span>}
      </div>
    </div>
  )
}
