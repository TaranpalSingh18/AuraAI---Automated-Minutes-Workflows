import { useRef, useState, useEffect } from "react"
import "./MacbookScroll.css"

const AuraAIScreen = () => {
  const [displayedText, setDisplayedText] = useState("")
  const [isTyping, setIsTyping] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  
  const fullText = "Please fetch my latest deadlines from my Trello Board"

  useEffect(() => {
    if (isTyping) {
      let currentIndex = 0
      const typingInterval = setInterval(() => {
        if (currentIndex < fullText.length) {
          setDisplayedText(fullText.slice(0, currentIndex + 1))
          currentIndex++
        } else {
          setIsTyping(false)
          setIsLoading(true)
          clearInterval(typingInterval)
          
          // After 4 seconds of loading, show success message
          setTimeout(() => {
            setIsLoading(false)
            setShowSuccess(true)
          }, 4000)
        }
      }, 50) // Typing speed - 50ms per character

      return () => clearInterval(typingInterval)
    }
  }, [isTyping, fullText])

  return (
    <div style={{ height: "100%", width: "100%", display: "flex", flexDirection: "column", backgroundColor: "#ffffff" }}>
      {/* Navbar */}
      <div style={{ 
        width: "100%", 
        background: "#000000", 
        padding: "10px 16px", 
        display: "flex", 
        alignItems: "center", 
        justifyContent: "space-between",
        borderBottom: "1px solid #374151"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div style={{ 
            width: "24px", 
            height: "24px", 
            borderRadius: "4px", 
            backgroundColor: "#ffffff", 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "center" 
          }}>
            <span style={{ color: "#000000", fontSize: "12px", fontWeight: "bold" }}>A</span>
          </div>
          <span style={{ color: "#ffffff", fontWeight: "600", fontSize: "14px" }}>Aura AI</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#6b7280" }}></div>
          <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#6b7280" }}></div>
          <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#6b7280" }}></div>
        </div>
      </div>

      {/* Chat Area */}
      <div style={{ 
        flex: 1, 
        overflowY: "auto", 
        padding: "12px 16px", 
        display: "flex", 
        flexDirection: "column", 
        gap: "16px",
        backgroundColor: "#ffffff",
        justifyContent: "flex-start"
      }}>
        {/* User message with typewriter effect */}
        <div style={{
          display: "flex",
          alignItems: "flex-start",
          gap: "12px",
          justifyContent: "flex-end",
        }}>
          <div
            style={{
              maxWidth: "75%",
              borderRadius: "8px",
              padding: "8px 12px",
              fontSize: "12px",
              backgroundColor: "#1f2937",
              color: "#ffffff",
            }}
          >
            {displayedText}
            {isTyping && (
              <span style={{
                display: "inline-block",
                width: "2px",
                height: "12px",
                backgroundColor: "#ffffff",
                marginLeft: "2px",
                animation: "blink 1s infinite"
              }}></span>
            )}
          </div>
          <div style={{
            width: "24px",
            height: "24px",
            borderRadius: "50%",
            backgroundColor: "#6b7280",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            marginTop: "2px"
          }}>
            <span style={{ color: "#ffffff", fontSize: "12px" }}>U</span>
          </div>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", justifyContent: "flex-start" }}>
            <div style={{
              width: "24px",
              height: "24px",
              borderRadius: "50%",
              backgroundColor: "#000000",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              marginTop: "2px"
            }}>
              <span style={{ color: "#ffffff", fontSize: "12px", fontWeight: "bold" }}>A</span>
            </div>
            <div style={{
              backgroundColor: "#f3f4f6",
              border: "1px solid #e5e7eb",
              borderRadius: "8px",
              padding: "8px 12px"
            }}>
              <div style={{ display: "flex", gap: "4px" }}>
                <div style={{
                  width: "6px",
                  height: "6px",
                  backgroundColor: "#6b7280",
                  borderRadius: "50%",
                  animation: "bounce 1.4s infinite",
                  animationDelay: "0ms"
                }}></div>
                <div style={{
                  width: "6px",
                  height: "6px",
                  backgroundColor: "#6b7280",
                  borderRadius: "50%",
                  animation: "bounce 1.4s infinite",
                  animationDelay: "150ms"
                }}></div>
                <div style={{
                  width: "6px",
                  height: "6px",
                  backgroundColor: "#6b7280",
                  borderRadius: "50%",
                  animation: "bounce 1.4s infinite",
                  animationDelay: "300ms"
                }}></div>
              </div>
            </div>
          </div>
        )}

        {/* Success message */}
        {showSuccess && (
          <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", justifyContent: "flex-start" }}>
            <div style={{
              width: "24px",
              height: "24px",
              borderRadius: "50%",
              backgroundColor: "#000000",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              marginTop: "2px"
            }}>
              <span style={{ color: "#ffffff", fontSize: "12px", fontWeight: "bold" }}>A</span>
            </div>
            <div style={{
              maxWidth: "75%",
              borderRadius: "8px",
              padding: "8px 12px",
              fontSize: "12px",
              backgroundColor: "#f3f4f6",
              color: "#000000",
              border: "1px solid #e5e7eb",
            }}>
              Workflow Triggered Successfully
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div style={{ borderTop: "1px solid #e5e7eb", padding: "12px", backgroundColor: "#ffffff" }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          backgroundColor: "#f3f4f6",
          borderRadius: "8px",
          padding: "8px 12px",
          border: "1px solid #e5e7eb"
        }}>
          <input
            type="text"
            placeholder="Message Aura AI..."
            style={{
              flex: 1,
              backgroundColor: "transparent",
              fontSize: "12px",
              color: "#000000",
              outline: "none",
              border: "none"
            }}
            readOnly
          />
          <button style={{
            width: "20px",
            height: "20px",
            borderRadius: "4px",
            backgroundColor: "#000000",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "none",
            cursor: "pointer"
          }}>
            <svg
              style={{ width: "12px", height: "12px", color: "white" }}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default function MacbookScroll() {
  const containerRef = useRef(null)

  return (
    <div ref={containerRef} className="macbook-scroll-container">
      <div className="macbook-wrapper">
        {/* MacBook Frame */}
        <div className="macbook-frame">
          {/* Screen */}
          <div className="macbook-screen">
            <div className="macbook-screen-inner">
              {/* Notch */}
              <div className="macbook-notch"></div>
              
              {/* Screen Content */}
              <div className="macbook-content">
                <div className="macbook-scroll-content">
                  <AuraAIScreen />
                </div>
              </div>
            </div>
          </div>
          
          {/* Base */}
          <div className="macbook-base">
            <div className="macbook-keyboard">
              {/* Top Row - Function Keys */}
              <div className="keyboard-row">
                <div className="key">esc</div>
                <div className="key">F1</div>
                <div className="key">F2</div>
                <div className="key">F3</div>
                <div className="key">F4</div>
                <div className="key">F5</div>
                <div className="key">F6</div>
                <div className="key">F7</div>
                <div className="key">F8</div>
                <div className="key">F9</div>
                <div className="key">F10</div>
                <div className="key">F11</div>
                <div className="key">F12</div>
              </div>
              {/* Number Row */}
              <div className="keyboard-row">
                <div className="key">`</div>
                <div className="key">1</div>
                <div className="key">2</div>
                <div className="key">3</div>
                <div className="key">4</div>
                <div className="key">5</div>
                <div className="key">6</div>
                <div className="key">7</div>
                <div className="key">8</div>
                <div className="key">9</div>
                <div className="key">0</div>
                <div className="key">-</div>
                <div className="key">=</div>
                <div className="key wide">delete</div>
              </div>
              {/* Q Row */}
              <div className="keyboard-row">
                <div className="key wide">tab</div>
                <div className="key">Q</div>
                <div className="key">W</div>
                <div className="key">E</div>
                <div className="key">R</div>
                <div className="key">T</div>
                <div className="key">Y</div>
                <div className="key">U</div>
                <div className="key">I</div>
                <div className="key">O</div>
                <div className="key">P</div>
                <div className="key">[</div>
                <div className="key">]</div>
                <div className="key">\</div>
              </div>
              {/* A Row */}
              <div className="keyboard-row">
                <div className="key wide">caps</div>
                <div className="key">A</div>
                <div className="key">S</div>
                <div className="key">D</div>
                <div className="key">F</div>
                <div className="key">G</div>
                <div className="key">H</div>
                <div className="key">J</div>
                <div className="key">K</div>
                <div className="key">L</div>
                <div className="key">;</div>
                <div className="key">'</div>
                <div className="key wide">return</div>
              </div>
              {/* Z Row */}
              <div className="keyboard-row">
                <div className="key wide">shift</div>
                <div className="key">Z</div>
                <div className="key">X</div>
                <div className="key">C</div>
                <div className="key">V</div>
                <div className="key">B</div>
                <div className="key">N</div>
                <div className="key">M</div>
                <div className="key">,</div>
                <div className="key">.</div>
                <div className="key">/</div>
                <div className="key wide">shift</div>
              </div>
              {/* Bottom Row */}
              <div className="keyboard-row">
                <div className="key">fn</div>
                <div className="key">control</div>
                <div className="key">option</div>
                <div className="key">⌘</div>
                <div className="key space">space</div>
                <div className="key">⌘</div>
                <div className="key">option</div>
                <div className="key">←</div>
                <div className="key">↓</div>
                <div className="key">→</div>
              </div>
            </div>
            <div className="macbook-trackpad"></div>
          </div>
        </div>
      </div>
    </div>
  )
}



