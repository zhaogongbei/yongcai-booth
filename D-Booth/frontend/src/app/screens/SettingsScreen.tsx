import { Camera, Printer, Cloud, Globe, Palette, Sun, Star, Sparkles, Lock, Droplets, Zap, Volume2, Mic, Play, Square, KeyRound } from "lucide-react";
import type { ElementType } from "react";
import { useState, useCallback } from "react";
import { GlassCard } from "../components/GlassCard";
import { GLASS_SELECT_OPTION_CLASS_NAME, getGlassSelectClassName } from "../components/glassSelect";
import { useSettings } from "../stores/useSettings";
import { showToast } from "../stores/useToast";
import { attendantPlayer } from "../services/attendantPlayer";
import { previewVirtualAttendantTts } from "../../lib/api";

const LANGUAGE_OPTIONS = [
  { value: "zh-CN", label: "简体中文" },
  { value: "zh-TW", label: "繁體中文" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "ko", label: "한국어" },
];

const POSITION_OPTIONS = [
  { value: "top_left", label: "左上" },
  { value: "top_center", label: "上中" },
  { value: "top_right", label: "右上" },
  { value: "center", label: "居中" },
  { value: "bottom_left", label: "左下" },
  { value: "bottom_center", label: "下中" },
  { value: "bottom_right", label: "右下" },
  { value: "tile", label: "平铺" },
];

const SHARPEN_OPTIONS = [
  { value: "none", label: "无" },
  { value: "low", label: "低" },
  { value: "medium", label: "中" },
  { value: "high", label: "高" },
];

const VOICE_LANGUAGE_OPTIONS = [
  { value: "zh-CN", label: "中文" },
  { value: "en-US", label: "英文" },
];

const VOICE_GENDER_OPTIONS = [
  { value: "female", label: "女声" },
  { value: "male", label: "男声" },
];

const PLAY_TIMINGS = [
  { key: "attract_screen", label: "吸引屏", defaultText: "欢迎光临！点击屏幕开始拍照吧！" },
  { key: "before_countdown", label: "倒计时前", defaultText: "准备拍照！请看镜头，微笑！" },
  { key: "after_capture", label: "拍照完成", defaultText: "拍得真棒！点击下一步继续。" },
  { key: "during_processing", label: "处理中", defaultText: "照片处理中，请稍候..." },
  { key: "after_processing", label: "处理完成", defaultText: "照片处理完成！请查看您的照片。" },
  { key: "session_end", label: "会话结束", defaultText: "感谢您的参与！请取走您的照片。" },
];

function isValidLockPin(pin: string): boolean {
  return /^\d{4,6}$/.test(pin) && pin !== "1234";
}

// ─── Section item types ─────────────────────────────────────────────────────────

interface DeviceToggleItem {
  label: string;
  desc: string;
  icon: ElementType;
  toggleKey: "camera" | "printer" | "cloud";
}

interface LanguageSelectItem {
  label: string;
  desc: string;
  icon: ElementType;
  settingKey: "language";
}

interface BrightnessSliderItem {
  label: string;
  desc: string;
  icon: ElementType;
  settingKey: "brightness";
}

interface StaticInfoItem {
  label: string;
  desc: string;
  icon: ElementType;
}

type SectionItem = DeviceToggleItem | LanguageSelectItem | BrightnessSliderItem | StaticInfoItem;

