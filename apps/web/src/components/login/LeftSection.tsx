"use client";
import { useEffect, useRef } from "react";
import { createNoise3D } from "simplex-noise";

export default function LeftSection() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d")!;
    const noise = createNoise3D();
    let animationId: number;
    let nt = 0;

    
    const colors = [
      "#C9A84C", // gold
      "#E8C84A", // bright amber
      "#AE67C2", // deep gold
      "#F0D060", // warm yellow
      "#8B6914", // dark amber
    ];

    const resize = () => {
      canvas.width = container.offsetWidth;
      canvas.height = container.offsetHeight;
    };

    const drawWave = () => {
      const w = canvas.width;
      const h = canvas.height;

      ctx.fillStyle = "#1a1a1a";
      ctx.globalAlpha = 1;
      ctx.fillRect(0, 0, w, h);

      nt += 0.0015;

      for (let i = 0; i < 5; i++) {
        ctx.beginPath();
        ctx.lineWidth = 60;
        ctx.strokeStyle = colors[i % colors.length];
        ctx.globalAlpha = 0.45;

        for (let x = 0; x < w; x += 5) {
          const y = noise(x / 800, 0.3 * i, nt) * 120;
          ctx.lineTo(x, y + h * 0.5);
        }
        ctx.stroke();
        ctx.closePath();
      }

      animationId = requestAnimationFrame(drawWave);
    };

    resize();
    drawWave();

    const ro = new ResizeObserver(resize);
    ro.observe(container);

    return () => {
      cancelAnimationFrame(animationId);
      ro.disconnect();
    };
  }, []);

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden bg-[#1a1a1a]">
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full"
        style={{ filter: "blur(12px)" }}
      />

     
      <div className="absolute inset-0 z-10 flex flex-col justify-end px-12 pb-16">
      
        <div className="mb-6">
          

          <p className="text-[#C9A84C] text-xs font-semibold tracking-[0.2em] uppercase mb-3">
            RouteMinds
          </p>
          <h1 className="text-5xl font-bold text-white leading-tight mb-4">
            Stop Waiting.<br />
            <span className="text-[#C9A84C]">Start Predicting.</span>
          </h1>
          <p className="text-gray-400 text-base max-w-xs leading-relaxed">
            AI-powered traffic predictions for Delhi — plan smarter, arrive earlier.
          </p>
        </div>
      </div>
    </div>
  );
}