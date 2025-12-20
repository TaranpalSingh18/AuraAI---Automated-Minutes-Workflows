"use client"
import "../styles/AboutPage.css"

export default function AboutPage() {
  return (
    <div className="about-page">
      <section className="about-hero">
        <div className="about-container">
          <h1>About AuraAI</h1>
          <p className="lead">
            We're building the future of meeting intelligence. Transform how your team captures, organizes, and acts on
            meeting insights.
          </p>
        </div>
      </section>

      <section className="about-content">
        <div className="about-container">
          <div className="content-block">
            <h2>Our Mission</h2>
            <p>
              Meeting overload is destroying productivity. Teams waste hours transcribing notes, extracting action
              items, and searching for context. We automate this entirely, freeing your team to focus on what matters:
              execution.
            </p>
          </div>

          <div className="content-block">
            <h2>Why AuraAI?</h2>
            <div className="why-grid">
              <div className="why-item">
                <h3>AI-Powered</h3>
                <p>
                  Advanced language models understand context, extract key points, and generate meaningful summaries
                  automatically.
                </p>
              </div>
              <div className="why-item">
                <h3>Team Focused</h3>
                <p>
                  Built for modern, distributed teams. Easy collaboration, clear ownership, and transparent action
                  tracking.
                </p>
              </div>
              <div className="why-item">
                <h3>Privacy First</h3>
                <p>Your data stays yours. Enterprise-grade security with full compliance and zero tracking.</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
