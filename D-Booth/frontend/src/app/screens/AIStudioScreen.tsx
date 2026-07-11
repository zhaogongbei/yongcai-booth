import { Sparkles, ImagePlus, Zap, ChevronRight } from "lucide-react";
import { motion } from "motion/react";
import { NeonBadge } from "../components/NeonBadge";
import type { Screen } from "../types";

export function AIStudioScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const features = [
    { icon: Sparkles, label: "AI 美颜优化", desc: "智能人像美化，一键提升颜值", badge: "热门", color: "from-violet-600/40 to-violet-900/40", glow: "#8b5cf6", screen: "beauty" as Screen },
    { icon: ImagePlus, label: "AI 背景替换", desc: "绿幕抠图、背景上传、预览与保存", badge: "已接入", color: "from-blue-600/40 to-blue-900/40", glow: "#3b82f6", screen: "green-screen" as Screen },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">AI 功能中心</h2>
          <p className="text-xs text-white/40 mt-0.5">基于最新大模型技术，为您提供专业 AI 摄影服务</p>
        </div>
        <div className="flex items-center gap-2">
          <NeonBadge color="blue"><Zap size={11} />实时处理</NeonBadge>
        </div>
      </div>

      {/* Feature grid */}
      <div className="grid grid-cols-2 gap-4">
        {features.map(f => (
          <motion.div key={f.label}
            className={`relative rounded-2xl p-5 cursor-pointer group overflow-hidden bg-gradient-to-br ${f.color} border border-white/[0.06]`}
            whileHover={{ scale: 1.02, y: -3 }} whileTap={{ scale: 0.98 }}
            onClick={() => navigate(f.screen)}
            style={{ boxShadow: `0 0 0 1px rgba(255,255,255,0.04)` }}
          >
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              style={{ background: `radial-gradient(ellipse at 30% 30%, ${f.glow}20 0%, transparent 70%)` }} />
            <div className="relative">
              <div className="flex items-start justify-between mb-3">
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
                  style={{ background: `${f.glow}20`, boxShadow: `0 0 20px ${f.glow}30` }}>
                  <f.icon size={24} style={{ color: f.glow }} />
                </div>
                {f.badge && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/10 text-white/70">{f.badge}</span>
                )}
              </div>
              <div className="text-sm font-semibold text-white mb-1">{f.label}</div>
              <div className="text-xs text-white/50 leading-relaxed">{f.desc}</div>
              <div className="mt-4 flex items-center gap-1 text-xs text-white/40 group-hover:text-white/70 transition-colors">
                <span>立即体验</span>
                <ChevronRight size={13} />
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <p className="text-xs text-white/30">
        使用统计与积分账户尚未接入后端，接入后将在此展示真实数据。
      </p>
    </div>
  );
}
