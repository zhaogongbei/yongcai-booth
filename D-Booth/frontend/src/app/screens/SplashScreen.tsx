import { useState, useEffect } from "react";
import { Camera, Sparkles } from "lucide-react";
import { motion } from "motion/react";

export function SplashScreen({ onDone }: { onDone: () => void }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setProgress(p => {
      if (p >= 100) { clearInterval(t); setTimeout(onDone, 400); return 100; }
      return p + 2;
    }), 40);
    return () => clearInterval(t);
  }, [onDone]);

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center overflow-hidden" style={{ background: "#050816" }}>
      {/* Animated nebula background */}
      <div className="absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full"
          style={{ background: "radial-gradient(ellipse, rgba(139,92,246,0.18) 0%, rgba(59,130,246,0.08) 50%, transparent 70%)" }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] rounded-full"
          style={{ background: "radial-gradient(ellipse at 30% 50%, rgba(236,72,153,0.15) 0%, transparent 60%)" }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] rounded-full"
          style={{ background: "radial-gradient(ellipse at 70% 50%, rgba(59,130,246,0.12) 0%, transparent 60%)" }} />
      </div>
      {/* Light trails */}
      {[...Array(6)].map((_, i) => (
        <motion.div key={i}
          className="absolute h-px opacity-30"
          style={{
            width: `${150 + i * 60}px`,
            background: i % 2 === 0 ? "linear-gradient(90deg, transparent, #8b5cf6, transparent)" : "linear-gradient(90deg, transparent, #ec4899, transparent)",
            top: `${35 + i * 5}%`,
            left: `${10 + i * 8}%`,
            transform: `rotate(${-15 + i * 6}deg)`,
          }}
          animate={{ opacity: [0.1, 0.5, 0.1], scaleX: [0.8, 1.2, 0.8] }}
          transition={{ duration: 3 + i * 0.5, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}

      {/* Logo */}
      <motion.div
        className="relative z-10 flex flex-col items-center gap-6"
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}
      >
        <motion.div
          className="relative w-24 h-24 rounded-3xl flex items-center justify-center"
          style={{ background: "linear-gradient(135deg, #7c3aed 0%, #8b5cf6 50%, #a78bfa 100%)", boxShadow: "0 0 60px rgba(139,92,246,0.6), 0 0 120px rgba(139,92,246,0.3)" }}
          animate={{ boxShadow: ["0 0 60px rgba(139,92,246,0.6)", "0 0 80px rgba(139,92,246,0.8)", "0 0 60px rgba(139,92,246,0.6)"] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <Camera size={40} className="text-white" />
          <motion.div
            className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-gradient-to-br from-pink-400 to-pink-600 flex items-center justify-center"
            animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 1.5, repeat: Infinity }}
          >
            <Sparkles size={12} className="text-white" />
          </motion.div>
        </motion.div>

        <div className="text-center">
          <div className="flex items-baseline gap-2 justify-center mb-1">
            <span className="text-5xl font-bold bg-clip-text text-transparent"
              style={{ backgroundImage: "linear-gradient(135deg, #a78bfa 0%, #8b5cf6 40%, #ec4899 100%)" }}>
              AI
            </span>
            <span className="text-5xl font-bold text-white">Booth</span>
          </div>
          <p className="text-sm text-white/50 tracking-widest uppercase">Professional Event Photo Booth</p>
        </div>

        <div className="flex gap-2 mt-2">
          {[0, 1, 2].map(i => (
            <motion.div key={i} className="w-2 h-2 rounded-full"
              style={{ background: progress > i * 33 ? "#8b5cf6" : "rgba(255,255,255,0.2)" }}
              animate={{ scale: progress > i * 33 ? [1, 1.3, 1] : 1 }}
              transition={{ duration: 0.4 }}
            />
          ))}
        </div>

        <p className="text-xs text-white/30 mt-2">Loading wonderful moments...</p>

        {/* Progress bar */}
        <div className="w-48 h-0.5 bg-white/10 rounded-full overflow-hidden">
          <motion.div className="h-full rounded-full"
            style={{ background: "linear-gradient(90deg, #8b5cf6, #ec4899)", width: `${progress}%` }}
            transition={{ duration: 0.1 }}
          />
        </div>
      </motion.div>
    </div>
  );
}
