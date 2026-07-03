import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft, ImagePlus, Trash2, Upload, Camera, RefreshCw,
  Sliders, Palette, Zap, Layers, MonitorSmartphone, Flashlight
} from "lucide-react";
import { motion } from "motion/react";
import { toast } from "sonner";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import { SliderControl } from "../components/SliderControl";
import { useCaptureFlow } from "../stores/useCaptureFlow";
import type { Screen } from "../types";

// Types for green screen settings
export type GreenScreenMode = "chroma_key" | "ai_removal" | "auto";
export type BackgroundMode = "rotate" | "manual";
export type OutputSize = "template" | "1800x1200" | "max";

export interface GreenScreenBackground {
  id: string;
  name: string;
  backgroundUrl: string;
  overlayUrl?: string;
  order: number;
}

export interface GreenScreenSettings {
  enabled: boolean;
  mode: GreenScreenMode;
  colorToRemove: string;
  sensitivity: number;
  smoothness: number;
  useFlash: boolean;
  backgroundMode: BackgroundMode;
  backgrounds: GreenScreenBackground[];
  outputSize: OutputSize;
  currentBackgroundIndex: number;
}

const defaultSettings: GreenScreenSettings = {
  enabled: true,
  mode: "auto",
  colorToRemove: "#00FF00",
  sensitivity: 50,
  smoothness: 30,
  useFlash: false,
  backgroundMode: "rotate",
  backgrounds: [],
  outputSize: "template",
  currentBackgroundIndex: 0,
};

// Debounce utility
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

