"use client"
import "./styles/MeetingCard.css"

interface Meeting {
  id: string
  title: string
  date: string
  participants: { id: string; name: string }[]
  minutesSummary: string
  actionItems: { id: string; text: string; assignee: string; status: string }[]
}

interface MeetingCardProps {
  meeting: Meeting
}

export default function MeetingCard({ meeting }: MeetingCardProps) {
  return (
    <div className="meeting-card">
      <div className="meeting-header">
        <h3>{meeting.title}</h3>
        <span className="meeting-date">{new Date(meeting.date).toLocaleDateString()}</span>
      </div>

      <div className="meeting-summary">
        <p>{meeting.minutesSummary}</p>
      </div>

      <div className="meeting-participants">
        <span className="participants-label">Participants:</span>
        <div className="participants-list">
          {meeting.participants.map((p) => (
            <span key={p.id} className="participant-badge">
              {p.name}
            </span>
          ))}
        </div>
      </div>

      <div className="meeting-actions">
        <span className="action-count">{meeting.actionItems.length} action items</span>
        <button className="btn-view-details">View details</button>
      </div>
    </div>
  )
}
