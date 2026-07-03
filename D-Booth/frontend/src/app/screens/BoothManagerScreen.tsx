import { useState, useEffect, useCallback } from "react";
import { Monitor, RefreshCw } from "lucide-react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import { NeonBadge } from "../components/NeonBadge";
import { getMyTeams, getTeamBooths, tokenStorage, type BoothResponse } from "../../lib/api";
import { useSettings } from "../stores/useSettings";
import type { Screen } from "../types";

interface BoothDevice {
  id: string;
  name: string;
  device_id: string;
  status: "online" | "offline" | "busy" | "error";
  ip_address: string;
  current_event_name: string | null;
  last_heartbeat: string;
  photos_today: number;
  prints_today: number;
  shares_today: number;
  storage_used: number;
  storage_total: number;
}

function toBoothDevice(booth: BoothResponse): BoothDevice {
  return {
    id: booth.id,
    name: booth.name,
    device_id: booth.device_id,
    status: booth.status,
    ip_address: booth.ip_address ?? "",
    current_event_name: booth.current_event_id ? "已关联活动" : null,
    last_heartbeat: booth.last_heartbeat ?? "",
    photos_today: 0,
    prints_today: 0,
    shares_today: 0,
    storage_used: 0,
    storage_total: 0,
  };
}

export function BoothManagerScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const { currentEvent } = useSettings();
  const [booths, setBooths] = useState<BoothDevice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBooths = useCallback(async () => {
    const token = tokenStorage.access;
    if (!token) {
      setLoading(false);
      setBooths([]);
      return;
    }
    try {
      setLoading(true);
      let teamId = currentEvent?.teamId;
      if (!teamId) {
        const teams = await getMyTeams(token);
        teamId = teams[0]?.id;
      }

      if (!teamId) {
        setBooths([]);
        setError(null);
        return;
      }

      const data = await getTeamBooths(teamId, token);
      setBooths(data.map(toBoothDevice));
      setError(null);
    } catch {
      setError("获取展位列表失败");
    } finally {
      setLoading(false);
    }
  }, [currentEvent?.teamId]);

  useEffect(() => {
    loadBooths();
    const interval = setInterval(loadBooths, 30000);
    return () => clearInterval(interval);
  }, [loadBooths]);

  const activeCount = booths.filter((b) => b.status === "online" || b.status === "busy").length;
  const totalPhotos = booths.reduce((s, b) => s + b.photos_today, 0);
  const totalPrints = booths.reduce((s, b) => s + b.prints_today, 0);

  const statusColor = (status: string) =>
    status === "online" ? "text-emerald-400" :
    status === "busy" ? "text-yellow-400" :
    status === "error" ? "text-red-400" : "text-white/30";

  const statusBg = (status: string) =>
    status === "online" ? "bg-emerald-400" :
    status === "busy" ? "bg-yellow-400" :
    status === "error" ? "bg-red-400" : "bg-white/20";

  const statusLabel = (status: string) =>
    status === "online" ? "在线" :
    status === "busy" ? "忙碌" :
    status === "error" ? "故障" : "离线";

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Monitor size={20} className="text-violet-400" /> 展位管理
            </h2>
            <p className="text-xs text-white/40 mt-0.5">管理所有拍照亭设备状态</p>
          </div>
          <GlowBtn size="sm" variant="ghost" onClick={loadBooths}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> 刷新
          </GlowBtn>
        </div>

        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "活跃展位", value: activeCount.toString(), icon: Monitor, color: "text-emerald-400" },
            { label: "今日照片", value: totalPhotos.toString(), icon: Monitor, color: "text-violet-400" },
            { label: "今日打印", value: totalPrints.toString(), icon: Monitor, color: "text-amber-400" },
            { label: "总展位数", value: booths.length.toString(), icon: Monitor, color: "text-blue-400" },
          ].map((k) => (
            <GlassCard key={k.label} className="p-4">
              <div className="text-xs text-white/40">{k.label}</div>
              <div className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</div>
            </GlassCard>
          ))}
        </div>

        <div className="text-sm font-semibold text-white/80">展位列表</div>

        {loading && booths.length === 0 && (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
          </div>
        )}

        {error && !loading && (
          <GlassCard className="p-6 text-center">
            <p className="text-sm text-amber-400">{error}</p>
            <GlowBtn size="sm" variant="outline" onClick={loadBooths} className="mt-3">重试</GlowBtn>
          </GlassCard>
        )}

        {!loading && !error && booths.length === 0 && (
          <GlassCard className="p-10 text-center">
            <Monitor size={48} className="text-white/10 mx-auto mb-4" />
            <p className="text-sm text-white/40">暂无展位设备注册</p>
            <p className="text-xs text-white/20 mt-1">在拍照亭设备上注册后即可在此管理</p>
          </GlassCard>
        )}

        <div className="space-y-3">
          {booths.map((booth) => (
            <motion.div key={booth.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <GlassCard className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${statusBg(booth.status)}`} />
                    <div>
                      <div className="text-sm font-medium text-white">{booth.name}</div>
                      <div className="text-xs text-white/30">{booth.ip_address || "无IP"}</div>
                    </div>
                    <NeonBadge color={booth.status === "online" ? "green" : "purple"}>
                      {statusLabel(booth.status)}
                    </NeonBadge>
                    {booth.current_event_name && (
                      <span className="text-xs text-violet-400/80">{booth.current_event_name}</span>
                    )}
                  </div>

                  <div className="flex items-center gap-6 text-center">
                    <div>
                      <div className="text-sm font-bold text-white">{booth.photos_today}</div>
                      <div className="text-[10px] text-white/30">照片</div>
                    </div>
                    <div>
                      <div className="text-sm font-bold text-white">{booth.prints_today}</div>
                      <div className="text-[10px] text-white/30">打印</div>
                    </div>
                    <div>
                      <div className="text-sm font-bold text-white">{booth.shares_today}</div>
                      <div className="text-[10px] text-white/30">分享</div>
                    </div>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default BoothManagerScreen;
