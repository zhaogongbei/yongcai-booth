import { useState, useEffect, useCallback } from "react";
import { CalendarDays, TrendingUp, Camera, Printer, Filter, Plus, Search, Eye, Settings, RefreshCw } from "lucide-react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import { SimpleBarChart } from "../components/SimpleBarChart";
import { showToast } from "../stores/useToast";
import { useCaptureFlow } from "../stores/useCaptureFlow";
import { createPhotoSession, getEvents, tokenStorage, type EventResponse } from "../../lib/api";
import type { Screen } from "../types";

interface EventsScreenProps {
  navigate?: (s: Screen) => void;
}

// 演示数据：后端无活动时回退展示
const DEMO_EVENTS = [
  { id: "demo-event-1", name: "夏日派对 2026", date: "2026-06-10", status: "进行中", photos: 1234, prints: 856, guests: 234, qr: 1892, revenue: "¥12,800" },
  { id: "demo-event-2", name: "婚礼庆典 2026", date: "2026-06-08", status: "已完成", photos: 2341, prints: 1890, guests: 412, qr: 3241, revenue: "¥28,500" },
  { id: "demo-event-3", name: "毕业典礼 2026", date: "2026-06-15", status: "即将开始", photos: 0, prints: 0, guests: 0, qr: 0, revenue: "¥0" },
];

// 后端状态映射到中文展示
const STATUS_LABEL: Record<string, string> = {
  active: "进行中", completed: "已完成", scheduled: "即将开始", draft: "草稿", cancelled: "已取消",
};

function toRow(ev: EventResponse) {
  return {
    id: ev.id,
    name: ev.name,
    date: (ev.start_date || "").slice(0, 10),
    status: STATUS_LABEL[ev.status] ?? ev.status,
    photos: 0, prints: 0, guests: 0, qr: 0, revenue: "—",
    real: true,
  };
}

