export function NeonBadge({ children, color = "purple" }: { children: React.ReactNode; color?: "purple" | "pink" | "blue" | "green" }) {
  const colors: Record<string, string> = {
    purple: "bg-violet-500/10 text-violet-400 border-violet-500/20",
    pink: "bg-pink-500/10 text-pink-400 border-pink-500/20",
    blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    green: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${colors[color]}`}>
      {children}
    </span>
  );
}
