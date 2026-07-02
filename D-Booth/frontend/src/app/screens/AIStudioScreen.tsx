import { Sparkles, ImagePlus, UserCircle, Brain, Image, Globe, Video, Building, Cpu, Zap, ChevronRight } from "lucide-react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { NeonBadge } from "../components/NeonBadge";
import { GlowBtn } from "../components/GlowBtn";
import { SparkArea } from "../components/SparkArea";
import { showToast } from "../stores/useToast";
import type { Screen } from "../types";

export function AIStudioScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const features = [
    { icon: Sparkles, label: "AI 美颜优化", desc: "智能人像美化，一键提升颜值", badge: "热门", color: "from-violet-600/40 to-violet-900/40", glow: "#8b5cf6", screen: "beauty" as Screen },
    { icon: ImagePlus, label: "AI 背景去除", desc: "精准扣图，背景替换秒完成", badge: "新功能", color: "from-blue-600/40 to-blue-900/40", glow: "#3b82f6" },
    { icon: UserCircle, label: "AI 证件照", desc: "专业证件照，多种尺寸一键生成", badge: "", color: "from-emerald-600/40 to-emerald-900/40", glow: "#22c55e" },
    { icon: Brain, label: "AI 头像生成", desc: "把自拍变成专业艺术风格头像", badge: "VIP", color: "from-pink-600/40 to-pink-900/40", glow: "#ec4899" },
    { icon: Image, label: "AI 海报生成", desc: "输入主题，自动生成精美海报", badge: "VIP", color: "from-orange-600/40 to-orange-900/40", glow: "#f59e0b" },
    { icon: Globe, label: "AI 场景生成", desc: "一键生成专业摄影级场景背景", badge: "", color: "from-teal-600/40 to-teal-900/40", glow: "#06b6d4" },
    { icon: Video, label: "AI 视频拍摄", desc: "短视频动态效果，社交媒体首选", badge: "即将上线", color: "from-red-600/40 to-red-900/40", glow: "#ef4444" },
    { icon: Building, label: "AI 品牌生成", desc: "品牌定制，LOGO 与物料一站式", badge: "企业版", color: "from-cyan-600/40 to-cyan-900/40", glow: "#22d3ee" },
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
      <div className="grid grid-cols-4 gap-4">
        {features.map(f => (
          <motion.div key={f.label}
            className={`relative rounded-2xl p-5 cursor-pointer group overflow-hidden bg-gradient-to-br ${f.color} border border-white/[0.06]`}
            whileHover={{ scale: 1.02, y: -3 }} whileTap={{ scale: 0.98 }}
            onClick={() => { if (f.screen) { navigate(f.screen); } else { showToast.info("该功能即将上线，敬请期待！"); } }}
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
            { name: "AI 背景", count: 341, pct: 27 },
            { name: "AI 海报", count: 235, pct: 19 },
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
          <div className="text-xs text-white/40 mb-3">剩余积分（可用约 280 次）</div>
          <GlowBtn size="sm" variant="primary" className="w-full justify-center" onClick={() => showToast.info("充值功能即将上线，敬请期待！")}>充值积分</GlowBtn>
        </GlassCard>
      </div>
    </div>
  );
}
