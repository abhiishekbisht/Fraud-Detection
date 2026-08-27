import React, { useEffect, useRef, useState } from 'react';
import { Eye, EyeOff, Activity } from 'lucide-react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  baseAlpha: number;
  color: string;
  isAnomaly: boolean;
  pulseOffset: number;
}

export const Background3D: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isEnabled, setIsEnabled] = useState(true);
  const mouseRef = useRef({ x: -1000, y: -1000 });

  useEffect(() => {
    if (!isEnabled) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Create particle network symbolizing financial nodes & transaction anomalies
    const particleCount = Math.min(Math.floor((width * height) / 18000), 70);
    const particles: Particle[] = [];

    const colors = [
      'rgba(14, 165, 233, ', // Cyan primary
      'rgba(99, 102, 241, ', // Indigo secondary
      'rgba(245, 158, 11, ', // Amber fraud alert
    ];

    for (let i = 0; i < particleCount; i++) {
      const isAnomaly = Math.random() < 0.08; // 8% anomaly nodes
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: isAnomaly ? Math.random() * 2.5 + 2 : Math.random() * 1.5 + 1,
        baseAlpha: Math.random() * 0.4 + 0.2,
        color: isAnomaly ? 'rgba(245, 158, 11, ' : colors[i % 2],
        isAnomaly,
        pulseOffset: Math.random() * Math.PI * 2,
      });
    }

    let time = 0;

    const render = () => {
      time += 0.02;
      ctx.clearRect(0, 0, width, height);

      // Radial background grid effect
      const gradient = ctx.createRadialGradient(
        width / 2,
        height / 3,
        0,
        width / 2,
        height / 2,
        Math.max(width, height)
      );
      gradient.addColorStop(0, 'rgba(14, 165, 233, 0.04)');
      gradient.addColorStop(0.5, 'rgba(15, 23, 42, 0.02)');
      gradient.addColorStop(1, 'rgba(7, 8, 12, 0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Render connecting node lines
      for (let i = 0; i < particles.length; i++) {
        const p1 = particles[i];

        // Move particle
        p1.x += p1.vx;
        p1.y += p1.vy;

        // Bounce from walls
        if (p1.x < 0 || p1.x > width) p1.vx *= -1;
        if (p1.y < 0 || p1.y > height) p1.vy *= -1;

        // Interactive mouse push
        const dxMouse = p1.x - mouseRef.current.x;
        const dyMouse = p1.y - mouseRef.current.y;
        const distMouse = Math.sqrt(dxMouse * dxMouse + dyMouse * dyMouse);
        if (distMouse < 120) {
          const force = (120 - distMouse) / 120;
          p1.x += (dxMouse / distMouse) * force * 1.5;
          p1.y += (dyMouse / distMouse) * force * 1.5;
        }

        // Draw connections
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 140) {
            const alpha = (1 - dist / 140) * 0.15;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            if (p1.isAnomaly || p2.isAnomaly) {
              ctx.strokeStyle = `rgba(245, 158, 11, ${alpha * 1.5})`;
              ctx.lineWidth = 1.2;
            } else {
              ctx.strokeStyle = `rgba(14, 165, 233, ${alpha})`;
              ctx.lineWidth = 0.8;
            }
            ctx.stroke();
          }
        }

        // Draw Node
        const pulse = Math.sin(time * 2 + p1.pulseOffset) * 0.2 + 0.8;
        const currentAlpha = p1.baseAlpha * pulse;

        ctx.beginPath();
        ctx.arc(p1.x, p1.y, p1.radius * (p1.isAnomaly ? pulse : 1), 0, Math.PI * 2);
        ctx.fillStyle = `${p1.color}${currentAlpha})`;
        ctx.fill();

        // Anomaly outer ring glow
        if (p1.isAnomaly) {
          ctx.beginPath();
          ctx.arc(p1.x, p1.y, p1.radius * 2.8 * pulse, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(245, 158, 11, ${currentAlpha * 0.3})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, [isEnabled]);

  return (
    <>
      {isEnabled && (
        <canvas
          ref={canvasRef}
          className="fixed inset-0 pointer-events-none z-0 transition-opacity duration-1000"
          style={{ opacity: 0.85 }}
        />
      )}
      <div className="fixed bottom-4 right-4 z-40">
        <button
          onClick={() => setIsEnabled(!isEnabled)}
          title={isEnabled ? 'Disable 3D Node Mesh' : 'Enable 3D Node Mesh'}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-mono bg-slate-900/80 border border-slate-800 text-slate-400 hover:text-sky-400 hover:border-sky-500/50 backdrop-blur-md transition-all shadow-lg"
        >
          <Activity className="w-3.5 h-3.5 text-sky-400 animate-pulse" />
          <span>{isEnabled ? '3D Mesh Active' : '3D Mesh Paused'}</span>
          {isEnabled ? <Eye className="w-3 h-3 ml-1" /> : <EyeOff className="w-3 h-3 ml-1 text-slate-500" />}
        </button>
      </div>
    </>
  );
};
