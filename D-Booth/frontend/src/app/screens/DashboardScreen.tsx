import { Camera, LayoutDashboard, Image, CalendarDays, GalleryHorizontal, Share2, BarChart3, Sparkles, Settings, Monitor, Printer, ChevronRight, Plus, Cloud, Users, QrCode } from "lucide-react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { NeonBadge } from "../components/NeonBadge";
import { GlowBtn } from "../components/GlowBtn";
import { DualAreaChart } from "../components/DualAreaChart";
import { showToast } from "../stores/useToast";
import { WEEK_DATA } from "../constants";
import type { Screen } from "../types";

export function DashboardScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const statsData = WEEK_DATA.map(d => ({ name: d.day, photos: d.photos, prints: d.prints }));

  const quickActions = [
    { label: "开始拍摄", sub: "进入拍照界面", icon: Camera, color: "from-violet-600/80 to-violet-800/80", glow: "rgba(139,92,246,0.4)", screen: "camera" as Screen },
    { label: "模板中心", sub: "选择精美模板", icon: Image, color: "from-pink-600/80 to-pink-800/80", glow: "rgba(236,72,153,0.4)", screen: "templates" as Screen },
    { label: "活动管理", sub: "管理您的活动", icon: CalendarDays, color: "from-blue-600/80 to-blue-800/80", glow: "rgba(59,130,246,0.4)", screen: "events" as Screen },
    { label: "数据统计", sub: "查看运营数据", icon: BarChart3, color: "from-emerald-600/80 to-emerald-800/80", glow: "rgba(34,197,94,0.4)", screen: "analytics" as Screen },
  ];

  return (
    <main className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      {/* Header */}
      <section className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">欢迎回来，摄影师！👋</h1>
          <p className="text-sm text-white/40 mt-0.5">今天是个拍照的好日子，您有 3 个活动正在进行中</p>
        </div>
        <GlowBtn onClick={() => { showToast.info("正在启动相机..."); navigate("camera"); }} size="md" variant="primary">
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

      {/* Device Status + Chart */}
      <section className="grid grid-cols-3 gap-4">
        <GlassCard className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-white/80">设备状态</span>
            <NeonBadge color="green">全部在线</NeonBadge>
          </div>
          {[
            { label: "Canon EOS R5", sub: "主拍摄相机", icon: Camera, status: "在线", pct: 95 },
            { label: "DNP DS620", sub: "打印机", icon: Printer, status: "就绪", pct: 120 },
            { label: "云端同步", sub: "实时备份", icon: Cloud, status: "同步中", pct: 78 },
          ].map(d => (
            <div key={d.label} className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-violet-500/15 flex items-center justify-center">
                <d.icon size={15} className="text-violet-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-white truncate">{d.label}</div>
                <div className="text-[10px] text-white/40">{d.sub}</div>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.8)]" />
                <span className="text-[10px] text-emerald-400">{d.status}</span>
              </div>
            </div>
          ))}
        </GlassCard>

        <GlassCard className="p-4 col-span-2">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-white/80">今日概览</span>
            <span className="text-xs text-white/30">最近 7 天</span>
          </div>
          <DualAreaChart data={statsData} keys={["photos","prints"]} colors={["#8b5cf6","#ec4899"]} labelKey="name" height={110} />
        </GlassCard>
      </section>

      {/* Stats Row */}
      <section className="grid grid-cols-4 gap-4">
        {[
          { label: "今日拍摄", value: "856", unit: "张", icon: Camera, color: "violet", trend: "+12%" },
          { label: "打印数量", value: "312", unit: "张", icon: Printer, color: "pink", trend: "+8%" },
          { label: "参与人数", value: "234", unit: "人", icon: Users, color: "blue", trend: "+15%" },
          { label: "二维码下载", value: "1,892", unit: "次", icon: QrCode, color: "green", trend: "+24%" },
        ].map(s => (
          <GlassCard key={s.label} className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-white/40">{s.label}</span>
              <span className="text-xs text-emerald-400">{s.trend}</span>
            </div>
            <div className="text-2xl font-bold text-white">{s.value}</div>
            <div className="text-xs text-white/30">{s.unit}</div>
          </GlassCard>
        ))}
      </section>
    </main>
  );
}