export function GreenScreenScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const { eventId } = useCaptureFlow();
  const [settings, setSettings] = useState<GreenScreenSettings>(defaultSettings);
  const [compareMode, setCompareMode] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedImageUrl, setProcessedImageUrl] = useState<string | null>(null);
  const [testPhotoAnalysis, setTestPhotoAnalysis] = useState<any>(null);
  const [selectedBackgroundId, setSelectedBackgroundId] = useState<string | null>(null);

  // Using a sample test photo for preview
  const testPhotoUrl = "/images/scenes/wedding-guests-fun.webp";
  const abortControllerRef = useRef<AbortController | null>(null);
  const previousParamsRef = useRef<string | null>(null);

  // Fetch processed image from backend with debounce
  const fetchProcessedImage = useCallback(async (settings: GreenScreenSettings) => {
    // Cancel previous request if exists
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Skip if same params as previous
    const paramsKey = JSON.stringify(settings);
    if (paramsKey === previousParamsRef.current && processedImageUrl) {
      return;
    }
    previousParamsRef.current = paramsKey;

    setIsProcessing(true);

    try {
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      // Fetch test image
      const response = await fetch(testPhotoUrl);
      const imageBlob = await response.blob();

      // Create form data
      const formData = new FormData();
      formData.append("file", imageBlob, "test.jpg");
      formData.append("settings", JSON.stringify({
        enabled: settings.enabled,
        mode: settings.mode,
        color_to_remove: settings.colorToRemove,
        sensitivity: settings.sensitivity,
        smoothness: settings.smoothness,
        use_flash: settings.useFlash,
        background_mode: settings.backgroundMode,
        output_size: settings.outputSize,
        current_background_index: settings.currentBackgroundIndex,
      }));

      // Add background if exists
      if (settings.backgrounds.length > 0) {
        const bgResponse = await fetch(settings.backgrounds[settings.currentBackgroundIndex].backgroundUrl);
        const bgBlob = await bgResponse.blob();
        formData.append("background_file", bgBlob, "background.jpg");
      }

      // Call preview API
      const apiResponse = await fetch("/api/v1/green-screen/preview", {
        method: "POST",
        body: formData,
        signal: abortController.signal,
      });

      if (!apiResponse.ok) {
        throw new Error("Preview failed");
      }

      const processedBlob = await apiResponse.blob();
      const objectUrl = URL.createObjectURL(processedBlob);

      // Clean up previous object URL
      if (processedImageUrl) {
        URL.revokeObjectURL(processedImageUrl);
      }

      setProcessedImageUrl(objectUrl);
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        return;
      }
      console.error("Green screen processing failed:", error);
      toast.error("处理失败，请检查设置");
      setProcessedImageUrl(null);
    } finally {
      setIsProcessing(false);
      abortControllerRef.current = null;
    }
  }, [processedImageUrl, testPhotoUrl]);

  // Debounced version
  const debouncedFetch = useMemo(
    () => debounce(fetchProcessedImage, 500),
    [fetchProcessedImage]
  );

  // Trigger processing when settings change
  useEffect(() => {
    if (settings.enabled) {
      debouncedFetch(settings);
    }
  }, [settings, debouncedFetch]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (processedImageUrl) {
        URL.revokeObjectURL(processedImageUrl);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [processedImageUrl]);

  // Take test photo
  const takeTestPhoto = useCallback(async () => {
    try {
      setIsProcessing(true);
      toast.info("正在拍摄测试照片...");

      // Simulate camera capture
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Fetch test image
      const response = await fetch(testPhotoUrl);
      const imageBlob = await response.blob();

      // Call analysis API
      const formData = new FormData();
      formData.append("file", imageBlob, "test.jpg");

      const apiResponse = await fetch("/api/v1/green-screen/test-photo", {
        method: "POST",
        body: formData,
      });

      if (!apiResponse.ok) {
        throw new Error("Analysis failed");
      }

      const analysis = await apiResponse.json();
      setTestPhotoAnalysis(analysis);

      // Apply recommended settings
      setSettings(prev => ({
        ...prev,
        mode: analysis.recommended_mode,
        sensitivity: analysis.suggested_sensitivity,
      }));

      toast.success("测试照片分析完成");
    } catch (error) {
      console.error("Test photo analysis failed:", error);
      toast.error("测试照片分析失败");
    } finally {
      setIsProcessing(false);
    }
  }, [testPhotoUrl]);

  // Upload background
  const uploadBackground = useCallback(async () => {
    if (!eventId) {
      toast.error("请先从活动进入拍照流程，再上传绿幕背景");
      return;
    }

    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async (e: any) => {
      const file = e.target.files?.[0];
      if (!file) return;

      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("name", file.name);
        formData.append("event_id", eventId);

        const response = await fetch("/api/v1/green-screen/backgrounds", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error("Upload failed");
        }

        const background = await response.json();
        setSettings(prev => ({
          ...prev,
          backgrounds: [
            ...prev.backgrounds,
            {
              id: background.id,
              name: background.name,
              backgroundUrl: background.background_url,
              overlayUrl: background.overlay_url,
              order: prev.backgrounds.length,
            }
          ]
        }));

        toast.success("背景上传成功");
      } catch (error) {
        console.error("Background upload failed:", error);
        toast.error("背景上传失败");
      }
    };
    input.click();
  }, [eventId]);

  // Delete background
  const deleteBackground = useCallback((id: string) => {
    setSettings(prev => ({
      ...prev,
      backgrounds: prev.backgrounds.filter(bg => bg.id !== id),
      currentBackgroundIndex: 0,
    }));
    setSelectedBackgroundId(null);
    toast.success("背景已删除");
  }, []);

  const displayedImageUrl = processedImageUrl || testPhotoUrl;

  const modeOptions = [
    { value: "auto" as GreenScreenMode, label: "自动模式", description: "根据背景自动选择最佳算法" },
    { value: "chroma_key" as GreenScreenMode, label: "色度键控", description: "传统绿幕抠图，适合纯色背景" },
    { value: "ai_removal" as GreenScreenMode, label: "AI分割", description: "AI人像分割，适合复杂背景" },
  ];

  const outputSizeOptions = [
    { value: "template" as OutputSize, label: "模板尺寸" },
    { value: "1800x1200" as OutputSize, label: "1800×1200" },
    { value: "max" as OutputSize, label: "原始尺寸" },
  ];

  const backgroundModeOptions = [
    { value: "rotate" as BackgroundMode, label: "自动轮换" },
    { value: "manual" as BackgroundMode, label: "手动选择" },
  ];

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left sidebar - mode selection */}
      <div className="w-64 border-r border-white/5 flex flex-col p-4 gap-4 overflow-y-auto">
        <div className="flex items-center gap-2 mb-2">
          <button onClick={() => navigate("settings")} className="text-xs text-white/40 hover:text-white/70 flex items-center gap-1">
            <ArrowLeft size={14} />
            返回
          </button>
          <span className="text-xs text-white/70">绿幕设置</span>
        </div>

        <div className="space-y-4">
          <div>
            <div className="text-xs font-semibold text-white/60 mb-3 uppercase tracking-wider">工作模式</div>
            <div className="space-y-2">
              {modeOptions.map(mode => (
                <button
                  key={mode.value}
                  onClick={() => setSettings(prev => ({ ...prev, mode: mode.value }))}
                  className={`w-full p-3 rounded-lg text-left transition-all ${
                    settings.mode === mode.value
                      ? "bg-violet-500/20 border border-violet-500/50"
                      : "bg-white/5 border border-transparent hover:bg-white/10"
                  }`}
                >
                  <div className="text-xs font-medium text-white/80 mb-1">{mode.label}</div>
                  <div className="text-[10px] text-white/40">{mode.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Enable toggle */}
          <div className="flex items-center justify-between py-2">
            <span className="text-xs text-white/60">启用绿幕功能</span>
            <button
              onClick={() => setSettings(prev => ({ ...prev, enabled: !prev.enabled }))}
              className={`w-10 h-5 rounded-full transition-all relative ${
                settings.enabled ? "bg-violet-500" : "bg-white/10"
              }`}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  settings.enabled ? "translate-x-5" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>

          {/* Test photo button */}
          <GlowBtn
            variant="primary"
            size="sm"
            onClick={takeTestPhoto}
            disabled={isProcessing}
            className="w-full"
          >
            <Camera size={14} />
            拍摄测试照片
          </GlowBtn>

          {/* Analysis results */}
          {testPhotoAnalysis && (
            <GlassCard className="p-3 space-y-2">
              <div className="text-xs font-semibold text-white/70">分析结果</div>
              <div className="text-[10px] text-white/50 space-y-1">
                <div>背景复杂度: {(testPhotoAnalysis.complexity_score * 100).toFixed(0)}%</div>
                <div>推荐模式: {testPhotoAnalysis.recommended_mode === "chroma_key" ? "色度键控" : "AI分割"}</div>
                <div>绿色背景: {testPhotoAnalysis.is_green_background ? "是" : "否"}</div>
                <div>推荐灵敏度: {testPhotoAnalysis.suggested_sensitivity}</div>
              </div>
              <div className="text-[10px] text-violet-400 mt-2">
                {testPhotoAnalysis.suggestions?.map((s: string, i: number) => (
                  <div key={i}>• {s}</div>
                ))}
              </div>
            </GlassCard>
          )}
        </div>
      </div>

      {/* Main preview area */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between px-4 py-2 border-b border-white/5">
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/70">实时预览</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/40">对比模式</span>
            <button
              onClick={() => setCompareMode(!compareMode)}
              className={`w-10 h-5 rounded-full transition-all relative ${
                compareMode ? "bg-violet-500" : "bg-white/10"
              }`}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  compareMode ? "translate-x-5" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>
        </div>

        {/* Preview */}
        <div className="flex-1 relative flex items-center justify-center bg-black/40 p-4">
          <div className="relative h-full max-h-full aspect-[3/4] overflow-hidden rounded-2xl">
            {/* Processing overlay */}
            {isProcessing && (
              <div className="absolute inset-0 z-10 bg-black/40 backdrop-blur-sm flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-12 h-12 rounded-full border-4 border-violet-500/30 border-t-violet-500 animate-spin" />
                  <span className="text-xs text-white/70">处理中...</span>
                </div>
              </div>
            )}

            {compareMode ? (
              <div className="relative w-full h-full">
                <img
                  src={testPhotoUrl}
                  alt="original"
                  className="absolute inset-0 w-full h-full object-cover"
                  style={{ clipPath: "inset(0 50% 0 0)" }}
                  loading="lazy"
                />
                <img
                  src={displayedImageUrl}
                  alt="processed"
                  className="absolute inset-0 w-full h-full object-cover"
                  style={{ clipPath: "inset(0 0 0 50%)" }}
                  loading="lazy"
                />
                <div className="absolute top-0 bottom-0 left-1/2 w-0.5 bg-white/80" />
                <div className="absolute top-3 left-3 bg-black/60 text-white text-xs px-2 py-0.5 rounded">原图</div>
                <div className="absolute top-3 right-3 bg-violet-500/80 text-white text-xs px-2 py-0.5 rounded">处理后</div>
              </div>
            ) : (
              <img
                src={displayedImageUrl}
                alt="green screen preview"
                className="w-full h-full object-cover"
                loading="lazy"
              />
            )}
          </div>
        </div>

        {/* Background thumbnails strip */}
        <div className="border-t border-white/5 px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/40">背景库</span>
              <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded text-white/40">
                {settings.backgrounds.length} 个背景
              </span>
            </div>
            <button
              onClick={uploadBackground}
              className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1"
            >
              <Upload size={12} />
              上传背景
            </button>
          </div>
          <div className="flex gap-3 overflow-x-auto pb-1">
            {settings.backgrounds.map((bg, index) => (
              <div
                key={bg.id}
                onClick={() => {
                  setSelectedBackgroundId(bg.id);
                  setSettings(prev => ({ ...prev, currentBackgroundIndex: index }));
                }}
                className={`flex-shrink-0 flex flex-col items-center gap-1.5 cursor-pointer group relative`}
              >
                <div
                  className={`w-16 h-16 rounded-xl overflow-hidden border-2 transition-all ${
                    settings.currentBackgroundIndex === index
                      ? "border-violet-500"
                      : "border-transparent group-hover:border-white/30"
                  }`}
                >
                  <img
                    src={bg.backgroundUrl}
                    alt={bg.name}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                </div>
                <span className={`text-[10px] ${
                  settings.currentBackgroundIndex === index ? "text-violet-400" : "text-white/40"
                }`}>
                  {bg.name.length > 10 ? `${bg.name.slice(0, 10)}...` : bg.name}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteBackground(bg.id);
                  }}
                  className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Trash2 size={8} className="text-white" />
                </button>
              </div>
            ))}

            {/* Add background button */}
            <button
              onClick={uploadBackground}
              className="flex-shrink-0 w-16 h-16 rounded-xl border-2 border-dashed border-white/20 hover:border-violet-500/50 flex items-center justify-center transition-colors"
            >
              <ImagePlus size={20} className="text-white/30 hover:text-violet-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Right panel - settings */}
      <GlassCard className="w-64 rounded-none border-l border-white/5 p-4 space-y-4 overflow-y-auto">
        {/* Chroma key settings */}
        {settings.mode === "chroma_key" && (
          <>
            <div>
              <div className="text-xs font-semibold text-white/60 mb-3 uppercase tracking-wider">色度键控设置</div>

              <div className="space-y-3">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-white/40">抠图颜色</span>
                    <input
                      type="color"
                      value={settings.colorToRemove}
                      onChange={(e) => setSettings(prev => ({ ...prev, colorToRemove: e.target.value }))}
                      className="w-6 h-6 rounded bg-transparent cursor-pointer"
                    />
                  </div>
                  <div
                    className="w-full h-6 rounded-lg border border-white/10"
                    style={{ backgroundColor: settings.colorToRemove }}
                  />
                </div>

                <SliderControl
                  label="灵敏度"
                  value={settings.sensitivity}
                  icon={Palette}
                  onChange={(v) => setSettings(prev => ({ ...prev, sensitivity: v }))}
                  min={0}
                  max={100}
                />

                <SliderControl
                  label="平滑度"
                  value={settings.smoothness}
                  icon={Sliders}
                  onChange={(v) => setSettings(prev => ({ ...prev, smoothness: v }))}
                  min={0}
                  max={100}
                />

                <div className="flex items-center justify-between py-1">
                  <div className="flex items-center gap-1.5">
                    <Flashlight size={12} className="text-white/40" />
                    <span className="text-xs text-white/40">闪光灯模式</span>
                  </div>
                  <button
                    onClick={() => setSettings(prev => ({ ...prev, useFlash: !prev.useFlash }))}
                    className={`w-8 h-4 rounded-full transition-all relative ${
                      settings.useFlash ? "bg-violet-500" : "bg-white/10"
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${
                        settings.useFlash ? "translate-x-4" : "translate-x-0.5"
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>
          </>
        )}

        {/* AI removal settings */}
        {settings.mode === "ai_removal" && (
          <div>
            <div className="text-xs font-semibold text-white/60 mb-3 uppercase tracking-wider">AI分割设置</div>
            <div className="text-xs text-white/50 space-y-2">
              <p>• 使用MediaPipe人像分割模型</p>
              <p>• CPU上约3秒/张处理速度</p>
              <p>• 适合复杂背景和非绿幕场景</p>
              <p className="text-amber-400/70 mt-2">提示：对于纯色绿幕背景，色度键控模式速度更快，效果更好</p>
            </div>
          </div>
        )}

        {/* Background settings */}
        <div>
          <div className="text-xs font-semibold text-white/60 mb-3 uppercase tracking-wider">背景设置</div>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <span className="text-xs text-white/40">背景模式</span>
              <div className="flex gap-1">
                {backgroundModeOptions.map(option => (
                  <button
                    key={option.value}
                    onClick={() => setSettings(prev => ({ ...prev, backgroundMode: option.value }))}
                    className={`flex-1 py-1.5 rounded-lg text-[10px] transition-colors ${
                      settings.backgroundMode === option.value
                        ? "bg-violet-500 text-white"
                        : "bg-white/5 text-white/40 hover:bg-white/10"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs text-white/40">输出尺寸</span>
              <div className="flex flex-wrap gap-1">
                {outputSizeOptions.map(option => (
                  <button
                    key={option.value}
                    onClick={() => setSettings(prev => ({ ...prev, outputSize: option.value }))}
                    className={`flex-1 py-1.5 rounded-lg text-[10px] transition-colors ${
                      settings.outputSize === option.value
                        ? "bg-violet-500 text-white"
                        : "bg-white/5 text-white/40 hover:bg-white/10"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Save button */}
        <div className="pt-4">
          <GlowBtn
            variant="primary"
            size="sm"
            onClick={() => {
              toast.error("绿幕设置保存暂不可用");
            }}
            className="w-full"
          >
            <RefreshCw size={14} />
            保存设置
          </GlowBtn>
        </div>
      </GlassCard>
    </div>
  );
}
