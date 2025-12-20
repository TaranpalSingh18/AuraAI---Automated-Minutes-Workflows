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
              <a href="/products">Features</a>
            </li>
            <li>
              <a href="/">Pricing</a>
            </li>
            <li>
              <a href="/">Docs</a>
            </li>
          </ul>
        </div>
        <div className="footer-section">
          <h4>Company</h4>
          <ul>
            <li>
              <a href="/about">About</a>
            </li>
            <li>
              <a href="/">Blog</a>
            </li>
            <li>
              <a href="/">Contact</a>
            </li>
          </ul>
        </div>
        <div className="footer-section">
          <h4>Legal</h4>
          <ul>
            <li>
              <a href="/">Privacy</a>
            </li>
            <li>
              <a href="/">Terms</a>
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
