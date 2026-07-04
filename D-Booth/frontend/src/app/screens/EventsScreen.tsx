import { useState, useEffect, useCallback } from "react";
import { CalendarDays, TrendingUp, Camera, Printer, Filter, Plus, Search, Eye, RefreshCw } from "lucide-react";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import { showToast } from "../stores/useToast";
import { useSettings } from "../stores/useSettings";
import { useCaptureFlow } from "../stores/useCaptureFlow";
import { createEvent, createPhotoSession, getEvents, getMyTeams, tokenStorage, type EventResponse } from "../../lib/api";
import type { Screen } from "../types";

interface EventsScreenProps {
  navigate?: (s: Screen) => void;
}

interface EventRow {
  id: string;
  name: string;
  teamId: string;
  date: string;
  status: string;
  photos: number;
  prints: number;
  guests: number;
  revenue: string;
}

// 后端状态映射到中文展示
const STATUS_LABEL: Record<string, string> = {
  active: "进行中", completed: "已完成", scheduled: "即将开始", draft: "草稿", cancelled: "已取消",
};

function toRow(ev: EventResponse): EventRow {
  return {
    id: ev.id,
    name: ev.name,
    teamId: ev.team_id,
    date: (ev.start_date || "").slice(0, 10),
    status: STATUS_LABEL[ev.status] ?? ev.status,
    photos: 0, prints: 0, guests: 0, revenue: "—",
  };
}

function parseRevenue(value: string) {
  const numeric = Number(value.replace(/[^\d.-]/g, ""));
  return Number.isFinite(numeric) ? numeric : 0;
}

