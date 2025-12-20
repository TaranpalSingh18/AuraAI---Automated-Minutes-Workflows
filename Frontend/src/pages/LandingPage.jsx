import { Link } from "react-router-dom"
import { useRef, useEffect, useState } from "react"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"
import MacbookScroll from "../components/MacbookScroll"
import { BackgroundLines } from "../components/ui/background-lines"
import { AuraGlareCard } from "../components/AuraGlareCard"
import { DottedArrow } from "../components/DottedArrow"
import "./LandingPage.css"

gsap.registerPlugin(ScrollTrigger)

export default function LandingPage() {
  const landingPageRef = useRef(null)
  const macbookTriggerRef = useRef(null)
  const macbookWrapperRef = useRef(null)
  const [shouldLoadMacbook, setShouldLoadMacbook] = useState(false)
  
  // Refs for cards and arrows
  const card1Ref = useRef(null)
  const card2Ref = useRef(null)
  const card3Ref = useRef(null)
  const card4Ref = useRef(null)
  const arrow1Ref = useRef(null)
  const arrow2Ref = useRef(null)
  const arrow3Ref = useRef(null)
  const arrow4Ref = useRef(null)

  useEffect(() => {
    // Set up scroll trigger for Macbook component
    const trigger = ScrollTrigger.create({
      trigger: macbookTriggerRef.current,
      start: "top 80%", // Trigger when the element is 80% from the top of viewport
      onEnter: () => {
        setShouldLoadMacbook(true)
      },
      once: true // Only trigger once
    })

    return () => {
      trigger.kill()
    }
  }, [])

  useEffect(() => {
    if (shouldLoadMacbook && macbookWrapperRef.current) {
      // Create timeline for sequential loading
      const tl = gsap.timeline()
      
      // Step 1: Animate MacBook
      tl.fromTo(
        macbookWrapperRef.current,
        {
          opacity: 0,
          y: 50,
          scale: 0.95
        },
        {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 1,
          ease: "power3.out"
        }
      )
      
      // Wait for MacBook workflow to complete (~6.5 seconds: typing ~2.5s + loading 4s)
      // Then start card sequence
      const workflowCompleteTime = 7.0
      
      // Step 2: Arrow 1 appears, then Card 1
      if (card1Ref.current) {
        tl.fromTo(
          card1Ref.current,
          { opacity: 0, y: 30, scale: 0.9 },
          { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "power3.out" },
          workflowCompleteTime + 0.8 // After workflow + arrow animation
        )
      }
      
      // Step 3: Arrow 2 appears, then Card 2
      if (card2Ref.current) {
        tl.fromTo(
          card2Ref.current,
          { opacity: 0, y: 30, scale: 0.9 },
          { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "power3.out" },
          workflowCompleteTime + 2.0 // After previous card + arrow
        )
      }
      
      // Step 4: Arrow 3 appears, then Card 3
      if (card3Ref.current) {
        tl.fromTo(
          card3Ref.current,
          { opacity: 0, y: 30, scale: 0.9 },
          { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "power3.out" },
          workflowCompleteTime + 3.2 // After previous card + arrow
        )
      }
      
      // Step 5: Arrow 4 appears, then Card 4
      if (card4Ref.current) {
        tl.fromTo(
          card4Ref.current,
          { opacity: 0, y: 30, scale: 0.9 },
          { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "power3.out" },
          workflowCompleteTime + 4.4 // After previous card + arrow
        )
      }
    }
  }, [shouldLoadMacbook])

  return (
    <div className="landing-page" ref={landingPageRef}>
      {/* Hero Section */}
      <section className="hero">
        <BackgroundLines>
          <div className="hero-container">
            <div className="hero-content">
              <h1 className="hero-title ">Automate meeting minutes. Fetch what matters.</h1>
              <p className="hero-subtitle">
                Agentic workflows that turn conversations into tasks, summaries, and action.
              </p>
              <div className="hero-cta">
                <Link to="/signup" className="btn btn-primary">
                  Get started — Free
                </Link>
                <button className="btn btn-secondary">See demo</button>
              </div>
            </div>
          </div>
        </BackgroundLines>
      </section>

      {/* Scroll Trigger Element */}
      <div ref={macbookTriggerRef} className="macbook-trigger"></div>

      {/* MacBook Section with Glare Cards */}
      {shouldLoadMacbook && (
        <section className="macbook-showcase-section">
          <div className="macbook-showcase-container">
            {/* Left Side Cards */}
            <div className="macbook-showcase-left">
              <div className="card-wrapper" ref={card1Ref}>
                <DottedArrow 
                  ref={arrow1Ref}
                  direction="left"
                  delay={7.2}
                />
                <AuraGlareCard
                  title="AI-Powered Transcription"
                  description="Automatically transcribe and summarize meetings with advanced AI, capturing every important detail and decision."
                />
              </div>
              <div className="card-wrapper" ref={card2Ref}>
                <DottedArrow 
                  ref={arrow2Ref}
                  direction="left"
                  delay={8.4}
                />
                <AuraGlareCard
                  title="Smart Task Extraction"
                  description="Intelligently identify and convert action items into trackable tasks, ensuring nothing falls through the cracks."
                />
              </div>
            </div>

            {/* Center Mac Component */}
            <div ref={macbookWrapperRef} className="macbook-wrapper-animated">
              <MacbookScroll />
            </div>

            {/* Right Side Cards */}
            <div className="macbook-showcase-right">
              <div className="card-wrapper" ref={card3Ref}>
                <DottedArrow 
                  ref={arrow3Ref}
                  direction="right"
                  delay={9.6}
                />
                <AuraGlareCard
                  title="Context-Aware Fetch"
                  description="Retrieve related content by task, date, or topic. Get all relevant meeting notes and documents in one place."
                />
              </div>
              <div className="card-wrapper" ref={card4Ref}>
                <DottedArrow 
                  ref={arrow4Ref}
                  direction="right"
                  delay={10.8}
                />
                <AuraGlareCard
                  title="Seamless Integration"
                  description="Connect with your existing tools and workflows. Works with calendars, task managers, and collaboration platforms."
                />
              </div>
            </div>
          </div>
        </section>
      )}

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
        <Link to="/signup" className="btn btn-primary btn-large">
          Get started — Free
        </Link>
      </section>
    </div>
  )
}
