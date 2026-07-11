import { ArrowLeft, ChevronDown, User } from "lucide-react";
import { useSettings } from "../stores/useSettings";
import { useAuth } from "../stores/useAuth";
import { cameraTone, printerTone, useBoothHealth, type HealthTone } from "../hooks/useBoothHealth";

const TONE_DOT_CLASS: Record<HealthTone, string> = {
  ok: "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]",
  warn: "bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.8)]",
  error: "bg-red-400 shadow-[0_0_6px_rgba(248,113,113,0.8)]",
  idle: "bg-white/30",
};

function StatusDot({ tone }: { tone: HealthTone }) {
  return <div className={`w-2 h-2 rounded-full ${TONE_DOT_CLASS[tone]}`} />;
}

export function TopBar({ title, onBack, onSelectEvent }: { title?: string; onBack?: () => void; onSelectEvent?: () => void }) {
  const { currentEvent } = useSettings();
  const { user } = useAuth();
  // 常驻顶栏只读共享健康轮询，不启动打印队列轮询（队列由打印/运营页按需拉取）
  const health = useBoothHealth(undefined, { withQueue: false });

  const cameraLabel = health.camera.connected
    ? (health.camera.model || "相机已连接")
    : "相机未连接";
  const printerLabel = health.selectedPrinter?.name
    ?? (health.printers.length > 0 ? health.printers[0].name : "未检测到打印机");
  const userInitial = user
    ? (user.full_name?.trim() || user.email).charAt(0).toUpperCase()
    : null;

  return (
    <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
      <div className="flex items-center gap-3">
        {onBack && (
          <button onClick={onBack} className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/60" aria-label="返回">
            <ArrowLeft size={16} />
          </button>
        )}
        <button
          className="flex items-center gap-2 rounded-lg px-1.5 py-1 -mx-1.5 hover:bg-white/5 transition-colors disabled:cursor-default disabled:hover:bg-transparent"
          onClick={onSelectEvent}
          disabled={!onSelectEvent}
          aria-label="切换活动"
        >
          <span className="text-xs text-white/40">活动名称：</span>
          <span className={`text-xs font-medium ${currentEvent ? "text-white/80" : "text-white/40"}`}>
            {currentEvent?.name ?? "未选择活动"}
          </span>
          {onSelectEvent && <ChevronDown size={12} className="text-white/40" />}
        </button>
        {title && <span className="text-sm font-semibold text-white">{title}</span>}
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5" title={health.camera.error ?? undefined}>
          <StatusDot tone={cameraTone(health.camera)} />
          <span className="text-xs text-white/60">{cameraLabel}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <StatusDot tone={printerTone(health.selectedPrinter)} />
          <span className="text-xs text-white/60">{printerLabel}</span>
        </div>
        <div className="flex items-center gap-2">
          {user && (
            <span className="text-xs text-white/50 max-w-[140px] truncate">
              {user.full_name?.trim() || user.email}
            </span>
          )}
          <div
            className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-pink-500 flex items-center justify-center text-xs font-bold text-white"
            title={user ? (user.full_name?.trim() || user.email) : "未登录"}
          >
            {userInitial ?? <User size={14} className="text-white/80" />}
          </div>
        </div>
      </div>
    </div>
  );
}
