"use client"
import "../styles/ProductsPage.css"

export default function ProductsPage() {
  return (
    <div className="products-page">
      <section className="products-hero">
        <div className="products-container">
          <h1>Powerful Features</h1>
          <p>Everything you need to automate meeting workflows and turn conversations into action.</p>
        </div>
      </section>

      <section className="products-content">
        <div className="products-container">
          <div className="feature-section">
            <div className="feature-row">
              <div className="feature-text">
                <h2>Meeting Intelligence</h2>
                <p>
                  Transcription, summarization, and action item extraction all happen automatically. No manual effort
                  required.
                </p>
                <ul className="feature-list">
                  <li>Real-time transcription</li>
                  <li>AI-powered summaries</li>
                  <li>Automatic action item extraction</li>
                  <li>Speaker identification</li>
                </ul>
              </div>
              <div className="feature-visual">
                <div className="visual-box"></div>
              </div>
            </div>
          </div>

          <div className="feature-section">
            <div className="feature-row reverse">
              <div className="feature-text">
                <h2>Smart Task Management</h2>
                <p>
                  Convert action items to tasks instantly. Assign, track, and collaborate without leaving the platform.
                </p>
                <ul className="feature-list">
                  <li>One-click task creation</li>
                  <li>Intelligent assignment</li>
                  <li>Progress tracking</li>
                  <li>Team collaboration</li>
                </ul>
              </div>
              <div className="feature-visual">
                <div className="visual-box"></div>
              </div>
            </div>
          </div>

          <div className="feature-section">
            <div className="feature-row">
              <div className="feature-text">
                <h2>Content Fetch & Search</h2>
                <p>
                  Intelligently retrieve related documents, notes, and context. Everything you need is just a few clicks
                  away.
                </p>
                <ul className="feature-list">
                  <li>Semantic search</li>
                  <li>Related content discovery</li>
                  <li>Historical context</li>
                  <li>Fast retrieval</li>
                </ul>
              </div>
              <div className="feature-visual">
                <div className="visual-box"></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="pricing-preview">
        <div className="products-container">
          <h2 style={{ textAlign: "center", marginBottom: "var(--space-10)" }}>Simple Pricing</h2>
          <div className="pricing-grid">
            <div className="pricing-card">
              <h3>Starter</h3>
              <div className="price">
                $0<span>/month</span>
              </div>
              <p>Perfect for individuals</p>
              <ul>
                <li>5 meetings/month</li>
                <li>Basic summaries</li>
                <li>Task management</li>
              </ul>
            </div>
            <div className="pricing-card featured">
              <span className="badge">Popular</span>
              <h3>Pro</h3>
              <div className="price">
                $29<span>/month</span>
              </div>
              <p>For teams</p>
              <ul>
                <li>Unlimited meetings</li>
                <li>Advanced AI features</li>
                <li>Team collaboration</li>
                <li>Priority support</li>
              </ul>
            </div>
            <div className="pricing-card">
              <h3>Enterprise</h3>
              <div className="price">Custom</div>
              <p>For large organizations</p>
              <ul>
                <li>Custom integration</li>
                <li>Dedicated support</li>
                <li>SLA guarantee</li>
                <li>Advanced security</li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