function toEventDateInputValue(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

function buildEventDateRange(dateValue: string) {
  const start = new Date(`${dateValue}T09:00:00`);
  const end = new Date(start);
  end.setHours(start.getHours() + 4);
  return {
    startDate: start.toISOString(),
    endDate: end.toISOString(),
  };
}

export function EventsScreen({ navigate }: EventsScreenProps) {
  const { setCurrentEvent } = useSettings();
  const { setCaptureContext } = useCaptureFlow();
  const [searchTerm, setSearchTerm] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState("全部");
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newEventName, setNewEventName] = useState("");
  const [newEventDate, setNewEventDate] = useState(toEventDateInputValue());
  const [newEventVenue, setNewEventVenue] = useState("");

  const loadEvents = useCallback(async () => {
    const token = tokenStorage.access;
    if (!token) {
      setEvents([]);
      setLoadError("请先登录后查看和创建活动");
      return;
    }
    setLoading(true);
    try {
      const data = await getEvents(token);
      setEvents(data.map(toRow));
      setLoadError(null);
    } catch {
      setEvents([]);
      setLoadError("活动列表加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadEvents(); }, [loadEvents]);

  const filtered = events.filter(e => {
    if (!e.name.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    if (selectedStatus !== "全部" && e.status !== selectedStatus) return false;
    return true;
  });

  const resetCreateForm = () => {
    setNewEventName("");
    setNewEventDate(toEventDateInputValue());
    setNewEventVenue("");
  };

  const submitNewEvent = async () => {
    const token = tokenStorage.access;
    const name = newEventName.trim();
    if (!token) {
      showToast.error("请先登录后再新建活动");
      return;
    }
    if (!name) {
      showToast.error("请输入活动名称");
      return;
    }
    if (!newEventDate) {
      showToast.error("请选择活动日期");
      return;
    }

    setCreating(true);
    try {
      const teams = await getMyTeams(token);
      const teamId = teams[0]?.id;
      if (!teamId) {
        showToast.error("未找到可创建活动的团队");
        return;
      }

      const dateRange = buildEventDateRange(newEventDate);
      const event = await createEvent({
        teamId,
        name,
        startDate: dateRange.startDate,
        endDate: dateRange.endDate,
        eventType: "booth",
        venueName: newEventVenue.trim() || undefined,
        token,
      });

      setEvents(prev => [toRow(event), ...prev.filter(item => item.id !== event.id)]);
      resetCreateForm();
      setShowCreateForm(false);
      showToast.success("活动已创建");
      await loadEvents();
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "活动创建失败");
    } finally {
      setCreating(false);
    }
  };

  // 进入某活动的拍照流程：注入 eventId + token，跳转相机屏
  const enterCapture = async (eventId: string, eventName: string) => {
    const token = tokenStorage.access;
    if (!token) {
      showToast.error("请先登录后再进入拍照");
      return;
    }

    let teamId = events.find(event => event.id === eventId)?.teamId;
    if (!teamId) {
      const teams = await getMyTeams(token).catch(() => []);
      teamId = teams[0]?.id;
    }
    if (teamId) {
      setCurrentEvent({ id: eventId, name: eventName, teamId });
    }

    try {
      const session = await createPhotoSession({ eventId, token });
      setCaptureContext({ eventId, teamId, sessionId: session.id, authToken: token });
      showToast.success(`已进入「${eventName}」拍照模式`);
    } catch (err) {
      setCaptureContext({ eventId, teamId, sessionId: null, authToken: token });
      showToast.error(err instanceof Error ? err.message : "拍照会话创建失败");
    }
    navigate?.("camera");
  };

  const statusColors: Record<string, string> = {
    "进行中": "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
    "已完成": "text-blue-400 bg-blue-400/10 border-blue-400/20",
    "即将开始": "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  };
  const totals = {
    events: events.length,
    revenue: events.reduce((sum, event) => sum + parseRevenue(event.revenue), 0),
    photos: events.reduce((sum, event) => sum + event.photos, 0),
    prints: events.reduce((sum, event) => sum + event.prints, 0),
  };

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">活动管理</h2>
          <p className="text-xs text-white/40 mt-0.5">
            共 {events.length} 个活动
            {loading && " · 加载中…"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <GlowBtn size="sm" variant="ghost" onClick={loadEvents} disabled={loading}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />刷新
          </GlowBtn>
          <GlowBtn size="sm" variant="ghost" onClick={() => setShowFilters(f => !f)}><Filter size={14} />筛选</GlowBtn>
          <GlowBtn size="sm" variant="primary" onClick={() => setShowCreateForm(f => !f)}><Plus size={14} />新建活动</GlowBtn>
        </div>
      </div>

      {showCreateForm && (
        <GlassCard className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm font-semibold text-white/80">新建活动</span>
            <button className="text-xs text-white/40 hover:text-white/70" onClick={() => setShowCreateForm(false)}>关闭</button>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-[1.5fr_160px_1fr_auto] md:items-end">
            <label className="space-y-1">
              <span className="text-xs text-white/40">活动名称</span>
              <input
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:border-violet-500/50"
                placeholder="例如：品牌快闪拍照"
                value={newEventName}
                onChange={e => setNewEventName(e.target.value)}
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-white/40">活动日期</span>
              <input
                type="date"
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-violet-500/50"
                value={newEventDate}
                onChange={e => setNewEventDate(e.target.value)}
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-white/40">场地</span>
              <input
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:border-violet-500/50"
                placeholder="可选"
                value={newEventVenue}
                onChange={e => setNewEventVenue(e.target.value)}
              />
            </label>
            <GlowBtn size="sm" variant="primary" onClick={submitNewEvent} disabled={creating}>
              <Plus size={14} />{creating ? "创建中" : "创建"}
            </GlowBtn>
          </div>
        </GlassCard>
      )}

      {loadError && (
        <GlassCard className="border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-200">
          {loadError}
        </GlassCard>
      )}

      {/* Filter panel */}
      {showFilters && (
        <GlassCard className="p-4">
          <div className="flex items-center gap-4">
            <span className="text-xs text-white/40">按状态筛选：</span>
            {["全部", "进行中", "已完成", "即将开始"].map(f => (
              <button
                key={f}
                className={`px-3 py-1 rounded-lg text-xs transition-colors ${selectedStatus === f ? "bg-violet-500/20 text-violet-300 border border-violet-500/30" : "bg-white/5 text-white/60 hover:bg-white/10 hover:text-white"}`}
                onClick={() => setSelectedStatus(f)}
              >
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
          { label: "总活动数", value: totals.events.toLocaleString(), icon: CalendarDays, color: "violet" },
          { label: "收入记录", value: totals.revenue ? `¥${totals.revenue.toLocaleString()}` : "—", icon: TrendingUp, color: "green" },
          { label: "总拍摄量", value: totals.photos.toLocaleString(), icon: Camera, color: "blue" },
          { label: "总打印量", value: totals.prints.toLocaleString(), icon: Printer, color: "pink" },
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
                {["活动名称", "日期", "状态", "照片数", "打印数", "参与人数", "收入", "操作"].map(h => (
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
                  <td className="px-4 py-4 text-sm font-semibold text-emerald-400">{e.revenue}</td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-1">
                      <button className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-white/70" onClick={() => setSelectedEvent(e.name)} title="查看详情"><Eye size={13} /></button>
                      <button className="p-1.5 rounded-lg hover:bg-violet-500/20 text-white/40 hover:text-violet-400" onClick={() => enterCapture(e.id, e.name)} title="进入拍照"><Camera size={13} /></button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-sm text-white/35">
                    暂无活动，请先新建真实活动
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}
