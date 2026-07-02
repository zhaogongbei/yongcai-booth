type StatusTone = "ok" | "warn" | "error" | "idle";

const toneClasses: Record<StatusTone, string> = {
  ok: "border-emerald-500/20 bg-emerald-500/10 text-emerald-300",
  warn: "border-yellow-500/20 bg-yellow-500/10 text-yellow-300",
  error: "border-red-500/20 bg-red-500/10 text-red-300",
  idle: "border-white/10 bg-white/5 text-white/45",
};

const dotClasses: Record<StatusTone, string> = {
  ok: "bg-emerald-400",
  warn: "bg-yellow-400",
  error: "bg-red-400",
  idle: "bg-white/35",
};

export function StatusPill({ label, tone = "idle" }: { label: string; tone?: StatusTone }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${toneClasses[tone]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dotClasses[tone]}`} />
      {label}
    </span>
  );
}
