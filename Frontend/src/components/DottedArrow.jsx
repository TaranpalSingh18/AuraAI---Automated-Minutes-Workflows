import { forwardRef, useRef, useEffect, useImperativeHandle } from "react"
import { gsap } from "gsap"
import "./DottedArrow.css"

export const DottedArrow = forwardRef(({ 
  direction = "horizontal",
  delay = 0 
}, ref) => {
  const arrowRef = useRef(null)
  const pathRef = useRef(null)

  useImperativeHandle(ref, () => ({
    element: arrowRef.current
  }))

  useEffect(() => {
    if (arrowRef.current && pathRef.current) {
      // Set initial state - hidden
      gsap.set(arrowRef.current, { opacity: 0, scale: 0 })
      
      // Animate arrow appearing
      const tl = gsap.timeline({ delay: delay })
      tl.to(arrowRef.current, {
        opacity: 1,
        scale: 1,
        duration: 0.5,
        ease: "power2.out"
      })

      // Animate path drawing
      const pathLength = pathRef.current.getTotalLength()
      gsap.set(pathRef.current, {
        strokeDasharray: pathLength,
        strokeDashoffset: pathLength
      })
      
      tl.to(pathRef.current, {
        strokeDashoffset: 0,
        duration: 0.8,
        ease: "power2.inOut"
      }, "-=0.3")
      
      // Show arrow head after path is drawn
      const arrowHead = arrowRef.current.querySelector('.dotted-arrow-head')
      if (arrowHead) {
        tl.to(arrowHead, {
          opacity: 1,
          duration: 0.3,
          ease: "power2.out"
        }, "-=0.2")
      }
    }
  }, [delay])

  const getPath = () => {
    if (direction === "left") {
      // Arrow pointing left (from MacBook to card)
      return "M 200 50 L 20 50"
    } else if (direction === "right") {
      // Arrow pointing right (from MacBook to card)
      return "M 0 50 L 180 50"
    } else if (direction === "up") {
      // Arrow pointing up
      return "M 50 100 L 50 20"
    } else if (direction === "down") {
      // Arrow pointing down
      return "M 50 0 L 50 80"
    }
    return "M 0 50 L 200 50"
  }

  const getArrowHead = () => {
    if (direction === "left") {
      // Arrow head at the end (pointing to card)
      return "M 20 50 L 5 40 M 20 50 L 5 60"
    } else if (direction === "right") {
      // Arrow head at the end (pointing to card)
      return "M 180 50 L 195 40 M 180 50 L 195 60"
    } else if (direction === "up") {
      return "M 50 20 L 45 10 M 50 20 L 55 10"
    } else if (direction === "down") {
      return "M 50 80 L 45 90 M 50 80 L 55 90"
    }
    return "M 180 50 L 195 40 M 180 50 L 195 60"
  }

  return (
    <div 
      ref={arrowRef} 
      className={`dotted-arrow dotted-arrow-${direction}`}
    >
      <svg 
        width="100%" 
        height="100%" 
        viewBox="0 0 200 100" 
        preserveAspectRatio="none"
        className="dotted-arrow-svg"
      >
        <path
          ref={pathRef}
          d={getPath()}
          fill="none"
          stroke="#ffffff"
          strokeWidth="15"
          strokeDasharray="8 8"
          className="dotted-arrow-path"
        />
        <path
          d={getArrowHead()}
          fill="none"
          stroke="#ffffff"
          strokeWidth="15"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="dotted-arrow-head"
        />
      </svg>
    </div>
  )
})

DottedArrow.displayName = "DottedArrow"

