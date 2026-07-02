import { ArrowLeft, ChevronDown } from "lucide-react";
import { Crown } from "./Crown";

export function TopBar({ title, event = "夏日派对 2026", onBack }: { title?: string; event?: string; onBack?: () => void }) {
  return (
    <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
      <div className="flex items-center gap-3">
        {onBack && (
          <button onClick={onBack} className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/60" aria-label="返回">
            <ArrowLeft size={16} />
          </button>
        )}
        <div className="flex items-center gap-2" role="group" aria-label="切换活动">
          <span className="text-xs text-white/40">活动名称：</span>
          <span className="text-xs text-white/80 font-medium">{event}</span>
          <ChevronDown size={12} className="text-white/40" />
        </div>
        {title && <span className="text-sm font-semibold text-white">{title}</span>}
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
          <span className="text-xs text-white/60">Canon EOS R5</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
          <span className="text-xs text-white/60">DNP DS620</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-gradient-to-r from-amber-500/20 to-amber-600/10 border border-amber-500/20 rounded-full px-3 py-1">
            <Crown size={12} className="text-amber-400" />
            <span className="text-xs text-amber-400">Pro 会员</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-pink-500 flex items-center justify-center text-xs font-bold">
            张
          </div>
        </div>
      </div>
    </div>
  );
}
