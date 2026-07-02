export function GlassCard({ className = "", children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={`rounded-2xl border border-white/[0.06] bg-white/[0.04] backdrop-blur-xl ${className}`}>
      {children}
    </div>
  );
}
