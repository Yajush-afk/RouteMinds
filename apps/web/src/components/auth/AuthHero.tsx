import { useEffect, useRef } from "react"

const getWaveNoise = (x: number, y: number, z: number) => {
  return (
    Math.sin(x * 2.2 + z * 0.9 + y * 1.7) * 0.5 +
    Math.sin(x * 0.8 - z * 1.3 + y * 2.4) * 0.3 +
    Math.cos(x * 1.5 + z * 0.7 - y * 1.1) * 0.2
  )
}

export default function AuthHero() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current

    if (!canvas || !container) {
      return
    }

    const context = canvas.getContext("2d")

    if (!context) {
      return
    }

    let animationFrame = 0
    let noiseTime = 0

    const colors = ["#C9A84C", "#E8C84A", "#A67C2E", "#F0D060", "#8B6914"]

    const resize = () => {
      canvas.width = container.offsetWidth
      canvas.height = container.offsetHeight
    }

    const draw = () => {
      const width = canvas.width
      const height = canvas.height

      context.fillStyle = "#161512"
      context.globalAlpha = 1
      context.fillRect(0, 0, width, height)

      noiseTime += 0.0015

      for (let waveIndex = 0; waveIndex < 5; waveIndex += 1) {
        context.beginPath()
        context.lineWidth = 60
        context.strokeStyle = colors[waveIndex % colors.length]
        context.globalAlpha = 0.45

        for (let x = 0; x < width; x += 5) {
          const y = getWaveNoise(x / 800, 0.3 * waveIndex, noiseTime) * 120

          if (x === 0) {
            context.moveTo(x, y + height * 0.5)
          } else {
            context.lineTo(x, y + height * 0.5)
          }
        }

        context.stroke()
        context.closePath()
      }

      animationFrame = requestAnimationFrame(draw)
    }

    resize()
    draw()

    const observer = new ResizeObserver(resize)
    observer.observe(container)

    return () => {
      cancelAnimationFrame(animationFrame)
      observer.disconnect()
    }
  }, [])

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full overflow-hidden bg-[#161512]"
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 h-full w-full"
        style={{ filter: "blur(12px)" }}
      />

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(240,208,96,0.16),transparent_32%),linear-gradient(180deg,rgba(10,10,10,0.16),rgba(10,10,10,0.58))]" />

      <div className="absolute inset-0 z-10 flex flex-col justify-end px-8 py-8 sm:px-10 sm:py-10 lg:px-12 lg:py-14">
        <div className="max-w-xl">
          <p className="mb-5 text-xs font-semibold tracking-[0.26em] text-[#cfb35e] uppercase">
            Delhi Transit Intelligence
          </p>
          <h1 className="max-w-lg text-4xl leading-[1.02] font-semibold tracking-tight text-white sm:text-5xl lg:text-6xl">
            One step in.
            <br />
            <span className="text-[#e8c84a]">Phone, email, and done.</span>
          </h1>
          <p className="mt-6 max-w-md text-sm leading-7 text-[#d5d0c3] sm:text-base">
            Use a one-time code to get into RouteMinds faster. No passwords,
            no split between signing up and signing in, just one Delhi-ready
            entry flow.
          </p>
        </div>
      </div>
    </div>
  )
}
