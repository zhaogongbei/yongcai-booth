import { Sparkles, ImagePlus, Cpu, Zap, ChevronRight } from "lucide-react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { NeonBadge } from "../components/NeonBadge";
import { SparkArea } from "../components/SparkArea";
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
          <NeonBadge color="purple"><Cpu size={11} />GPT-4V 加持</NeonBadge>
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

      {/* AI usage stats */}
      <div className="grid grid-cols-3 gap-4">
        <GlassCard className="p-4">
          <div className="text-xs text-white/40 mb-3">AI 使用统计</div>
          <div className="flex items-end gap-3">
            <div>
              <div className="text-3xl font-black text-white">1,256</div>
              <div className="text-xs text-white/40">本月 AI 处理次数</div>
            </div>
            <div className="flex-1">
              <SparkArea data={[80,120,95,180,140,220,180,260]} color="#8b5cf6" height={50} />
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-4">
          <div className="text-xs text-white/40 mb-3">热门 AI 功能 TOP 3</div>
          {[
            { name: "AI 美颜", count: 680, pct: 54 },
            { name: "背景替换", count: 341, pct: 27 },
            { name: "贴纸美化", count: 235, pct: 19 },
          ].map(r => (
            <div key={r.name} className="flex items-center gap-2 mb-2">
              <span className="text-xs text-white/60 w-16">{r.name}</span>
              <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-pink-500" style={{ width: `${r.pct}%` }} />
              </div>
              <span className="text-xs text-white/40 w-8 text-right">{r.count}</span>
            </div>
          ))}
        </GlassCard>

        <GlassCard className="p-4">
          <div className="text-xs text-white/40 mb-3">AI 积分余额</div>
          <div className="text-3xl font-black text-white mb-1">8,420</div>
          <div className="text-xs text-white/40">当前仅展示账户余额；充值请在后台账户系统处理。</div>
        </GlassCard>
      </div>
    </div>
  );
}
