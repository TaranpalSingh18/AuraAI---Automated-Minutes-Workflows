"use client"

import { useState } from "react"
import { mockMeetings } from "../../utils/mockData"
import MeetingCard from "../MeetingCard"
import "../styles/MeetingsView.css"

export default function MeetingsView() {
  const [meetings] = useState(mockMeetings)

  return (
    <div className="meetings-view">
      <div className="view-header">
        <h1>Meetings</h1>
        <p className="view-subtitle">View meeting transcripts, summaries, and action items</p>
      </div>

      <div className="meetings-grid">
        {meetings.length > 0 ? (
          meetings.map((meeting) => <MeetingCard key={meeting.id} meeting={meeting} />)
        ) : (
          <div className="empty-state">
            <p>No meetings yet. Schedule your first meeting to get started.</p>
          </div>
        )}
      </div>
    </div>
  )
}
