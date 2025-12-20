"use client"
import "../styles/LandingPage.css"

interface LandingPageProps {
  onGetStarted: () => void
}

export default function LandingPage({ onGetStarted }: LandingPageProps) {
  return (
    <div className="landing-page">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-container">
          <div className="hero-content">
            <h1 className="hero-title">Automate meeting minutes. Fetch what matters.</h1>
            <p className="hero-subtitle">
              Agentic workflows that turn conversations into tasks, summaries, and action.
            </p>
            <div className="hero-cta">
              <button onClick={onGetStarted} className="btn btn-primary">
                Get started — Free
              </button>
              <button className="btn btn-secondary">See demo</button>
            </div>
          </div>
          <div className="hero-visual">
            <svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e5e5e5" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="400" height="400" fill="url(#grid)" />
              <circle cx="200" cy="200" r="120" fill="none" stroke="#000000" strokeWidth="2" />
              <circle cx="200" cy="200" r="80" fill="none" stroke="#000000" strokeWidth="1.5" />
              <circle cx="200" cy="200" r="40" fill="#000000" opacity="0.5" />
              <line x1="200" y1="80" x2="200" y2="320" stroke="#e5e5e5" strokeWidth="1" />
              <line x1="80" y1="200" x2="320" y2="200" stroke="#e5e5e5" strokeWidth="1" />
            </svg>
          </div>
        </div>
      </section>

      {/* Trust Section */}
      <section className="trust-section">
        <h3>Trusted by leading teams</h3>
        <div className="trust-logos">
          <div className="logo-item">Acme Corp</div>
          <div className="logo-item">TechFlow</div>
          <div className="logo-item">CloudBase</div>
          <div className="logo-item">DataSync</div>
          <div className="logo-item">NextGen AI</div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features">
        <div className="section-header">
          <h2>Powerful features for modern teams</h2>
          <p>Everything you need to capture, organize, and act on meeting insights.</p>
        </div>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">📝</div>
            <h3>Auto-Generated Minutes</h3>
            <p>
              Meetings are automatically transcribed and summarized with AI, capturing key points and action items
              instantly.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3>Smart Task Creation</h3>
            <p>
              Convert action items into tasks and assign them directly from meeting minutes. Keep your team aligned.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔍</div>
            <h3>Intelligent Fetch</h3>
            <p>Fetch related content by task or date range. Aggregated notes, documents, and context in one place.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Complete History</h3>
            <p>
              Searchable archive of all meeting minutes. Easy access to past decisions and action items whenever needed.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚙️</div>
            <h3>Seamless Integration</h3>
            <p>Works with your existing calendar and task management tools. No disruption to your workflow.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔐</div>
            <h3>Enterprise Security</h3>
            <p>Your data stays private and secure. Built with privacy-first architecture and compliance in mind.</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <h2>Ready to transform your meetings?</h2>
        <p>Start automating your workflow today. No credit card required.</p>
        <button onClick={onGetStarted} className="btn btn-primary btn-large">
          Get started — Free
        </button>
      </section>
    </div>
  )
}