export function EventsScreen({ navigate }: EventsScreenProps) {
  const { setCaptureContext } = useCaptureFlow();
  const [searchTerm, setSearchTerm] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);
  const [events, setEvents] = useState(DEMO_EVENTS);
  const [loading, setLoading] = useState(false);
  const [usingMock, setUsingMock] = useState(true);

  const loadEvents = useCallback(async () => {
    const token = tokenStorage.access;
    if (!token) { setUsingMock(true); setEvents(DEMO_EVENTS); return; }
    setLoading(true);
    try {
      const data = await getEvents(token);
      if (data.length > 0) {
        setEvents(data.map(toRow));
        setUsingMock(false);
      } else {
        setEvents(DEMO_EVENTS);
        setUsingMock(true);
      }
    } catch {
      setEvents(DEMO_EVENTS);
      setUsingMock(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadEvents(); }, [loadEvents]);

  const filtered = events.filter(e => e.name.toLowerCase().includes(searchTerm.toLowerCase()));

  // 进入某活动的拍照流程：注入 eventId + token，跳转相机屏
  const enterCapture = async (eventId: string, eventName: string) => {
    const token = tokenStorage.access;
    if (!token || usingMock) {
      setCaptureContext({ eventId, sessionId: null, authToken: token });
      showToast.success(`已进入「${eventName}」拍照模式（演示数据，上传会失败）`);
      navigate?.("camera");
      return;
    }

    try {
      const session = await createPhotoSession({ eventId, token });
      setCaptureContext({ eventId, sessionId: session.id, authToken: token });
      showToast.success(`已进入「${eventName}」拍照模式`);
    } catch (err) {
      setCaptureContext({ eventId, sessionId: null, authToken: token });
      showToast.error(err instanceof Error ? err.message : "拍照会话创建失败");
    }
    navigate?.("camera");
  };

  const statusColors: Record<string, string> = {
    "进行中": "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
    "已完成": "text-blue-400 bg-blue-400/10 border-blue-400/20",
    "即将开始": "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  };

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">活动管理</h2>
          <p className="text-xs text-white/40 mt-0.5">
            共 {events.length} 个活动{usingMock ? " · 演示数据" : ""}
            {loading && " · 加载中…"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <GlowBtn size="sm" variant="ghost" onClick={loadEvents} disabled={loading}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />刷新
          </GlowBtn>
          <GlowBtn size="sm" variant="ghost" onClick={() => setShowFilters(f => !f)}><Filter size={14} />筛选</GlowBtn>
          <GlowBtn size="sm" variant="primary" onClick={() => showToast.info("新建活动功能开发中")}><Plus size={14} />新建活动</GlowBtn>
        </div>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <GlassCard className="p-4">
          <div className="flex items-center gap-4">
            <span className="text-xs text-white/40">按状态筛选：</span>
            {["全部", "进行中", "已完成", "即将开始"].map(f => (
              <button key={f} className="px-3 py-1 rounded-lg text-xs bg-white/5 text-white/60 hover:bg-white/10 hover:text-white transition-colors">
                {f}
              </button>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Selected event detail */}
      {selectedEvent && (
        <GlassCard className="p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-white/80">{selectedEvent} - 详情</span>
            <button className="text-xs text-white/40 hover:text-white/70" onClick={() => setSelectedEvent(null)}>关闭</button>
          </div>
          <div className="grid grid-cols-4 gap-3">
            {(() => {
              const ev = events.find(e => e.name === selectedEvent);
              if (!ev) return null;
              return [
                { label: "照片数", value: ev.photos.toLocaleString() },
                { label: "打印数", value: ev.prints.toLocaleString() },
                { label: "参与人数", value: ev.guests.toLocaleString() },
                { label: "收入", value: ev.revenue },
              ].map(d => (
                <div key={d.label}>
                  <div className="text-xs text-white/40">{d.label}</div>
                  <div className="text-sm font-bold text-white">{d.value}</div>
                </div>
              ));
            })()}
          </div>
        </GlassCard>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "总活动数", value: "24", icon: CalendarDays, color: "violet" },
          { label: "本月收入", value: "¥41,300", icon: TrendingUp, color: "green" },
          { label: "总拍摄量", value: "12,856", icon: Camera, color: "blue" },
          { label: "总打印量", value: "8,234", icon: Printer, color: "pink" },
        ].map(s => (
          <GlassCard key={s.label} className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-500/15 flex items-center justify-center">
              <s.icon size={20} className="text-violet-400" />
            </div>
            <div>
              <div className="text-xs text-white/40">{s.label}</div>
              <div className="text-xl font-bold text-white">{s.value}</div>
            </div>
          </GlassCard>
        ))}
      </div>

      {/* Events table */}
      <GlassCard className="overflow-hidden">
        <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between">
          <span className="text-sm font-semibold text-white/80">活动列表</span>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-white/30" />
              <input className="bg-white/5 border border-white/10 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-white/30 outline-none"
                placeholder="搜索活动..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
            </div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                {["活动名称", "日期", "状态", "照片数", "打印数", "参与人数", "二维码下载", "云端相册", "收入", "操作"].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-[10px] text-white/30 uppercase font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((e, i) => (
                <tr key={e.id ?? i} className="border-b border-white/3 hover:bg-white/2 transition-colors">
                  <td className="px-4 py-4 text-sm font-medium text-white">{e.name}</td>
                  <td className="px-4 py-4 text-xs text-white/50">{e.date}</td>
                  <td className="px-4 py-4">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${statusColors[e.status]}`}>{e.status}</span>
                  </td>
                  <td className="px-4 py-4 text-sm text-white">{e.photos.toLocaleString()}</td>
                  <td className="px-4 py-4 text-sm text-white">{e.prints.toLocaleString()}</td>
                  <td className="px-4 py-4 text-sm text-white">{e.guests.toLocaleString()}</td>
                  <td className="px-4 py-4 text-sm text-white">{e.qr.toLocaleString()}</td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 rounded-full bg-emerald-400" />
                      <span className="text-xs text-emerald-400">同步中</span>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm font-semibold text-emerald-400">{e.revenue}</td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-1">
                      <button className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-white/70" onClick={() => setSelectedEvent(e.name)} title="查看详情"><Eye size={13} /></button>
                      <button className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-white/70" onClick={() => showToast.info(`${e.name} 设置`)} title="设置"><Settings size={13} /></button>
                      <button className="p-1.5 rounded-lg hover:bg-violet-500/20 text-white/40 hover:text-violet-400" onClick={() => enterCapture(e.id, e.name)} title="进入拍照"><Camera size={13} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {/* Recent activity */}
      <div className="grid grid-cols-2 gap-4">
        <GlassCard className="p-4">
          <div className="text-xs text-white/60 font-semibold mb-3">最近活动</div>
          <div className="space-y-3">
            {[
              { action: "拍摄完成", detail: "夏日派对 · 共 12 张", time: "2 分钟前", color: "violet" },
              { action: "打印任务", detail: "完成 5 张打印", time: "8 分钟前", color: "blue" },
              { action: "新访客", detail: "3 人扫码下载", time: "15 分钟前", color: "green" },
              { action: "云同步", detail: "已同步 24 张照片", time: "20 分钟前", color: "pink" },
            ].map((a, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className={`w-1.5 h-1.5 rounded-full mt-1.5 ${a.color === "violet" ? "bg-violet-400" : a.color === "blue" ? "bg-blue-400" : a.color === "green" ? "bg-emerald-400" : "bg-pink-400"}`} />
                <div className="flex-1">
                  <div className="text-xs text-white">{a.action}</div>
                  <div className="text-[10px] text-white/40">{a.detail}</div>
                </div>
                <span className="text-[10px] text-white/30">{a.time}</span>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard className="p-4">
          <div className="text-xs text-white/60 font-semibold mb-3">收入分析</div>
          <SimpleBarChart data={[{n:"1月",v:8200},{n:"2月",v:11500},{n:"3月",v:9800},{n:"4月",v:14200},{n:"5月",v:12800},{n:"6月",v:18500}]} valueKey="v" labelKey="n" color="#8b5cf6" height={120} />
        </GlassCard>
      </div>
    </div>
  );
}
