import { useEffect, useState } from "react"
import { motion, useMotionValue, useSpring } from "motion/react"
import "./AuraPointer.css"

export default function AuraPointer() {
  const [isVisible, setIsVisible] = useState(false)
  const [isHovering, setIsHovering] = useState(false)
  const cursorX = useMotionValue(-100)
  const cursorY = useMotionValue(-100)

  const springConfig = { damping: 25, stiffness: 700 }
  const cursorXSpring = useSpring(cursorX, springConfig)
  const cursorYSpring = useSpring(cursorY, springConfig)

  useEffect(() => {
    const moveCursor = (e) => {
      cursorX.set(e.clientX - 10)
      cursorY.set(e.clientY - 10)
      if (!isVisible) setIsVisible(true)

      // Check if hovering over interactive elements
      const target = e.target
      const isInteractive =
        target.tagName === "A" ||
        target.tagName === "BUTTON" ||
        target.closest("button") ||
        target.closest("a") ||
        target.closest(".btn") ||
        target.closest("[role='button']") ||
        target.closest("input[type='submit']") ||
        target.closest("input[type='button']") ||
        target.closest("select") ||
        target.style.cursor === "pointer" ||
        window.getComputedStyle(target).cursor === "pointer"

      setIsHovering(isInteractive)
    }

    const handleMouseLeave = () => {
      setIsVisible(false)
      setIsHovering(false)
    }

    const handleMouseEnter = () => {
      setIsVisible(true)
    }

    window.addEventListener("mousemove", moveCursor)
    document.addEventListener("mouseleave", handleMouseLeave)
    document.addEventListener("mouseenter", handleMouseEnter)

    return () => {
      window.removeEventListener("mousemove", moveCursor)
      document.removeEventListener("mouseleave", handleMouseLeave)
      document.removeEventListener("mouseenter", handleMouseEnter)
    }
  }, [cursorX, cursorY, isVisible])

  return (
    <motion.div
      className={`aura-pointer ${isHovering ? "aura-pointer-hover" : ""}`}
      style={{
        translateX: cursorXSpring,
        translateY: cursorYSpring,
        opacity: isVisible ? 1 : 0,
      }}
    >
      <div className="aura-pointer-dot"></div>
      <div className="aura-pointer-ring"></div>
    </motion.div>
  )
}

