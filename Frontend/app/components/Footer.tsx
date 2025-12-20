"use client"
import "./Footer.css"

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-section">
          <h4>AuraAI</h4>
          <p>Automate meeting minutes. Turn conversations into action.</p>
        </div>
        <div className="footer-section">
          <h4>Product</h4>
          <ul>
            <li>
              <a href="#features">Features</a>
            </li>
            <li>
              <a href="#pricing">Pricing</a>
            </li>
            <li>
              <a href="#docs">Docs</a>
            </li>
          </ul>
        </div>
        <div className="footer-section">
          <h4>Company</h4>
          <ul>
            <li>
              <a href="#about">About</a>
            </li>
            <li>
              <a href="#blog">Blog</a>
            </li>
            <li>
              <a href="#contact">Contact</a>
            </li>
          </ul>
        </div>
        <div className="footer-section">
          <h4>Legal</h4>
          <ul>
            <li>
              <a href="#privacy">Privacy</a>
            </li>
            <li>
              <a href="#terms">Terms</a>
            </li>
          </ul>
        </div>
      </div>
      <div className="footer-bottom">
        <p>&copy; 2025 AuraAI. All rights reserved.</p>
      </div>
    </footer>
  )
}