export function SettingsScreen() {
  const { settings, updateSettings } = useSettings();
  const d = settings.device;
  const ui = settings.ui;
  const wm = settings.watermark;
  const prt = settings.print;
  const lockScreen = settings.lockScreen;
  const hasConfiguredLockPin = isValidLockPin(lockScreen.pin);

  // 虚拟助手本地状态
  const va = settings.virtualAttendant ?? {
    enabled: true,
    language: "zh-CN",
    voice: "female",
    volume: 0.8,
    timings: {} as Record<string, { enabled: boolean; text: string }>,
  };

  const [vaLocal, setVaLocal] = useState<{
    language: "zh-CN" | "en-US";
    voice: "female" | "male";
    volume: number;
  }>({
    language: va.language ?? "zh-CN",
    voice: va.voice ?? "female",
    volume: va.volume ?? 0.8,
  });

  const [previewLoading, setPreviewLoading] = useState(false);
  const [currentLockPin, setCurrentLockPin] = useState("");
  const [newLockPin, setNewLockPin] = useState("");
  const [confirmLockPin, setConfirmLockPin] = useState("");

  const toggleDevice = (key: "camera" | "printer" | "cloud") => {
    updateSettings({ device: { ...d, [key]: !d[key] } });
  };

  const handleVaLanguageChange = (value: "zh-CN" | "en-US") => {
    setVaLocal(p => ({ ...p, language: value }));
    updateSettings({ virtualAttendant: { ...va, language: value } });
    showToast.success(`语音语言已切换为 ${VOICE_LANGUAGE_OPTIONS.find(o => o.value === value)?.label}`);
  };

  const handleVaVoiceChange = (value: "female" | "male") => {
    setVaLocal(p => ({ ...p, voice: value }));
    updateSettings({ virtualAttendant: { ...va, voice: value } });
    showToast.success(`语音已切换为 ${VOICE_GENDER_OPTIONS.find(o => o.value === value)?.label}`);
  };

  const handleVaVolumeChange = (value: number) => {
    setVaLocal(p => ({ ...p, volume: value }));
    updateSettings({ virtualAttendant: { ...va, volume: value } });
    attendantPlayer.setVolume(value);
  };

  const handleTimingToggle = (timing: string) => {
    const timings = { ...(va.timings ?? {}) };
    timings[timing] = {
      enabled: !(timings[timing]?.enabled ?? true),
      text: timings[timing]?.text ?? PLAY_TIMINGS.find(t => t.key === timing)?.defaultText ?? "",
    };
    updateSettings({ virtualAttendant: { ...va, timings } });
  };

  const handleTimingTextChange = (timing: string, text: string) => {
    const timings = { ...(va.timings ?? {}) };
    timings[timing] = {
      enabled: timings[timing]?.enabled ?? true,
      text,
    };
    updateSettings({ virtualAttendant: { ...va, timings } });
  };

  const handlePreviewTTS = useCallback(async (timing: string) => {
    setPreviewLoading(true);
    let audioUrl: string | null = null;
    try {
      const timingItem = PLAY_TIMINGS.find(t => t.key === timing);
      const text = va.timings?.[timing]?.text ?? timingItem?.defaultText ?? "";
      const audioBlob = await previewVirtualAttendantTts({
        text,
        language: vaLocal.language,
        voice: vaLocal.voice,
      });
      audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.volume = vaLocal.volume;
      const cleanup = () => {
        if (audioUrl) {
          URL.revokeObjectURL(audioUrl);
          audioUrl = null;
        }
      };
      audio.addEventListener('ended', () => {
        cleanup();
        setPreviewLoading(false);
      });
      audio.addEventListener('error', () => {
        cleanup();
        setPreviewLoading(false);
        showToast.error("试听失败，请检查TTS服务是否可用");
      });
      await audio.play();
    } catch {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      setPreviewLoading(false);
      showToast.error("试听失败");
    }
  }, [vaLocal, va]);

  const handleSaveLockPin = () => {
    const currentPin = currentLockPin.trim();
    const nextPin = newLockPin.trim();
    const confirmPin = confirmLockPin.trim();

    if (hasConfiguredLockPin && currentPin !== lockScreen.pin) {
      showToast.error("当前 PIN 不正确");
      return;
    }

    if (!isValidLockPin(nextPin)) {
      showToast.error("PIN 必须为 4-6 位数字，且不能使用 1234");
      return;
    }

    if (nextPin !== confirmPin) {
      showToast.error("两次输入的 PIN 不一致");
      return;
    }

    updateSettings({
      lockScreen: {
        ...lockScreen,
        pin: nextPin,
        pinLength: nextPin.length,
      },
    });
    setCurrentLockPin("");
    setNewLockPin("");
    setConfirmLockPin("");
    showToast.success("锁屏 PIN 已保存");
  };

  const sections = [
    {
      title: "设备设置", items: [
        { label: "相机连接", desc: `Canon EOS R5 · ${d.camera ? "已连接" : "已断开"}`, icon: Camera, toggleKey: "camera" as const },
        { label: "打印机配置", desc: `DNP DS620 · ${d.printer ? "就绪" : "未连接"}`, icon: Printer, toggleKey: "printer" as const },
        { label: "云端同步", desc: `${d.cloud ? "自动同步 · 每 5 分钟" : "已关闭"}`, icon: Cloud, toggleKey: "cloud" as const },
      ]
    },
    {
      title: "界面设置", items: [
        { label: "语言", desc: LANGUAGE_OPTIONS.find(o => o.value === ui.language)?.label ?? ui.language, icon: Globe, settingKey: "language" as const },
        { label: "主题颜色", desc: "当前主题由应用默认样式控制", icon: Palette },
        { label: "屏幕亮度", desc: `${ui.brightness}%`, icon: Sun, settingKey: "brightness" as const },
      ]
    },
    {
      title: "账号与订阅", items: [
        { label: "Pro 会员", desc: "未接入订阅管理", icon: Star },
        { label: "AI 积分", desc: "未接入积分账户", icon: Sparkles },
        { label: "账号安全", desc: "请在认证后台管理账号安全", icon: Lock },
      ]
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-5">
      <h2 className="text-xl font-bold text-white">系统设置</h2>
      <div className="grid grid-cols-2 gap-5">
        {sections.map(s => (
          <GlassCard key={s.title} className="p-5">
            <div className="text-sm font-semibold text-white/80 mb-4">{s.title}</div>
            <div className="space-y-4">
              {s.items.map(item => (
                <div key={item.label} className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-violet-500/15 flex items-center justify-center">
                    <item.icon size={17} className="text-violet-400" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm text-white">{item.label}</div>
                    <div className="text-xs text-white/40">{item.desc}</div>
                    {"toggleKey" in item && (
                      <div className="mt-1">
                        <div className={`w-11 h-6 rounded-full relative cursor-pointer ${d[item.toggleKey] ? "bg-violet-500" : "bg-white/10"}`}
                          onClick={() => toggleDevice(item.toggleKey)}>
                          <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${d[item.toggleKey] ? "translate-x-6" : "translate-x-1"}`} />
                        </div>
                      </div>
                    )}
                    {"settingKey" in item && item.settingKey === "brightness" && (
                      <div className="mt-1 flex items-center gap-2">
                        <input
                          type="range"
                          min={20}
                          max={100}
                          value={ui.brightness}
                          onChange={e => updateSettings({ ui: { ...ui, brightness: Number(e.target.value) } })}
                          className="flex-1 h-1 rounded-full appearance-none bg-white/10 cursor-pointer
                            [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-violet-400"
                        />
                        <span className="text-xs text-white/50 w-8 text-right">{ui.brightness}%</span>
                      </div>
                    )}
                    {"settingKey" in item && item.settingKey === "language" && (
                      <div className="mt-1">
                        <select
                          className={getGlassSelectClassName("w-full rounded-lg px-2 py-1 text-xs")}
                          value={ui.language}
                          onChange={e => updateSettings({ ui: { ...ui, language: e.target.value } })}
                        >
                          {LANGUAGE_OPTIONS.map(option => (
                            <option key={option.value} value={option.value} className={GLASS_SELECT_OPTION_CLASS_NAME}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        ))}

        {/* 锁屏 PIN 设置 */}
        <GlassCard className="p-5">
          <div className="text-sm font-semibold text-white/80 mb-4 flex items-center gap-1.5">
            <KeyRound size={15} className="text-violet-400" />
            锁屏 PIN
          </div>
          <div className="space-y-4">
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm text-white">当前状态</div>
                  <div className="text-xs text-white/40">
                    {hasConfiguredLockPin ? `${lockScreen.pinLength} 位 PIN 已配置` : "未配置可用 PIN"}
                  </div>
                </div>
                <div className={`rounded-lg px-2 py-1 text-[10px] ${
                  hasConfiguredLockPin
                    ? "bg-emerald-500/15 text-emerald-300"
                    : "bg-amber-500/15 text-amber-300"
                }`}>
                  {hasConfiguredLockPin ? "可解锁" : "需设置"}
                </div>
              </div>
            </div>

            {hasConfiguredLockPin && (
              <div>
                <div className="text-sm text-white mb-1">当前 PIN</div>
                <input
                  type="password"
                  inputMode="numeric"
                  maxLength={6}
                  value={currentLockPin}
                  onChange={e => setCurrentLockPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-2 text-sm text-white/70 outline-none"
                  autoComplete="current-password"
                />
              </div>
            )}

            <div>
              <div className="text-sm text-white mb-1">新 PIN</div>
              <input
                type="password"
                inputMode="numeric"
                maxLength={6}
                value={newLockPin}
                onChange={e => setNewLockPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-2 text-sm text-white/70 outline-none"
                autoComplete="new-password"
              />
              <div className="mt-1 text-xs text-white/35">4-6 位数字，不能使用 1234</div>
            </div>

            <div>
              <div className="text-sm text-white mb-1">确认 PIN</div>
              <input
                type="password"
                inputMode="numeric"
                maxLength={6}
                value={confirmLockPin}
                onChange={e => setConfirmLockPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-2 text-sm text-white/70 outline-none"
                autoComplete="new-password"
              />
            </div>

            <button
              type="button"
              onClick={handleSaveLockPin}
              className="w-full rounded-xl bg-violet-500 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-400"
            >
              保存锁屏 PIN
            </button>
          </div>
        </GlassCard>

        {/* 水印设置 */}
        <GlassCard className="p-5">
          <div className="text-sm font-semibold text-white/80 mb-4 flex items-center gap-1.5">
            <Droplets size={15} className="text-violet-400" />
            水印设置
          </div>
          <div className="space-y-4">
            {/* 启用开关 */}
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <div className="text-sm text-white">启用水印</div>
                <div className="text-xs text-white/40">为照片添加水印保护</div>
              </div>
              <div className={`w-11 h-6 rounded-full relative cursor-pointer ${wm.enabled ? "bg-violet-500" : "bg-white/10"}`}
                onClick={() => updateSettings({ watermark: { ...wm, enabled: !wm.enabled } })}>
                <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${wm.enabled ? "translate-x-6" : "translate-x-1"}`} />
              </div>
            </div>

            {/* 水印位置 */}
            <div>
              <div className="text-sm text-white mb-1">位置</div>
              <div className="text-xs text-white/40 mb-1.5">选择水印在照片上的位置</div>
              <select
                className={getGlassSelectClassName("w-full rounded-lg px-2 py-1 text-xs")}
                value={wm.position}
                onChange={e => updateSettings({
                  watermark: {
                    ...wm,
                    position: e.target.value as typeof wm.position,
                    tile: e.target.value === "tile",
                  }
                })}
              >
                {POSITION_OPTIONS.map(option => (
                  <option key={option.value} value={option.value} className={GLASS_SELECT_OPTION_CLASS_NAME}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 透明度 */}
            <div>
              <div className="text-sm text-white mb-1 flex justify-between">
                <span>透明度</span>
                <span className="text-violet-400">{wm.opacity}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={wm.opacity}
                onChange={e => updateSettings({ watermark: { ...wm, opacity: Number(e.target.value) } })}
                className="w-full h-1 rounded-full appearance-none bg-white/10 cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-violet-400"
              />
            </div>

            {/* 缩放 */}
            <div>
              <div className="text-sm text-white mb-1 flex justify-between">
                <span>缩放</span>
                <span className="text-violet-400">{wm.scale}%</span>
              </div>
              <input
                type="range"
                min={10}
                max={200}
                value={wm.scale}
                onChange={e => updateSettings({ watermark: { ...wm, scale: Number(e.target.value) } })}
                className="w-full h-1 rounded-full appearance-none bg-white/10 cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-violet-400"
              />
            </div>

            {/* 水印URL */}
            <div>
              <div className="text-sm text-white mb-1">水印图片URL</div>
              <div className="text-xs text-white/40 mb-1.5">上传PNG格式水印图片</div>
              <input
                type="text"
                placeholder="输入水印图片URL..."
                value={wm.watermarkUrl}
                onChange={e => updateSettings({ watermark: { ...wm, watermarkUrl: e.target.value } })}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-xs text-white/70 outline-none"
              />
            </div>
          </div>
        </GlassCard>

        {/* 打印锐化设置 */}
        <GlassCard className="p-5">
          <div className="text-sm font-semibold text-white/80 mb-4 flex items-center gap-1.5">
            <Zap size={15} className="text-violet-400" />
            打印锐化
          </div>
          <div className="space-y-4">
            <div>
              <div className="text-sm text-white mb-1">锐化级别</div>
              <div className="text-xs text-white/40 mb-1.5">针对打印输出进行图像锐化处理</div>
              <select
                className={getGlassSelectClassName("w-full rounded-lg px-2 py-1 text-xs")}
                value={prt.sharpenProfile}
                onChange={e => updateSettings({
                  print: { ...prt, sharpenProfile: e.target.value as typeof prt.sharpenProfile }
                })}
              >
                {SHARPEN_OPTIONS.map(option => (
                  <option key={option.value} value={option.value} className={GLASS_SELECT_OPTION_CLASS_NAME}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="text-xs text-white/30 space-y-1 mt-3 pt-3 border-t border-white/5">
              <p>无 - 不进行锐化处理</p>
              <p>低 - 轻度锐化 (radius=1, percent=50)</p>
              <p>中 - 标准锐化 (radius=2, percent=100)</p>
              <p>高 - 强力锐化 (radius=3, percent=150)</p>
            </div>
          </div>
        </GlassCard>

        {/* 虚拟助手设置 */}
        <GlassCard className="p-5">
          <div className="text-sm font-semibold text-white/80 mb-4 flex items-center gap-1.5">
            <Mic size={15} className="text-violet-400" />
            虚拟助手语音
          </div>
          <div className="space-y-6">
            {/* 基础设置 */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-white">启用语音引导</div>
                  <div className="text-xs text-white/40">在拍照流程中播放语音提示</div>
                </div>
                <div className={`w-11 h-6 rounded-full relative cursor-pointer ${va.enabled ? "bg-violet-500" : "bg-white/10"}`}
                  onClick={() => {
                    const enabled = !va.enabled;
                    updateSettings({ virtualAttendant: { ...va, enabled } });
                    attendantPlayer.setMuted(!enabled);
                  }}>
                  <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${va.enabled ? "translate-x-6" : "translate-x-1"}`} />
                </div>
              </div>

              {/* 语言选择 */}
              <div>
                <div className="text-sm text-white mb-1">语言</div>
                <select
                  className={getGlassSelectClassName("w-full rounded-lg px-2 py-1 text-xs")}
                  value={vaLocal.language}
                  onChange={e => handleVaLanguageChange(e.target.value as "zh-CN" | "en-US")}
                  disabled={!va.enabled}
                >
                  {VOICE_LANGUAGE_OPTIONS.map(option => (
                    <option key={option.value} value={option.value} className={GLASS_SELECT_OPTION_CLASS_NAME}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* 语音选择 */}
              <div>
                <div className="text-sm text-white mb-1">语音</div>
                <select
                  className={getGlassSelectClassName("w-full rounded-lg px-2 py-1 text-xs")}
                  value={vaLocal.voice}
                  onChange={e => handleVaVoiceChange(e.target.value as "female" | "male")}
                  disabled={!va.enabled}
                >
                  {VOICE_GENDER_OPTIONS.map(option => (
                    <option key={option.value} value={option.value} className={GLASS_SELECT_OPTION_CLASS_NAME}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* 音量调节 */}
              <div>
                <div className="text-sm text-white mb-1 flex justify-between">
                  <span>音量</span>
                  <span className="text-violet-400">{Math.round(vaLocal.volume * 100)}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={vaLocal.volume}
                  onChange={e => handleVaVolumeChange(Number(e.target.value))}
                  disabled={!va.enabled}
                  className="w-full h-1 rounded-full appearance-none bg-white/10 cursor-pointer
                    [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-violet-400"
                />
              </div>
            </div>

            {/* 时机配置 */}
            <div className="border-t border-white/5 pt-4">
              <div className="text-sm text-white mb-3">提示时机配置</div>
              <div className="space-y-3">
                {PLAY_TIMINGS.map(timing => {
                  const isEnabled = va.timings?.[timing.key]?.enabled ?? true;
                  const currentText = va.timings?.[timing.key]?.text ?? timing.defaultText;
                  return (
                    <div key={timing.key} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            className={`w-11 h-6 rounded-full relative cursor-pointer ${isEnabled ? "bg-violet-500" : "bg-white/10"}`}
                            onClick={() => handleTimingToggle(timing.key)}
                            disabled={!va.enabled}
                          >
                            <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${isEnabled ? "translate-x-6" : "translate-x-1"}`} />
                          </button>
                          <span className="text-sm text-white/80">{timing.label}</span>
                        </div>
                        <button
                          className="p-1 rounded bg-white/5 hover:bg-white/10 transition-colors"
                          onClick={() => handlePreviewTTS(timing.key)}
                          disabled={!va.enabled || !isEnabled || previewLoading}
                          title="试听"
                        >
                          {previewLoading ? <Square size={12} className="text-violet-400" /> : <Play size={12} className="text-violet-400" />}
                        </button>
                      </div>
                      <input
                        type="text"
                        value={currentText}
                        onChange={e => handleTimingTextChange(timing.key, e.target.value)}
                        disabled={!va.enabled || !isEnabled}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white/70 outline-none disabled:opacity-50"
                        placeholder="输入自定义提示文本..."
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-5">
          <div className="text-sm font-semibold text-white/80 mb-4">关于 AI Booth</div>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
                style={{ background: "linear-gradient(135deg, #7c3aed, #8b5cf6)", boxShadow: "0 0 20px rgba(139,92,246,0.4)" }}>
                <Camera size={22} className="text-white" />
              </div>
              <div>
                <div className="text-base font-bold text-white">AI Booth</div>
                <div className="text-xs text-white/40">v3.2.1 · 专业版</div>
              </div>
            </div>
            {[
              { label: "版本号", value: "3.2.1 (Build 2026.06)" },
              { label: "设备ID", value: "AB-PRO-2026-001" },
              { label: "许可证", value: "商业授权" },
            ].map(i => (
              <div key={i.label} className="flex justify-between py-1.5 border-b border-white/5">
                <span className="text-xs text-white/40">{i.label}</span>
                <span className="text-xs text-white/70">{i.value}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
