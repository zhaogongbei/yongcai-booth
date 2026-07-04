import { useState, useEffect, useCallback } from "react";
import { Camera, Printer, CalendarDays, TrendingUp, RefreshCw } from "lucide-react";
import { GlassCard } from "../components/GlassCard";
import { DonutChart } from "../components/DonutChart";
import { getMyTeams, getAnalyticsOverview, tokenStorage } from "../../lib/api";
import type { Screen } from "../types";

interface AnalyticsScreenProps {
  navigate?: (s: Screen) => void;
}

export function AnalyticsScreen({ navigate }: AnalyticsScreenProps) {
  const [timeRange, setTimeRange] = useState("本月");
  const [loading, setLoading] = useState(false);
  const [loadMessage, setLoadMessage] = useState<string | null>(null);
  const [stats, setStats] = useState({
    totalPhotos: 0,
    totalPrints: 0,
    activeEvents: 0,
    revenue: 0,
    totalEvents: 0,
    totalShares: 0,
  });
  const [eventsByType, setEventsByType] = useState<Record<string, number>>({});

  const loadAnalytics = useCallback(async () => {
    const token = tokenStorage.access;
    if (!token) {
      setLoadMessage("请先登录后查看真实统计");
      setStats({ totalPhotos: 0, totalPrints: 0, activeEvents: 0, revenue: 0, totalEvents: 0, totalShares: 0 });
      setEventsByType({});
      return;
    }
    setLoading(true);
    try {
      const teams = await getMyTeams(token);
      if (teams.length === 0) {
        setLoadMessage("当前账号还没有团队，暂无统计数据");
        setStats({ totalPhotos: 0, totalPrints: 0, activeEvents: 0, revenue: 0, totalEvents: 0, totalShares: 0 });
        setEventsByType({});
        return;
      }
      const teamId = teams[0].id;
      const data = await getAnalyticsOverview(teamId, token);
      if (data.total_events !== undefined) {
        setStats({
          totalPhotos: data.total_photos || 0,
          totalPrints: data.total_prints || 0,
          activeEvents: data.active_events || 0,
          revenue: data.revenue || data.estimated_revenue || 0,
          totalEvents: data.total_events || 0,
          totalShares: data.total_shares || 0,
        });
        setEventsByType(data.events_by_type || {});
        setLoadMessage(null);
      } else {
        setLoadMessage("统计接口暂未返回可用数据");
        setStats({ totalPhotos: 0, totalPrints: 0, activeEvents: 0, revenue: 0, totalEvents: 0, totalShares: 0 });
        setEventsByType({});
      }
    } catch {
      setLoadMessage("统计数据加载失败，请稍后刷新");
      setStats({ totalPhotos: 0, totalPrints: 0, activeEvents: 0, revenue: 0, totalEvents: 0, totalShares: 0 });
      setEventsByType({});
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAnalytics(); }, [loadAnalytics]);

  const pieData = Object.entries(eventsByType)
    .filter(([, value]) => value > 0)
    .map(([name, value]) => ({ name, value }));
  const COLORS = ["#8b5cf6", "#ec4899", "#3b82f6", "#22c55e"];
  const hasOverviewData = stats.totalPhotos > 0 || stats.totalPrints > 0 || stats.totalEvents > 0 || stats.totalShares > 0;

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">数据统计</h2>
          <p className="text-xs text-white/40 mt-0.5">
            真实团队业绩概览{loadMessage ? ` · ${loadMessage}` : ""}
            {loading && " · 加载中..."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadAnalytics}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg text-xs bg-white/5 text-white/50 hover:bg-white/10 disabled:opacity-50"
          >
            <RefreshCw size={14} className={`inline mr-1 ${loading ? "animate-spin" : ""}`} />
            刷新
          </button>
          {(["今日", "本周", "本月", "全年"] as const).map(p => (
            <button key={p}
              className={`px-3 py-1.5 rounded-lg text-xs ${timeRange === p ? "bg-violet-500 text-white" : "bg-white/5 text-white/50 hover:bg-white/10"}`}
              onClick={() => setTimeRange(p)}>{p}</button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "总拍摄量", value: stats.totalPhotos.toLocaleString(), sub: "后端照片数", icon: Camera },
          { label: "总打印量", value: stats.totalPrints.toLocaleString(), sub: "后端打印任务", icon: Printer },
          { label: "活跃活动", value: stats.activeEvents.toString(), sub: `总活动 ${stats.totalEvents}`, icon: CalendarDays },
          { label: "估算收入", value: `¥${(stats.revenue / 100).toLocaleString()}`, sub: "来自后端统计", icon: TrendingUp },
        ].map(s => (
          <GlassCard key={s.label} className="p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-white/40">{s.label}</span>
              <s.icon size={16} className="text-violet-400" />
            </div>
            <div className="text-2xl font-black text-white">{s.value}</div>
            <div className="text-xs text-white/35 mt-1">{s.sub}</div>
          </GlassCard>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <GlassCard className="col-span-2 p-4">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-semibold text-white/80">趋势数据</span>
            <div className="flex items-center gap-3 text-xs text-white/40">
              <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-violet-400 inline-block rounded" />拍摄</span>
              <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-pink-400 inline-block rounded" />打印</span>
            </div>
          </div>
          {hasOverviewData ? (
            <div className="rounded-xl border border-white/5 py-14 text-center text-xs text-white/35">
              后端当前只提供汇总统计，趋势接口接入后再展示折线图。
            </div>
          ) : (
            <div className="rounded-xl border border-white/5 py-14 text-center text-xs text-white/35">
              暂无真实趋势数据
            </div>
          )}
        </GlassCard>

        <GlassCard className="p-4">
          <div className="text-sm font-semibold text-white/80 mb-4">活动类型分布</div>
          {pieData.length > 0 ? (
            <>
              <DonutChart data={pieData} colors={COLORS} size={140} />
              <div className="space-y-1.5 mt-2">
                {pieData.map((d, i) => (
                  <div key={d.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                      <span className="text-xs text-white/60">{d.name}</span>
                    </div>
                    <span className="text-xs text-white">{d.value}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="rounded-xl border border-white/5 py-14 text-center text-xs text-white/35">
              暂无真实分类数据
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
