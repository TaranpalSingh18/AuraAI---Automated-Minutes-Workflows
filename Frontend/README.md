# AuraAI - Meeting Intelligence Platform

A professional SaaS-style web application that automates meeting minutes and transforms conversations into actionable tasks.

## 🚀 Features

- **Auto-Generated Minutes** - AI-powered transcription and summarization of meetings
- **Smart Task Management** - Convert action items to tasks instantly
- **Meeting Intelligence** - Complete meeting transcripts, summaries, and action items
- **Task Tracking** - Organize and track tasks with filters and due dates
- **Clean Interface** - Modern black & white aesthetic inspired by OpenAI

## 📋 Prerequisites

- Node.js (v16 or higher)
- npm or yarn

## 🔧 Installation

\`\`\`bash
# Clone the repository
git clone <repository-url>
cd auraai

# Install dependencies
npm install

# Start the development server
npm run dev
\`\`\`

The application will open automatically at `http://localhost:3000`.

## 📦 Building for Production

\`\`\`bash
npm run build
npm run preview
\`\`\`

## 🗂️ Project Structure

\`\`\`
src/
├── pages/              # Main page components
│   ├── LandingPage.jsx
│   ├── AboutPage.jsx
│   ├── ProductsPage.jsx
│   ├── LoginPage.jsx
│   ├── SignupPage.jsx
│   └── Dashboard.jsx
├── components/         # Reusable UI components
│   ├── Navbar.jsx
│   ├── Footer.jsx
│   ├── Layout.jsx
│   ├── TaskCard.jsx
│   ├── MeetingCard.jsx
│   ├── DashboardNav.jsx
│   └── dashboard/      # Dashboard-specific components
│       ├── TasksView.jsx
│       ├── MeetingsView.jsx
│       ├── MeetingDetail.jsx
│       └── Settings.jsx
├── context/            # React Context
│   └── AuthContext.jsx
├── utils/              # Utility functions and mock data
│   └── mockData.js
├── globals.css         # Global styles and design tokens
└── App.jsx            # Main App component
\`\`\`

## 🎨 Design System

### Color Palette
- **Primary**: `#000000` (Black)
- **Background**: `#ffffff` (White)
- **Dark Variants**: `#0f0f0f`, `#1a1a1a`, `#2b2b2b`
- **Neutrals**: `#767676`, `#d1d1d1`
- **Borders**: `#e5e5e5`

### Typography
- **Font Family**: System fonts (Helvetica, Segoe UI)
- **Body Line Height**: 1.6
- **Heading Weights**: 700, 600, 500

### Spacing Scale
\`\`\`
1:   4px
2:   8px
3:   12px
4:   16px
5:   20px
6:   24px
8:   32px
10:  40px
12:  48px
\`\`\`

### Border Radius
- **sm**: 4px
- **md**: 8px
- **lg**: 12px

## 🔐 Authentication

The app uses mock authentication with localStorage. In production, integrate with:
- OAuth providers (Google, GitHub)
- Email/password authentication
- Multi-factor authentication

Current mock auth stores user data in localStorage under `auraai_user`.

## 📡 API Integration

### Mock API Endpoints

The following mock data structures are defined in `src/utils/mockData.js`:

#### Tasks
\`\`\`javascript
{
  id: string,
  title: string,
  description: string,
  status: "open" | "done",
  dueDate: string (YYYY-MM-DD),
  assignee: { id, name },
  meetingIds: string[]
}
\`\`\`

#### Meetings
\`\`\`javascript
{
  id: string,
  title: string,
  date: string (ISO),
  participants: [{ id, name }],
  transcript: [{ time, speaker, text }],
  minutesSummary: string,
  actionItems: [{ id, text, assignee, status }]
}
\`\`\`

To integrate with real APIs, replace mock data fetches in components with actual API calls.

## ⚙️ Features Guide

### Landing Page
Hero section with call-to-action, trust indicators, and feature showcase. Responsive design for all screen sizes.

### Authentication
- **Login Page** (`/login`) - Email/password authentication with validation
- **Signup Page** (`/signup`) - New account creation with form validation
- Protected routes redirect unauthenticated users to login

### Dashboard (`/app`)
- **Tasks View** - Manage tasks with status filters (All, Open, Done)
- **Meetings View** - View all recorded meetings
- **Meeting Detail** - Complete meeting info including transcript, action items, and export
- **Settings** - Account and preference management

### Task Management
- Create tasks from action items
- Mark tasks as complete/incomplete
- Filter by status
- Visual indicators for overdue tasks
- Edit task details inline

### Meeting Features
- View meeting transcripts with timestamps
- AI-generated summaries and action items
- Convert action items to tasks
- Export meeting minutes (text format)
- Full participant list

## 🎯 Key User Flows

### 1. Join a Meeting
1. User navigates to Dashboard
2. Clicks on a meeting from the Meetings view
3. Views transcript, summary, and action items
4. Can convert action items to tasks

### 2. Manage Tasks
1. User views Tasks page
2. Filters tasks by status (All/Open/Done)
3. Can mark tasks complete
4. Views task details and linked meetings

### 3. Fetch Contents
User can select a task and fetch related documents/notes (feature ready for backend integration).

## 🧪 Testing

Add tests using Jest and React Testing Library:

\`\`\`bash
npm install --save-dev @testing-library/react @testing-library/jest-dom jest
\`\`\`

Run tests:
\`\`\`bash
npm test
\`\`\`

## 🚀 Deployment

### Deploy to Vercel
\`\`\`bash
npm install -g vercel
vercel
\`\`\`

### Deploy to Netlify
\`\`\`bash
npm install -g netlify-cli
netlify deploy --prod --dir=dist
\`\`\`

## 📝 Component Documentation

### Navbar
Navigation bar with logo, menu links, and auth buttons. Mobile-responsive hamburger menu.

**Props**: None (uses Router context)

### TaskCard
Displays a single task with status, due date, and assignee.

**Props**:
- `task`: Task object
- `onToggleStatus`: Callback function

### MeetingCard
Displays a single meeting summary.

**Props**:
- `meeting`: Meeting object

### DashboardNav
Sidebar navigation for dashboard with user profile and logout.

**Props**:
- `sidebarOpen`: Boolean
- `setSidebarOpen`: Setter function

## 🔄 State Management

Currently using React Context for authentication. For larger apps, consider:
- Redux
- Zustand
- Recoil

## ♿ Accessibility

- WCAG AA color contrast ratios met
- Keyboard navigation throughout the app
- Proper ARIA labels on interactive elements
- Screen reader friendly
- Respects `prefers-reduced-motion`

## 🤝 Contributing

1. Create a feature branch (`git checkout -b feature/AuraFeature`)
2. Commit changes (`git commit -m 'Add AuraFeature'`)
3. Push to branch (`git push origin feature/AuraFeature`)
4. Open a Pull Request

## 📄 License

MIT

## 🆘 Support

For issues and questions:
1. Check existing GitHub issues
2. Create a new issue with detailed reproduction steps
3. Contact support@auraai.com

---

**AuraAI** - Transform meetings into action. 🚀
