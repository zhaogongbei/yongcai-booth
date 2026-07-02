import { useState, useEffect, useCallback } from "react";
import { Camera, Printer, CalendarDays, TrendingUp, RefreshCw } from "lucide-react";
import { GlassCard } from "../components/GlassCard";
import { DualAreaChart } from "../components/DualAreaChart";
import { DonutChart } from "../components/DonutChart";
import { getMyTeams, getAnalyticsOverview } from "../../lib/api";
import type { Screen } from "../types";

interface AnalyticsScreenProps {
  navigate?: (s: Screen) => void;
}

export function AnalyticsScreen({ navigate }: AnalyticsScreenProps) {
  const [timeRange, setTimeRange] = useState("本月");
  const [loading, setLoading] = useState(false);
  const [usingMock, setUsingMock] = useState(true);
  const [stats, setStats] = useState({
    totalPhotos: 12856,
    totalPrints: 8234,
    activeEvents: 24,
    revenue: 41300,
  });

  const loadAnalytics = useCallback(async () => {
    const token = localStorage.getItem("aibooth.access_token");
    if (!token) { setUsingMock(true); return; }
    setLoading(true);
    try {
      const teams = await getMyTeams(token);
      if (teams.length === 0) { setUsingMock(true); return; }
      const teamId = teams[0].id;
      const data = await getAnalyticsOverview(teamId, token);
      if (data.total_events !== undefined) {
        setStats({
          totalPhotos: data.total_photos || 0,
          totalPrints: data.total_prints || 0,
          activeEvents: data.active_events || 0,
          revenue: data.revenue || data.estimated_revenue || 0,
        });
        setUsingMock(false);
      } else {
        setUsingMock(true);
      }
    } catch {
      setUsingMock(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAnalytics(); }, [loadAnalytics]);

  const weekData = [
    { day: "周一", photos: 230, prints: 180, revenue: 2300 },
    { day: "周二", photos: 345, prints: 290, revenue: 3450 },
    { day: "周三", photos: 280, prints: 220, revenue: 2800 },
    { day: "周四", photos: 410, prints: 360, revenue: 4100 },
    { day: "周五", photos: 520, prints: 440, revenue: 5200 },
    { day: "周六", photos: 680, prints: 580, revenue: 6800 },
    { day: "周日", photos: 490, prints: 410, revenue: 4900 },
  ];
  const pieData = [
    { name: "婚礼", value: 35 },
    { name: "企业", value: 28 },
    { name: "生日", value: 20 },
    { name: "其他", value: 17 },
  ];
  const COLORS = ["#8b5cf6", "#ec4899", "#3b82f6", "#22c55e"];

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">数据统计</h2>
          <p className="text-xs text-white/40 mt-0.5">
            2026年6月 · 本月业绩概览{usingMock ? " · 演示数据" : ""}
            {loading && " · 加载中…"}
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
          { label: "总拍摄量", value: stats.totalPhotos.toLocaleString(), trend: "+23.5%", icon: Camera },
          { label: "总打印量", value: stats.totalPrints.toLocaleString(), trend: "+18.2%", icon: Printer },
          { label: "活跃活动", value: stats.activeEvents.toString(), trend: "+4", icon: CalendarDays },
          { label: "月度收入", value: `¥${(stats.revenue / 100).toLocaleString()}`, trend: "+31.8%", icon: TrendingUp },
        ].map(s => (
          <GlassCard key={s.label} className="p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-white/40">{s.label}</span>
              <s.icon size={16} className="text-violet-400" />
            </div>
            <div className="text-2xl font-black text-white">{s.value}</div>
            <div className="text-xs text-emerald-400 mt-1">{s.trend} 较上月</div>
          </GlassCard>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <GlassCard className="col-span-2 p-4">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-semibold text-white/80">本周趋势</span>
            <div className="flex items-center gap-3 text-xs text-white/40">
              <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-violet-400 inline-block rounded" />拍摄</span>
              <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-pink-400 inline-block rounded" />打印</span>
            </div>
          </div>
          <DualAreaChart data={weekData} keys={["photos","prints"]} colors={["#8b5cf6","#ec4899"]} labelKey="day" height={180} />
        </GlassCard>

        <GlassCard className="p-4">
          <div className="text-sm font-semibold text-white/80 mb-4">活动类型分布</div>
          <DonutChart data={pieData} colors={COLORS} size={140} />
          <div className="space-y-1.5 mt-2">
            {pieData.map((d, i) => (
              <div key={d.name} className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full" style={{ background: COLORS[i] }} />
                  <span className="text-xs text-white/60">{d.name}</span>
                </div>
                <span className="text-xs text-white">{d.value}%</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
