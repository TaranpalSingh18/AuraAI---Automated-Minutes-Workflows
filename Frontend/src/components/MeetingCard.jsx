import "./MeetingCard.css"

export default function MeetingCard({ meeting }) {
  return (
    <div className="meeting-card">
      <div className="meeting-header">
        <h3 className="meeting-title">{meeting.title}</h3>
        <span className="meeting-date">
          {new Date(meeting.date).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>

      <p className="meeting-summary">{meeting.minutesSummary ? (meeting.minutesSummary.length > 200 ? meeting.minutesSummary.substring(0, 200) + "..." : meeting.minutesSummary) : "No summary available"}</p>

      <div className="meeting-footer">
        <div className="meeting-participants">
          <span className="participants-label">
            👥 {meeting.participants.length} participant{meeting.participants.length !== 1 ? "s" : ""}
          </span>
        </div>
        <div className="meeting-actions">
          <span className="action-items-count">
            ✓ {meeting.actionItems.length} action item{meeting.actionItems.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>
    </div>
  )
}
