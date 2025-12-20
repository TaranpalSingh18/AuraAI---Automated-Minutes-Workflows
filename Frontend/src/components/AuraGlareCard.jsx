import { useRef } from "react"
import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import "./AuraGlareCard.css"

function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export const AuraGlareCard = ({
  children,
  className,
  title,
  description,
}) => {
  const isPointerInside = useRef(false)
  const refElement = useRef(null)
  const state = useRef({
    glare: {
      x: 50,
      y: 50,
    },
    background: {
      x: 50,
      y: 50,
    },
    rotate: {
      x: 0,
      y: 0,
    },
  })

  const containerStyle = {
    "--m-x": "50%",
    "--m-y": "50%",
    "--r-x": "0deg",
    "--r-y": "0deg",
    "--bg-x": "50%",
    "--bg-y": "50%",
    "--duration": "300ms",
    "--opacity": "0",
    "--radius": "16px",
    "--easing": "ease",
    "--transition": "var(--duration) var(--easing)",
  }

  const backgroundStyle = {
    "--shade":
      "radial-gradient( farthest-corner circle at var(--m-x) var(--m-y),rgba(255,255,255,0.15) 12%,rgba(255,255,255,0.1) 20%,rgba(255,255,255,0.05) 120% ) var(--bg-x) var(--bg-y)/300% no-repeat",
  }

  const updateStyles = () => {
    if (refElement.current) {
      const { background, rotate, glare } = state.current
      refElement.current?.style.setProperty("--m-x", `${glare.x}%`)
      refElement.current?.style.setProperty("--m-y", `${glare.y}%`)
      refElement.current?.style.setProperty("--r-x", `${rotate.x}deg`)
      refElement.current?.style.setProperty("--r-y", `${rotate.y}deg`)
      refElement.current?.style.setProperty("--bg-x", `${background.x}%`)
      refElement.current?.style.setProperty("--bg-y", `${background.y}%`)
    }
  }

  return (
    <div
      style={containerStyle}
      className="aura-glare-card-container"
      ref={refElement}
      onPointerMove={(event) => {
        const rotateFactor = 0.3
        const rect = event.currentTarget.getBoundingClientRect()
        const position = {
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
        }
        const percentage = {
          x: (100 / rect.width) * position.x,
          y: (100 / rect.height) * position.y,
        }
        const delta = {
          x: percentage.x - 50,
          y: percentage.y - 50,
        }

        const { background, rotate, glare } = state.current
        background.x = 50 + percentage.x / 4 - 12.5
        background.y = 50 + percentage.y / 3 - 16.67
        rotate.x = -(delta.x / 3.5)
        rotate.y = delta.y / 2
        rotate.x *= rotateFactor
        rotate.y *= rotateFactor
        glare.x = percentage.x
        glare.y = percentage.y

        updateStyles()
      }}
      onPointerEnter={() => {
        isPointerInside.current = true
        if (refElement.current) {
          setTimeout(() => {
            if (isPointerInside.current) {
              refElement.current?.style.setProperty("--duration", "0s")
            }
          }, 300)
        }
      }}
      onPointerLeave={() => {
        isPointerInside.current = false
        if (refElement.current) {
          refElement.current.style.removeProperty("--duration")
          refElement.current?.style.setProperty("--r-x", `0deg`)
          refElement.current?.style.setProperty("--r-y", `0deg`)
        }
      }}
    >
      <div className="aura-glare-card-inner">
        <div className="aura-glare-card-content">
          <div className={cn("aura-glare-card-bg", className)}>
            {title && <h3 className="aura-glare-card-title">{title}</h3>}
            {description && <p className="aura-glare-card-description">{description}</p>}
            {children}
          </div>
        </div>
        <div className="aura-glare-card-shine" />
        <div
          className="aura-glare-card-background"
          style={{ ...backgroundStyle }}
        />
      </div>
    </div>
  )
}

