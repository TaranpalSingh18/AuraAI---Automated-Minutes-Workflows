export const mockTasks = [
  {
    id: "1",
    title: "Q1 Planning Review",
    description: "Discuss quarterly goals and roadmap",
    status: "open",
    dueDate: "2025-01-15",
    assignee: { id: "1", name: "You" },
    meetingIds: ["m1"],
  },
  {
    id: "2",
    title: "Client Onboarding",
    description: "Prepare materials for new client",
    status: "done",
    dueDate: "2025-01-10",
    assignee: { id: "1", name: "You" },
    meetingIds: [],
  },
  {
    id: "3",
    title: "Team Standup Notes",
    description: "Document action items from standup",
    status: "open",
    dueDate: "2025-01-12",
    assignee: { id: "1", name: "You" },
    meetingIds: ["m2"],
  },
]

export const mockMeetings = [
  {
    id: "m1",
    title: "Q1 Planning Review",
    date: "2025-01-08T10:00:00Z",
    participants: [
      { id: "1", name: "You" },
      { id: "2", name: "Sarah" },
      { id: "3", name: "Mike" },
    ],
    transcript: [
      { time: "10:00", speaker: "You", text: "Alright everyone, let's discuss Q1 goals." },
      { time: "10:05", speaker: "Sarah", text: "I think we should focus on feature development." },
      { time: "10:10", speaker: "Mike", text: "Agreed. We need to allocate resources properly." },
      { time: "10:15", speaker: "You", text: "Great, let's break this down into action items." },
    ],
    minutesSummary:
      "Team discussed Q1 roadmap. Key focus areas: Feature development, resource allocation, and timeline planning.",
    actionItems: [
      { id: "ai1", text: "Create detailed feature roadmap", assignee: "Sarah", status: "open" },
      { id: "ai2", text: "Resource allocation plan", assignee: "Mike", status: "open" },
      { id: "ai3", text: "Timeline and milestones", assignee: "You", status: "open" },
    ],
  },
  {
    id: "m2",
    title: "Team Standup",
    date: "2025-01-07T09:00:00Z",
    participants: [
      { id: "1", name: "You" },
      { id: "2", name: "Sarah" },
    ],
    transcript: [
      { time: "09:00", speaker: "You", text: "What did everyone accomplish yesterday?" },
      { time: "09:02", speaker: "Sarah", text: "I finished the authentication module." },
      { time: "09:05", speaker: "You", text: "Great! Any blockers?" },
      { time: "09:07", speaker: "Sarah", text: "No blockers, moving to next task." },
    ],
    minutesSummary: "Quick standup: Authentication module completed. No blockers reported.",
    actionItems: [{ id: "ai4", text: "Review auth implementation", assignee: "You", status: "open" }],
  },
]
