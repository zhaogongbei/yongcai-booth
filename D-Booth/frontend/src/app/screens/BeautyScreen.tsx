import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import {
  Sparkles, Users, Eye, Sun, Zap, Sliders, Star, Heart,
  ArrowLeft, ImagePlus, RotateCcw, Download, Printer, Share2,
  Trash2
} from "lucide-react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import { SliderControl } from "../components/SliderControl";
import { StickerOverlay, type Sticker } from "../components/StickerOverlay";
import { useCaptureFlow } from "../stores/useCaptureFlow";
import { useResponsive } from "../hooks/useResponsive";
import type { Screen } from "../types";
import type { BeautyParams as BeautyParamsType } from "../../lib/api";
import { processBeautyImage, resolveBackendUrl } from "../../lib/api";
import { showToast } from "../stores/useToast";
import {
  BEAUTY_PRESETS, DEFAULT_BEAUTY_VALUES, BEAUTY_FALLBACK_IMAGE, BEAUTY_PRESET_AVATARS,
  DEFAULT_PROPS
} from "../constants";

type Tool = "美颜" | "贴纸";

const defaultBeautyValues = DEFAULT_BEAUTY_VALUES;

const FALLBACK_IMAGE = BEAUTY_FALLBACK_IMAGE;

function resolvePhotoUrl(url?: string): string {
  if (!url) return FALLBACK_IMAGE;
  if (/^(blob:|data:|https?:\/\/)/i.test(url)) return url;
  if (/^\/?(api\/v1\/media|uploads)\//i.test(url)) return resolveBackendUrl(url);
  return url;
}

function isImageStickerSource(src: string): boolean {
  return /^(blob:|data:|https?:\/\/|\/)/i.test(src);
}

async function loadImageFromBlob(blob: Blob): Promise<HTMLImageElement> {
  const objectUrl = URL.createObjectURL(blob);
  try {
    return await new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error("图片加载失败"));
      image.src = objectUrl;
    });
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

async function loadImageFromUrl(url: string): Promise<HTMLImageElement> {
  const response = await fetch(resolvePhotoUrl(url));
  if (!response.ok) {
    throw new Error(`图片加载失败: ${response.status}`);
  }
  return loadImageFromBlob(await response.blob());
}

