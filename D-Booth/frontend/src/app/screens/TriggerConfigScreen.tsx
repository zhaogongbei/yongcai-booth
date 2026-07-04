import { useState } from "react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { GLASS_SELECT_OPTION_CLASS_NAME, getGlassSelectClassName } from "../components/glassSelect";
import { GlowBtn } from "../components/GlowBtn";
import type { Screen } from "../types";

const TRIGGER_TYPES = [
  "session_start", "countdown_start", "capture_start", "file_download",
  "processing_start", "sharing_screen", "session_end", "printing",
] as const;

const ACTION_TYPES = ["http_callback", "app_execute"] as const;

interface TriggerItem {
  id: string;
  event_type: string;
  action_type: string;
  target: string;
  enabled: boolean;
}

export function TriggerConfigScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const [triggers, setTriggers] = useState<TriggerItem[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ event_type: "session_start", action_type: "http_callback", target: "", enabled: true });

  const addTrigger = () => {
    const newTrigger: TriggerItem = {
      id: Date.now().toString(),
      ...form,
    };
    setTriggers((prev) => [...prev, newTrigger]);
    setForm({ event_type: "session_start", action_type: "http_callback", target: "", enabled: true });
  };

  const toggleTrigger = (id: string) => {
    setTriggers((prev) => prev.map((t) => (t.id === id ? { ...t, enabled: !t.enabled } : t)));
  };

  const deleteTrigger = (id: string) => {
    setTriggers((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">外部触发器配置</h2>
            <p className="text-xs text-white/40 mt-0.5">配置拍照事件触发的外部回调或程序</p>
          </div>
          <GlowBtn size="sm" variant="ghost" onClick={() => navigate("settings")}>返回设置</GlowBtn>
        </div>

        <GlassCard className="p-4 space-y-3">
          <div className="text-sm font-semibold text-white/80">新增触发器</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-white/40">事件类型</label>
              <select className={getGlassSelectClassName("w-full rounded-lg px-3 py-2 text-xs")}
                value={form.event_type}
                onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value }))}>
                {TRIGGER_TYPES.map((t) => (
                  <option key={t} value={t} className={GLASS_SELECT_OPTION_CLASS_NAME}>{t}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-white/40">动作类型</label>
              <select className={getGlassSelectClassName("w-full rounded-lg px-3 py-2 text-xs")}
                value={form.action_type}
                onChange={(e) => setForm((f) => ({ ...f, action_type: e.target.value }))}>
                {ACTION_TYPES.map((a) => (
                  <option key={a} value={a} className={GLASS_SELECT_OPTION_CLASS_NAME}>{a === "http_callback" ? "HTTP回调" : "执行程序"}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-white/40">
              {form.action_type === "http_callback" ? "回调URL" : "可执行文件路径"}
            </label>
            <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-violet-500/50"
              placeholder={form.action_type === "http_callback" ? "https://example.com/webhook" : "C:\\scripts\\flash.exe"}
              value={form.target}
              onChange={(e) => setForm((f) => ({ ...f, target: e.target.value }))}
            />
          </div>
          <GlowBtn size="sm" variant="primary" onClick={addTrigger} className="w-full">添加触发器</GlowBtn>
        </GlassCard>

        <div className="space-y-3">
          <div className="text-sm font-semibold text-white/80">已配置的触发器</div>
          {triggers.length === 0 ? (
            <GlassCard className="p-6 text-center">
              <p className="text-sm text-white/30">暂无触发器配置</p>
            </GlassCard>
          ) : (
            triggers.map((t) => (
              <GlassCard key={t.id} className="p-4 flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${t.enabled ? "bg-emerald-400" : "bg-white/20"}`} />
                    <span className="text-sm font-medium text-white">{t.event_type}</span>
                    <span className="text-xs text-white/30 px-2 py-0.5 rounded bg-white/5">
                      {t.action_type === "http_callback" ? "HTTP回调" : "执行程序"}
                    </span>
                  </div>
                  <div className="text-xs text-white/40 mt-1 truncate">{t.target}</div>
                </div>
                <div className="flex items-center gap-2">
                  <GlowBtn size="sm" variant={t.enabled ? "ghost" : "outline"} onClick={() => toggleTrigger(t.id)}>
                    {t.enabled ? "禁用" : "启用"}
                  </GlowBtn>
                  <button onClick={() => deleteTrigger(t.id)} className="p-1.5 rounded-lg hover:bg-red-500/10 text-white/40 hover:text-red-400 transition-colors">
                    删除
                  </button>
                </div>
              </GlassCard>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
