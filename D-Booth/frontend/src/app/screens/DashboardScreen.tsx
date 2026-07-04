import { Camera, Image, CalendarDays, BarChart3, Printer, ChevronRight, Plus } from "lucide-react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import type { Screen } from "../types";

export function DashboardScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const quickActions = [
    { label: "开始拍摄", sub: "选择真实活动", icon: Camera, color: "from-violet-600/80 to-violet-800/80", glow: "rgba(139,92,246,0.4)", screen: "events" as Screen },
    { label: "模板中心", sub: "选择精美模板", icon: Image, color: "from-pink-600/80 to-pink-800/80", glow: "rgba(236,72,153,0.4)", screen: "templates" as Screen },
    { label: "活动管理", sub: "管理您的活动", icon: CalendarDays, color: "from-blue-600/80 to-blue-800/80", glow: "rgba(59,130,246,0.4)", screen: "events" as Screen },
    { label: "数据统计", sub: "查看运营数据", icon: BarChart3, color: "from-emerald-600/80 to-emerald-800/80", glow: "rgba(34,197,94,0.4)", screen: "analytics" as Screen },
  ];

  return (
    <main className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      {/* Header */}
      <section className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">工作台</h1>
          <p className="text-sm text-white/40 mt-0.5">从真实活动进入拍照，确保上传、打印和分享链路可用</p>
        </div>
        <GlowBtn onClick={() => navigate("events")} size="md" variant="primary">
          <Plus size={16} />
          开始新拍摄
        </GlowBtn>
      </section>

      {/* Quick Actions */}
      <section className="grid grid-cols-4 gap-4">
        {quickActions.map(a => (
          <motion.button key={a.label} onClick={() => navigate(a.screen)}
            className="relative rounded-2xl p-5 text-left overflow-hidden cursor-pointer group"
            style={{ background: `linear-gradient(135deg, ${a.color.replace("from-", "").replace(" to-", ", ")})` }}
            whileHover={{ scale: 1.02, y: -2 }} whileTap={{ scale: 0.98 }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
          >
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ background: `radial-gradient(ellipse at 30% 30%, ${a.glow} 0%, transparent 60%)` }} />
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-white/15 flex items-center justify-center mb-3">
                <a.icon size={22} className="text-white" />
              </div>
              <div className="text-base font-semibold text-white">{a.label}</div>
              <div className="text-xs text-white/60 mt-0.5">{a.sub}</div>
              <ChevronRight size={16} className="absolute top-0 right-0 text-white/40 group-hover:text-white/80 transition-colors" />
            </div>
          </motion.button>
        ))}
      </section>

      <section className="grid grid-cols-2 gap-4">
        <GlassCard className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/15">
              <CalendarDays size={20} className="text-violet-400" />
            </div>
            <div>
              <div className="text-sm font-semibold text-white/80">拍摄会话</div>
              <div className="text-xs text-white/40">活动页会创建真实 photo session</div>
            </div>
          </div>
        </GlassCard>
        <GlassCard className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-pink-500/15">
              <Printer size={20} className="text-pink-400" />
            </div>
            <div>
              <div className="text-sm font-semibold text-white/80">打印与分享</div>
              <div className="text-xs text-white/40">仅使用已上传照片提交真实任务</div>
            </div>
          </div>
        </GlassCard>
      </section>
    </main>
  );
}