async function renderStickerOutput(baseUrl: string, stickers: Sticker[]): Promise<Blob> {
  const baseImage = await loadImageFromUrl(baseUrl);
  const width = baseImage.naturalWidth || baseImage.width;
  const height = baseImage.naturalHeight || baseImage.height;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("无法创建图片画布");

  ctx.drawImage(baseImage, 0, 0, width, height);

  for (const sticker of stickers) {
    const size = Math.max(32, Math.round(Math.min(width, height) * 0.16 * sticker.scale));
    const x = sticker.x * width;
    const y = sticker.y * height;
    ctx.save();
    ctx.globalAlpha = sticker.opacity;
    ctx.translate(x, y);
    ctx.rotate((sticker.rotation * Math.PI) / 180);
    ctx.scale(sticker.flipH ? -1 : 1, sticker.flipV ? -1 : 1);

    if (isImageStickerSource(sticker.imageUrl)) {
      try {
        const stickerImage = await loadImageFromUrl(sticker.imageUrl);
        ctx.drawImage(stickerImage, -size / 2, -size / 2, size, size);
      } catch {
        // Keep the photo export usable even if a decorative asset fails to load.
      }
    } else {
      ctx.font = `${size}px "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(sticker.imageUrl, 0, 0);
    }

    ctx.restore();
  }

  return await new Promise((resolve, reject) => {
    canvas.toBlob(blob => {
      if (blob) {
        resolve(blob);
        return;
      }
      reject(new Error("导出图片失败"));
    }, "image/jpeg", 0.92);
  });
}

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

export function BeautyScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const { isMobile, isDesktop } = useResponsive();
  const [compareMode, setCompareMode] = useState(false);
  const [activeTool, setActiveTool] = useState<Tool>("美颜");
  const [selectedPreset, setSelectedPreset] = useState(1);
  const [beautyLevel, setBeautyLevel] = useState<"light" | "natural" | "high">("natural");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [processedImageUrl, setProcessedImageUrl] = useState<string | null>(null);
  const [processedImageBlob, setProcessedImageBlob] = useState<Blob | null>(null);

  const [smooth, setSmooth] = useState<number>(defaultBeautyValues.smooth);
  const [thinFace, setThinFace] = useState<number>(defaultBeautyValues.thinFace);
  const [bigEye, setBigEye] = useState<number>(defaultBeautyValues.bigEye);
  const [eyeLight, setEyeLight] = useState<number>(defaultBeautyValues.eyeLight);
  const [whiten, setWhiten] = useState<number>(defaultBeautyValues.whiten);
  const [acne, setAcne] = useState<number>(defaultBeautyValues.acne);
  const [nasolabial, setNasolabial] = useState<number>(defaultBeautyValues.nasolabial);
  const [teethWhiten, setTeethWhiten] = useState<number>(defaultBeautyValues.teethWhiten);
  const [lipColor, setLipColor] = useState<number>(defaultBeautyValues.lipColor);

  // Sticker state
  const [stickers, setStickers] = useState<Sticker[]>([]);
  const [selectedStickerId, setSelectedStickerId] = useState<string | null>(null);
  const [selectedStickerCategory, setSelectedStickerCategory] = useState<string>("全部");

  const { selectedPhoto, authToken, addPhoto } = useCaptureFlow();
  const photoUrl = useMemo(() => resolvePhotoUrl(selectedPhoto?.url), [selectedPhoto?.url]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const previousParamsRef = useRef<string | null>(null);

  // Build beauty params object
  const beautyParams: BeautyParamsType = useMemo(() => ({
    smooth,
    whiten,
    thinFace,
    bigEye,
    eyeLight,
    acne,
    nasolabial,
    teethWhiten,
    lipColor,
  }), [smooth, whiten, thinFace, bigEye, eyeLight, acne, nasolabial, teethWhiten, lipColor]);

  // Fetch processed image from backend with debounce
  const fetchProcessedImage = useCallback(async (params: BeautyParamsType) => {
    // Cancel previous request if exists
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Skip if same params as previous
    const paramsKey = JSON.stringify(params);
    if (paramsKey === previousParamsRef.current && processedImageUrl) {
      return;
    }
    previousParamsRef.current = paramsKey;

    if (!selectedPhoto?.url) {
      return;
    }

    setIsProcessing(true);

    try {
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      // Fetch image blob
      const response = await fetch(resolvePhotoUrl(selectedPhoto.url));
      const imageBlob = await response.blob();

      // Process with beauty API
      const processedBlob = await processBeautyImage(
        imageBlob,
        params,
        abortController.signal,
        authToken ?? undefined
      );

      // Create object URL for processed image
      const objectUrl = URL.createObjectURL(processedBlob);

      // Clean up previous object URL
      if (processedImageUrl) {
        URL.revokeObjectURL(processedImageUrl);
      }

      setProcessedImageBlob(processedBlob);
      setProcessedImageUrl(objectUrl);
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        // Request was cancelled, ignore
        return;
      }
      console.error("Beauty processing failed:", error);
      // Fallback to original image on error
      setProcessedImageBlob(null);
      setProcessedImageUrl(null);
    } finally {
      setIsProcessing(false);
      abortControllerRef.current = null;
    }
  }, [selectedPhoto, processedImageUrl, authToken]);

  // Debounced version of fetchProcessedImage
  const debouncedFetch = useMemo(
    () => debounce(fetchProcessedImage, 300),
    [fetchProcessedImage]
  );

  // Trigger processing when params change
  useEffect(() => {
    if (activeTool === "美颜") {
      debouncedFetch(beautyParams);
    }
  }, [beautyParams, debouncedFetch, activeTool]);

  // Clean up object URL and abort requests on unmount
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

  useEffect(() => {
    previousParamsRef.current = null;
    setProcessedImageBlob(null);
    setProcessedImageUrl(currentUrl => {
      if (currentUrl) URL.revokeObjectURL(currentUrl);
      return null;
    });
  }, [selectedPhoto?.id]);

  const displayedImageUrl = processedImageUrl || photoUrl;

  const presets = BEAUTY_PRESETS;

  const beautyControls = [
    { label: "皮肤磨皮", value: smooth, icon: Sparkles, onChange: setSmooth },
    { label: "瘦脸", value: thinFace, icon: Users, onChange: setThinFace },
    { label: "大眼", value: bigEye, icon: Eye, onChange: setBigEye },
    { label: "眼神光", value: eyeLight, icon: Sun, onChange: setEyeLight },
    { label: "美白", value: whiten, icon: Sun, onChange: setWhiten },
    { label: "祛痘", value: acne, icon: Zap, onChange: setAcne },
    { label: "祛法令纹", value: nasolabial, icon: Sliders, onChange: setNasolabial },
    { label: "牙齿美白", value: teethWhiten, icon: Star, onChange: setTeethWhiten },
    { label: "唇色", value: lipColor, icon: Heart, onChange: setLipColor },
  ];

  const resetBeauty = () => {
    setSmooth(defaultBeautyValues.smooth);
    setThinFace(defaultBeautyValues.thinFace);
    setBigEye(defaultBeautyValues.bigEye);
    setEyeLight(defaultBeautyValues.eyeLight);
    setWhiten(defaultBeautyValues.whiten);
    setAcne(defaultBeautyValues.acne);
    setNasolabial(defaultBeautyValues.nasolabial);
    setTeethWhiten(defaultBeautyValues.teethWhiten);
    setLipColor(defaultBeautyValues.lipColor);
    setBeautyLevel("natural");
    setSelectedPreset(1);
    previousParamsRef.current = null;
    setProcessedImageBlob(null);
    setProcessedImageUrl(currentUrl => {
      if (currentUrl) URL.revokeObjectURL(currentUrl);
      return null;
    });
  };

  const continueWithBeautyResult = async (nextScreen: Screen) => {
    if (isProcessing) {
      showToast.info("请等待当前美颜处理完成");
      return;
    }

    if (!selectedPhoto) {
      navigate("camera");
      return;
    }

    const needsStickerRender = stickers.length > 0;
    if (!processedImageBlob && !needsStickerRender) {
      navigate(nextScreen);
      return;
    }

    try {
      setIsCommitting(true);
      const outputBlob = needsStickerRender
        ? await renderStickerOutput(displayedImageUrl, stickers)
        : processedImageBlob;
      if (!outputBlob) {
        navigate(nextScreen);
        return;
      }
      await addPhoto({
        blob: outputBlob,
        filter: needsStickerRender ? "beauty-sticker" : "beauty",
        mediaType: selectedPhoto.mediaType,
      });
      showToast.success(needsStickerRender ? "已应用美颜和贴纸" : "已应用美颜结果");
      navigate(nextScreen);
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "应用美颜结果失败");
    } finally {
      setIsCommitting(false);
    }
  };

  // Apply preset
  const applyPreset = (index: number) => {
    setSelectedPreset(index);
    // Preset parameter mapping (matches backend presets)
    const presets = [
      { smooth: 0, whiten: 0, thinFace: 0, bigEye: 0, eyeLight: 0, acne: 0, nasolabial: 0, teethWhiten: 0, lipColor: 0 }, // 原图
      { smooth: 60, whiten: 40, thinFace: 30, bigEye: 20, eyeLight: 30, acne: 20, nasolabial: 25, teethWhiten: 30, lipColor: 15 }, // 自然
      { smooth: 55, whiten: 55, thinFace: 35, bigEye: 30, eyeLight: 40, acne: 25, nasolabial: 30, teethWhiten: 40, lipColor: 20 }, // 清新
      { smooth: 70, whiten: 85, thinFace: 40, bigEye: 35, eyeLight: 45, acne: 30, nasolabial: 35, teethWhiten: 50, lipColor: 10 }, // 白皙
      { smooth: 50, whiten: 35, thinFace: 50, bigEye: 55, eyeLight: 60, acne: 15, nasolabial: 20, teethWhiten: 35, lipColor: 55 }, // 元气
      { smooth: 65, whiten: 30, thinFace: 45, bigEye: 25, eyeLight: 35, acne: 40, nasolabial: 45, teethWhiten: 25, lipColor: 25 }, // 高级
      { smooth: 45, whiten: 20, thinFace: 25, bigEye: 15, eyeLight: 20, acne: 10, nasolabial: 10, teethWhiten: 15, lipColor: 20 }, // 胶片
      { smooth: 85, whiten: 60, thinFace: 30, bigEye: 40, eyeLight: 50, acne: 35, nasolabial: 40, teethWhiten: 45, lipColor: 35 }, // 奶油
      { smooth: 75, whiten: 70, thinFace: 65, bigEye: 60, eyeLight: 55, acne: 45, nasolabial: 50, teethWhiten: 55, lipColor: 45 }, // 韩系
      { smooth: 60, whiten: 50, thinFace: 40, bigEye: 50, eyeLight: 45, acne: 30, nasolabial: 35, teethWhiten: 40, lipColor: 50 }, // 日系
    ];
    if (index < presets.length) {
      const preset = presets[index];
      setSmooth(preset.smooth);
      setWhiten(preset.whiten);
      setThinFace(preset.thinFace);
      setBigEye(preset.bigEye);
      setEyeLight(preset.eyeLight);
      setAcne(preset.acne);
      setNasolabial(preset.nasolabial);
      setTeethWhiten(preset.teethWhiten);
      setLipColor(preset.lipColor);
    }
  };

  const tools: { icon: React.ElementType; label: Tool }[] = [
    { icon: Sparkles, label: "美颜" },
    { icon: ImagePlus, label: "贴纸" },
  ];

  const levelLabels: { key: "light" | "natural" | "high"; label: string }[] = [
    { key: "light", label: "轻" },
    { key: "natural", label: "自然" },
    { key: "high", label: "高" },
  ];

  const stickerCategories = useMemo(
    () => ["全部", ...Array.from(new Set(DEFAULT_PROPS.map(prop => prop.category)))],
    []
  );

  // Filter props by category
  const filteredProps = useMemo(() => {
    if (selectedStickerCategory === "全部") return DEFAULT_PROPS;
    return DEFAULT_PROPS.filter(p => p.category === selectedStickerCategory);
  }, [selectedStickerCategory]);

  // Add sticker to photo
  const addSticker = (prop: (typeof DEFAULT_PROPS)[number]) => {
    const newSticker: Sticker = {
      id: `sticker-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      propId: prop.id,
      imageUrl: prop.imageUrl,
      x: 0.5, // Center of photo
      y: 0.5, // Center of photo
      scale: 1.0,
      rotation: 0,
      flipH: false,
      flipV: false,
      opacity: 1.0
    };
    setStickers([...stickers, newSticker]);
    setSelectedStickerId(newSticker.id);
  };

  // Delete sticker
  const deleteSticker = (stickerId: string) => {
    setStickers(stickers.filter(s => s.id !== stickerId));
    if (selectedStickerId === stickerId) {
      setSelectedStickerId(null);
    }
  };

  // Clear all stickers
  const clearAllStickers = () => {
    setStickers([]);
    setSelectedStickerId(null);
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left sidebar tools (desktop only) */}
      {isDesktop && (
        <div className="w-16 border-r border-white/5 flex flex-col items-center gap-3 py-4">
          {tools.map(t => (
            <button key={t.label} onClick={() => setActiveTool(t.label)}
              className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-all ${activeTool === t.label ? "bg-violet-500/20" : "hover:bg-white/5"}`}>
              <t.icon size={18} className={activeTool === t.label ? "text-violet-400" : "text-white/40"} />
              <span className={`text-[9px] ${activeTool === t.label ? "text-violet-400" : "text-white/40"}`}>{t.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Main editor area */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between px-4 py-2 border-b border-white/5">
          <div className="flex items-center gap-2">
            <button onClick={() => navigate("camera")} className="text-xs text-white/40 hover:text-white/70 flex items-center gap-1">
              <ArrowLeft size={14} />
              返回
            </button>
            <span className="text-xs text-white/20">/</span>
            <span className="text-xs text-white/70">AI 美颜编辑器</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/40">对比模式</span>
            <button onClick={() => setCompareMode(!compareMode)}
              className={`w-10 h-5 rounded-full transition-all relative ${compareMode ? "bg-violet-500" : "bg-white/10"}`}>
              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${compareMode ? "translate-x-5" : "translate-x-0.5"}`} />
            </button>
          </div>
        </div>

        {/* Photo preview */}
        <div className="flex-1 relative flex items-center justify-center bg-black/40 p-4">
          <div className="relative h-full max-h-full aspect-[3/4] overflow-hidden rounded-2xl">
            {/* Processing skeleton overlay */}
            {isProcessing && (
              <div className="absolute inset-0 z-10 bg-black/40 backdrop-blur-sm flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-12 h-12 rounded-full border-4 border-violet-500/30 border-t-violet-500 animate-spin" />
                  <span className="text-xs text-white/70">美颜处理中...</span>
                </div>
              </div>
            )}

            {activeTool === "贴纸" ? (
              <StickerOverlay
                photoUrl={displayedImageUrl}
                stickers={stickers}
                onChange={setStickers}
                onStickerSelect={setSelectedStickerId}
                selectedStickerId={selectedStickerId}
              />
            ) : compareMode ? (
              <div className="relative w-full h-full">
                <img src={photoUrl}
                  alt="original" className="absolute inset-0 w-full h-full object-cover" style={{ clipPath: "inset(0 50% 0 0)" }} loading="lazy" />
                <img src={displayedImageUrl}
                  alt="beauty" className="absolute inset-0 w-full h-full object-cover" style={{ clipPath: "inset(0 0 0 50%)" }} loading="lazy" />
                <div className="absolute top-0 bottom-0 left-1/2 w-0.5 bg-white/80" />
                <div className="absolute top-3 left-3 bg-black/60 text-white text-xs px-2 py-0.5 rounded">原图</div>
                <div className="absolute top-3 right-3 bg-violet-500/80 text-white text-xs px-2 py-0.5 rounded">调整后</div>
              </div>
            ) : (
              <img src={displayedImageUrl}
                alt="beauty preview" className="w-full h-full object-cover" loading="lazy" />
            )}
          </div>
          <div className="absolute bottom-6 right-6 flex gap-2">
            <GlowBtn size="sm" variant="ghost" onClick={() => navigate("camera")}><RotateCcw size={13} />重拍</GlowBtn>
            {activeTool === "贴纸" ? (
              <>
                <GlowBtn size="sm" variant="ghost" onClick={clearAllStickers}><RotateCcw size={13} />清除贴纸</GlowBtn>
              </>
            ) : (
              <GlowBtn size="sm" variant="ghost" onClick={resetBeauty}><RotateCcw size={13} />重置</GlowBtn>
            )}
            <GlowBtn size="sm" variant="primary" disabled={isProcessing || isCommitting} onClick={() => void continueWithBeautyResult("print")}><Printer size={13} />打印照片</GlowBtn>
            <GlowBtn size="sm" variant="accent" disabled={isProcessing || isCommitting} onClick={() => void continueWithBeautyResult("sharing")}><Share2 size={13} />分享照片</GlowBtn>
          </div>
        </div>

        {/* Presets strip / Sticker category selector */}
        <div className="border-t border-white/5 px-4 py-3">
          {activeTool === "贴纸" ? (
            <>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-white/40">贴纸分类</span>
                <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded text-white/40">
                  共 {filteredProps.length} 个
                </span>
              </div>
              <div className="flex gap-2 overflow-x-auto pb-1 mb-2">
                {stickerCategories.map(cat => (
                  <button key={cat} onClick={() => setSelectedStickerCategory(cat)}
                    className={`flex-shrink-0 px-3 py-1 rounded-lg text-xs transition-all ${selectedStickerCategory === cat ? "bg-violet-500 text-white" : "bg-white/5 text-white/40 hover:bg-white/10"}`}>
                    {cat}
                  </button>
                ))}
              </div>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {filteredProps.map(prop => (
                  <div key={prop.id} onClick={() => addSticker(prop)}
                    className="flex-shrink-0 flex flex-col items-center gap-1.5 cursor-pointer group">
                    <div className="w-14 h-14 rounded-xl overflow-hidden border-2 border-transparent group-hover:border-white/30 transition-all flex items-center justify-center bg-white/5">
                      <span className="text-2xl">{prop.imageUrl}</span>
                    </div>
                    <span className="text-[10px] text-white/40 group-hover:text-white/70">{prop.name}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-white/40">美颜预设</span>
                <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded text-white/40">手动调节</span>
              </div>
              <div className="flex gap-3 overflow-x-auto pb-1">
                {presets.map((p, i) => {
                  const avatarImages = BEAUTY_PRESET_AVATARS;
                  return (
                    <div key={p} onClick={() => applyPreset(i)}
                      className="flex-shrink-0 flex flex-col items-center gap-1.5 cursor-pointer group">
                      <div className={`w-14 h-14 rounded-xl overflow-hidden border-2 transition-all ${i === selectedPreset ? "border-violet-500" : "border-transparent group-hover:border-white/30"}`}>
                        <img src={avatarImages[i]}
                          alt={p} className="w-full h-full object-cover" style={{ filter: i > 0 ? `saturate(${0.8 + i * 0.1}) brightness(${0.9 + i * 0.03})` : "none" }} loading="lazy" />
                      </div>
                      <span className={`text-[10px] ${i === selectedPreset ? "text-violet-400" : "text-white/40"}`}>{p}</span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Right panel (desktop only) */}
      {isDesktop && (
        <GlassCard className="w-56 rounded-none border-l border-white/5 p-4 space-y-3 overflow-y-auto">
          {activeTool === "贴纸" ? (
          <>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white/80">已添加贴纸</span>
              <button onClick={clearAllStickers} className="text-xs text-red-400 hover:text-red-300">
                清除全部
              </button>
            </div>
            {stickers.length === 0 ? (
              <div className="text-xs text-white/20 text-center py-8">
                点击下方贴纸添加到照片
              </div>
            ) : (
              <div className="space-y-2">
                {stickers.map(sticker => {
                  const prop = DEFAULT_PROPS.find(p => p.id === sticker.propId);
                  return (
                    <div
                      key={sticker.id}
                      onClick={() => setSelectedStickerId(sticker.id)}
                      className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-all ${selectedStickerId === sticker.id ? "bg-violet-500/20 border border-violet-500/50" : "bg-white/5 border border-transparent hover:bg-white/10"}`}
                    >
                      <span className="text-lg">{prop?.imageUrl || "?"}</span>
                      <span className="text-xs text-white/60 flex-1 truncate">{prop?.name || "未知"}</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteSticker(sticker.id); }}
                        className="text-white/40 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white/80">美颜调节</span>
              <button onClick={resetBeauty} className="text-xs text-violet-400 hover:text-violet-300">重置</button>
            </div>
            <div className="space-y-3">
              {beautyControls.map(c => (
                <SliderControl key={c.label} label={c.label} value={c.value} icon={c.icon} onChange={c.onChange} />
              ))}
            </div>
            <div className="pt-2">
              <div className="text-xs text-white/40 mb-2">美颜强度</div>
              <div className="flex gap-2">
                {levelLabels.map(l => (
                  <button key={l.key} onClick={() => setBeautyLevel(l.key)}
                    className={`flex-1 py-1.5 rounded-lg text-xs ${beautyLevel === l.key ? "bg-violet-500 text-white" : "bg-white/5 text-white/40"}`}>{l.label}</button>
                ))}
              </div>
            </div>
          </>
        )}
        </GlassCard>
      )}
    </div>
  );
}
