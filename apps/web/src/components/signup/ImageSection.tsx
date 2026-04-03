import { useEffect, useRef } from "react"

const getWaveNoise = (x: number, y: number, z: number) => {
  return (
    Math.sin(x * 2.2 + z * 0.9 + y * 1.7) * 0.5 +
    Math.sin(x * 0.8 - z * 1.3 + y * 2.4) * 0.3 +
    Math.cos(x * 1.5 + z * 0.7 - y * 1.1) * 0.2
  )
}

export default function ImageSection() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    const ctx = canvas.getContext("2d")!
    let animationId: number
    let nt = 0

    // Matched to landing page: amber/gold + warm dark tones
    const colors = [
      "#C9A84C", // gold
      "#E8C84A", // bright amber
      "#A67C2E", // deep gold
      "#F0D060", // warm yellow
      "#8B6914", // dark amber
    ]

    const resize = () => {
      canvas.width = container.offsetWidth
      canvas.height = container.offsetHeight
    }

    const drawWave = () => {
      const w = canvas.width
      const h = canvas.height

      ctx.fillStyle = "#1a1a1a"
      ctx.globalAlpha = 1
      ctx.fillRect(0, 0, w, h)

      nt += 0.0015

      for (let i = 0; i < 5; i++) {
        ctx.beginPath()
        ctx.lineWidth = 60
        ctx.strokeStyle = colors[i % colors.length]
        ctx.globalAlpha = 0.45

        for (let x = 0; x < w; x += 5) {
          const y = getWaveNoise(x / 800, 0.3 * i, nt) * 120
          if (x === 0) {
            ctx.moveTo(x, y + h * 0.5)
            continue
          }

          ctx.lineTo(x, y + h * 0.5)
        }
        ctx.stroke()
        ctx.closePath()
      }

      animationId = requestAnimationFrame(drawWave)
    }

    resize()
    drawWave()

    const ro = new ResizeObserver(resize)
    ro.observe(container)

    return () => {
      cancelAnimationFrame(animationId)
      ro.disconnect()
    }
  }, [])

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full overflow-hidden bg-[#1a1a1a]"
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 h-full w-full"
        style={{ filter: "blur(12px)" }}
      />

      {/* Overlay content */}
      <div className="absolute inset-0 z-10 flex flex-col justify-end px-12 pb-16">
        {/* Logo mark */}
        <div className="mb-6">
          <p className="mb-3 text-xs font-semibold tracking-[0.2em] text-[#C9A84C] uppercase">
            RouteMinds
          </p>
          <h1 className="mb-4 text-5xl leading-tight font-bold text-white">
            Stop Waiting.
            <br />
            <span className="text-[#C9A84C]">Start Predicting.</span>
          </h1>
          <p className="max-w-xs text-base leading-relaxed text-gray-400">
            AI-powered traffic predictions for Delhi — plan smarter, arrive
            earlier.
          </p>
        </div>
      </div>
    </div>
  )
}
