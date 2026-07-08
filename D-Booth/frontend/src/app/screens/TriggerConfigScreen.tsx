import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { GLASS_SELECT_OPTION_CLASS_NAME, getGlassSelectClassName } from "../components/glassSelect";
import { GlowBtn } from "../components/GlowBtn";
import { ApiError, getTriggerConfigs, updateTriggerConfigs, type TriggerConfigResponse } from "../../lib/api";
import { useCaptureFlow } from "../stores/useCaptureFlow";
import { useSettings } from "../stores/useSettings";
import { showToast } from "../stores/useToast";
import type { Screen } from "../types";

const TRIGGER_TYPES = [
  "session_start", "countdown_start", "capture_start", "file_download",
  "processing_start", "sharing_screen", "session_end", "printing",
] as const;

const ACTION_TYPES = ["http_callback"] as const;

interface TriggerItem {
  id: string;
  event_type: string;
  action_type: "http_callback";
  target: string;
  enabled: boolean;
}

export function TriggerConfigScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const { currentEvent } = useSettings();
  const { eventId, authToken } = useCaptureFlow();
  const activeEventId = currentEvent?.id ?? eventId;
  const [triggers, setTriggers] = useState<TriggerItem[]>([]);
  const [form, setForm] = useState<{ event_type: string; action_type: "http_callback"; target: string; enabled: boolean }>({
    event_type: "session_start",
    action_type: "http_callback",
    target: "",
    enabled: true,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const loadTriggers = async () => {
    if (!activeEventId || !authToken) {
      setTriggers([]);
      return;
    }

    try {
      setIsLoading(true);
      const configs = await getTriggerConfigs(activeEventId, authToken);
      setTriggers(configs.map((config: TriggerConfigResponse) => ({
        id: config.id,
        event_type: config.event_type,
        action_type: "http_callback",
        target: config.target,
        enabled: config.enabled,
      })));
    } catch (error) {
      showToast.error(error instanceof Error ? error.message : "触发器配置读取失败");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadTriggers();
  }, [activeEventId, authToken]);

  const persistTriggers = async (nextTriggers: TriggerItem[]) => {
    if (!activeEventId || !authToken) {
      showToast.error("请先从活动进入现场控制台并登录");
      return;
    }

    try {
      setIsSaving(true);
      const saved = await updateTriggerConfigs(activeEventId, authToken, nextTriggers.map(trigger => ({
        event_type: trigger.event_type,
        action_type: trigger.action_type,
        target: trigger.target,
        enabled: trigger.enabled,
        payload_template: {},
        timeout: 10,
        retry: 3,
      })));
      setTriggers(saved.map(config => ({
        id: config.id,
        event_type: config.event_type,
        action_type: "http_callback",
        target: config.target,
        enabled: config.enabled,
      })));
      showToast.success("触发器配置已保存");
    } catch (error) {
      const message = error instanceof ApiError ? error.message : error instanceof Error ? error.message : "触发器配置保存失败";
      showToast.error(message);
    } finally {
      setIsSaving(false);
    }
  };

  const addTrigger = () => {
    if (!form.target.trim()) {
      showToast.error("请填写 HTTP 回调 URL");
      return;
    }

    const newTrigger: TriggerItem = {
      id: `local_${Date.now()}`,
      ...form,
      target: form.target.trim(),
    };
    void persistTriggers([...triggers, newTrigger]);
    setForm({ event_type: "session_start", action_type: "http_callback", target: "", enabled: true });
  };

  const toggleTrigger = (id: string) => {
    void persistTriggers(triggers.map((t) => (t.id === id ? { ...t, enabled: !t.enabled } : t)));
  };

  const deleteTrigger = (id: string) => {
    void persistTriggers(triggers.filter((t) => t.id !== id));
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">外部触发器配置</h2>
            <p className="text-xs text-white/40 mt-0.5">配置拍照事件触发的 HTTP 回调；本地程序执行已禁用。</p>
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
                onChange={(e) => setForm((f) => ({ ...f, action_type: e.target.value as "http_callback" }))}>
                {ACTION_TYPES.map((a) => (
                  <option key={a} value={a} className={GLASS_SELECT_OPTION_CLASS_NAME}>HTTP回调</option>
                ))}
              </select>
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-white/40">
              回调URL
            </label>
            <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-violet-500/50"
              placeholder="https://example.com/webhook"
              value={form.target}
              onChange={(e) => setForm((f) => ({ ...f, target: e.target.value }))}
            />
          </div>
          <GlowBtn size="sm" variant="primary" onClick={addTrigger} disabled={isSaving || !activeEventId || !authToken} className="w-full">添加并保存触发器</GlowBtn>
        </GlassCard>

        <div className="space-y-3">
          <div className="text-sm font-semibold text-white/80">已配置的触发器</div>
          {!activeEventId || !authToken ? (
            <GlassCard className="p-6 text-center">
              <p className="text-sm text-white/30">请先从真实活动进入现场控制台并保持登录，再配置触发器。</p>
            </GlassCard>
          ) : isLoading ? (
            <GlassCard className="p-6 text-center">
              <p className="text-sm text-white/30">正在读取触发器配置...</p>
            </GlassCard>
          ) : triggers.length === 0 ? (
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
                      HTTP回调
                    </span>
                  </div>
                  <div className="text-xs text-white/40 mt-1 truncate">{t.target}</div>
                </div>
                <div className="flex items-center gap-2">
                  <GlowBtn size="sm" variant={t.enabled ? "ghost" : "outline"} disabled={isSaving} onClick={() => toggleTrigger(t.id)}>
                    {t.enabled ? "禁用" : "启用"}
                  </GlowBtn>
                  <button disabled={isSaving} onClick={() => deleteTrigger(t.id)} className="p-1.5 rounded-lg hover:bg-red-500/10 text-white/40 hover:text-red-400 transition-colors disabled:opacity-40">
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
