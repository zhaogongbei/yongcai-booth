import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Image, Timer, Sliders, CircleDot, Grid3X3, Wand2, Printer,
  Sparkles, RotateCcw, Video, Film, Zap, Square, Play, Camera, Layers, Wrench, LayoutTemplate
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { toast } from "sonner";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import { TemplateCaptureOverlay } from "../components/TemplateCaptureOverlay";
import { useCaptureFlow } from "../stores/useCaptureFlow";
import type { Screen } from "../types";
import { CAMERA_FILTERS, FORMAT_OPTIONS } from "../constants";
import { attendantPlayer } from "../services/attendantPlayer";
import { GifRecorder } from "../services/gifRecorder";
import { VideoRecorder } from "../services/videoRecorder";
import { useResponsive } from "../hooks/useResponsive";
import { request, type PhotoResponse } from "../../lib/api";
import { getRequiredTemplatePhotoCount, getTemplatePhotoSlots } from "../utils/templateLayout";

const FILTERS = CAMERA_FILTERS;

// 拍摄模式类型
type CaptureMode = "photo" | "gif" | "boomerang" | "video";
type CameraSettingsStatus = "reported" | "writable" | "unavailable";

// 拍摄模式配置
const CAPTURE_MODES: { mode: CaptureMode; label: string; icon: React.ReactNode }[] = [
  { mode: "photo", label: "照片", icon: <Camera size={14} /> },
  { mode: "gif", label: "GIF", icon: <Film size={14} /> },
  { mode: "boomerang", label: "回旋镖", icon: <Zap size={14} /> },
  { mode: "video", label: "视频", icon: <Video size={14} /> },
];

// GIF配置
const GIF_CONFIG = {
  frameCount: 5,      // 默认5帧
  frameDelay: 100,    // 帧间延迟100ms
  quality: 10
};

// 视频配置
const VIDEO_CONFIG = {
  maxDuration: 15,    // 最大录制15秒
  framerate: 30
};

export function CameraScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const { isMobile, isTablet, isDesktop } = useResponsive();
  const [countdown, setCountdown] = useState<number | null>(null);
  const [captured, setCaptured] = useState(false);
  const [showPhotoActions, setShowPhotoActions] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState(0);
  const [selectedPhoto, setSelectedPhoto] = useState<number | null>(null);
  const [aspectRatio, setAspectRatio] = useState("4:3");
  const [captureMode, setCaptureMode] = useState<CaptureMode>("photo");
  const [gifProgress, setGifProgress] = useState(0);
  const [isRecordingVideo, setIsRecordingVideo] = useState(false);
  // rAF 绘制循环读取的录制标记：state 闭包在录制启动前捕获旧值，必须用 ref
  const isRecordingVideoRef = useRef(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [showSettings, setShowSettings] = useState(false);
  // 相机连接状态
  const [cameraStatus, setCameraStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
  const [cameraModel, setCameraModel] = useState<string | null>(null);
  const [cameraControllerType, setCameraControllerType] = useState<string>("webcam");
  // 相机参数 - 从后端获取或使用默认值
  const [cameraParams, setCameraParams] = useState({
    iso: 800,
    shutter_speed: "1/125",
    white_balance: "5200K",
    aperture: "f/4.0",
    exposure_compensation: "+0.0",
    focus_mode: "AF-C",
  });
  const [cameraSettingsStatus, setCameraSettingsStatus] = useState<CameraSettingsStatus>("unavailable");

  const { addPhoto, removePhoto, photos, eventId, currentSessionId, authToken, activePrintTemplate, setTemplateSelectionReturnScreen } = useCaptureFlow();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const videoRecorderRef = useRef<VideoRecorder | null>(null);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const openTemplateSelectionForCamera = useCallback(() => {
    setTemplateSelectionReturnScreen("camera");
    navigate("templates");
  }, [navigate, setTemplateSelectionReturnScreen]);

  const requiredTemplatePhotoCount = useMemo(
    () => getRequiredTemplatePhotoCount(activePrintTemplate?.layout),
    [activePrintTemplate?.layout],
  );
  const templatePhotoRequirement = activePrintTemplate
    ? Math.max(requiredTemplatePhotoCount, 1)
    : 0;
  const templatePhotoSlots = useMemo(
    () => getTemplatePhotoSlots(activePrintTemplate?.layout),
    [activePrintTemplate?.layout],
  );
  const capturedTemplatePhotoCount = activePrintTemplate
    ? Math.min(photos.length, templatePhotoRequirement)
    : photos.length;
  const missingTemplatePhotoCount = activePrintTemplate
    ? Math.max(0, templatePhotoRequirement - photos.length)
    : 0;
  const nextTemplatePhotoNumber = activePrintTemplate && missingTemplatePhotoCount > 0
    ? Math.min(photos.length + 1, templatePhotoRequirement)
    : null;

  const openPrintPreview = useCallback(() => {
    if (!activePrintTemplate) {
      openTemplateSelectionForCamera();
      return;
    }

    if (missingTemplatePhotoCount > 0) {
      toast.info(`当前模板还差 ${missingTemplatePhotoCount} 张照片，请继续拍摄`);
      return;
    }

    navigate("print");
  }, [activePrintTemplate, missingTemplatePhotoCount, navigate, openTemplateSelectionForCamera]);

  const hidePostCaptureActions = useCallback(() => {
    setCaptured(false);
    setShowPhotoActions(false);
    setGifProgress(0);
  }, []);

  const discardLatestPhotoAndRetake = useCallback(() => {
    const latestPhoto = photos[photos.length - 1];
    if (latestPhoto) {
      removePhoto(latestPhoto.id);
      setSelectedPhoto(null);
    }
    hidePostCaptureActions();
  }, [hidePostCaptureActions, photos, removePhoto]);

  useEffect(() => {
    let cancelled = false;

    async function startCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraError("当前浏览器不支持相机");
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "user",
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach(track => track.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setCameraReady(true);
        setCameraError(null);
      } catch {
        setCameraReady(false);
        setCameraError("相机权限未开启");
        toast.error("相机权限未开启，当前仅显示预览占位");
      }
    }

    startCamera();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    };
  }, []);

  // 获取相机状态和参数
  useEffect(() => {
    let cancelled = false;

    async function fetchCameraStatus() {
      try {
        const status = await request<{
          connected: boolean;
          model?: string;
          controller_type: string;
        }>("/camera/status");
        if (cancelled) return;

        if (status.connected) {
          setCameraStatus("connected");
          setCameraModel(status.model ?? null);
          setCameraControllerType(status.controller_type);
        } else {
          setCameraStatus("disconnected");
          setCameraModel(null);
          setCameraControllerType("webcam");
        }
      } catch {
        if (!cancelled) {
          setCameraStatus("disconnected");
          setCameraControllerType("webcam");
        }
      }
    }

    async function fetchCameraSettings() {
      try {
        const settings = await request<{
          settings_available?: boolean;
          settings_writable?: boolean;
          source?: string;
          iso?: number;
          shutter_speed?: string;
          white_balance?: string;
          aperture?: string;
          exposure_compensation?: number;
          focus_mode?: string;
        }>("/camera/settings");
        if (cancelled) return;
        if (settings.settings_available === false) {
          setCameraSettingsStatus(settings.settings_writable ? "writable" : "unavailable");
          return;
        }
        setCameraParams({
          iso: settings.iso ?? 800,
          shutter_speed: settings.shutter_speed ?? "1/125",
          white_balance: settings.white_balance ?? "5200K",
          aperture: settings.aperture ?? "f/4.0",
          exposure_compensation: String(settings.exposure_compensation ?? "+0.0"),
          focus_mode: settings.focus_mode ?? "AF-C",
        });
        setCameraSettingsStatus("reported");
      } catch {
        setCameraSettingsStatus("unavailable");
      }
    }

    setCameraStatus("connecting");
    fetchCameraStatus();
    fetchCameraSettings();

    return () => {
      cancelled = true;
    };
  }, []);

  // 更新相机参数到后端
  const updateCameraSetting = useCallback(async (key: string, value: string) => {
    if (cameraSettingsStatus === "unavailable") {
      toast.error("当前相机不支持后端曝光参数设置");
      return;
    }

    try {
      const body: Record<string, unknown> = {};
      switch (key) {
        case "iso":
          body["iso"] = Number(value);
          break;
        case "shutter_speed":
          body["shutter_speed"] = value;
          break;
        case "white_balance":
          body["white_balance"] = value;
          break;
        case "aperture":
          body["aperture"] = value;
          break;
        case "exposure_compensation":
          body["exposure_compensation"] = Number(value);
          break;
        case "focus_mode":
          body["focus_mode"] = value;
          break;
      }
      await request("/camera/settings", { method: "PUT", body });
      if (cameraSettingsStatus === "reported") {
        setCameraParams(prev => ({ ...prev, [key]: value }));
      } else {
        toast.success("参数已发送到相机，当前读值不可用");
      }
    } catch (error) {
      console.error("Camera setting update failed:", error);
      toast.error("相机参数设置失败，显示值未更改");
    }
  }, [cameraSettingsStatus]);

  // 清理录制定时器
  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
    };
  }, []);

  // DSLR相机拍摄
  const captureDSLR = useCallback(async () => {
    try {
      const result = await request<{
        status: string;
        capture_method: string;
        local_path?: string;
        file_size?: number;
        photo?: PhotoResponse | null;
      }>("/camera/capture", {
        method: "POST",
        token: authToken ?? undefined,
        query: {
          event_id: eventId,
          session_id: currentSessionId,
        },
      });

      if (result.capture_method === "dslr") {
        if (!result.photo) {
          toast.error("请从真实活动进入拍照后再使用 DSLR 拍摄");
          return false;
        }
        await addPhoto({
          url: result.photo.original_url,
          filter: FILTERS[selectedFilter],
          serverPhotoId: result.photo.id,
          uploaded: true,
        });
        toast.success("DSLR拍摄成功");
        return true;
      }
      return false;
    } catch (error) {
      console.warn("DSLR capture failed, falling back to webcam:", error);
      return false;
    }
  }, [addPhoto, authToken, currentSessionId, eventId, selectedFilter]);

  const captureFrame = useCallback(async (): Promise<boolean> => {
    // 优先尝试DSLR拍摄
    if (cameraControllerType === "gphoto2") {
      const dslrSuccess = await captureDSLR();
      if (dslrSuccess) {
        // DSLR拍摄成功,照片已由后端处理
        return true;
      }
    }

    const video = videoRef.current;
    if (!video || !cameraReady || video.videoWidth === 0 || video.videoHeight === 0) {
      toast.error("相机未就绪，请开启权限或检查设备后再拍摄");
      return false;
    }

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      toast.error("无法读取相机画面，请重试");
      return false;
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>(resolve => {
      canvas.toBlob(resolve, "image/jpeg", 0.92);
    });
    if (!blob) {
      toast.error("照片生成失败，请重试");
      return false;
    }

    await addPhoto({ blob, filter: FILTERS[selectedFilter] });
    return true;
  }, [addPhoto, cameraReady, selectedFilter, cameraControllerType, captureDSLR]);

  // GIF拍摄逻辑
  const captureGif = useCallback(async (isBoomerang: boolean = false) => {
    if (!videoRef.current) return;

    setCaptured(true);
    setGifProgress(0);
    toast.info(`开始${isBoomerang ? "回旋镖" : "GIF"}拍摄`);

    try {
      const recorder = new GifRecorder(videoRef.current, {
        frameDelay: GIF_CONFIG.frameDelay,
        quality: GIF_CONFIG.quality
      });

      // 捕获指定数量的帧
      for (let i = 0; i < GIF_CONFIG.frameCount; i++) {
        await recorder.captureFrame();
        setGifProgress(((i + 1) / GIF_CONFIG.frameCount) * 100);
        await new Promise(resolve => setTimeout(resolve, GIF_CONFIG.frameDelay));
      }

      toast.info("正在合成...");
      const gifBlob = isBoomerang
        ? await recorder.generateBoomerang()
        : await recorder.composeGif();

      addPhoto({
        blob: gifBlob,
        filter: FILTERS[selectedFilter],
        mediaType: "gif"
      });

      setCaptured(false);
      toast.success(`${isBoomerang ? "回旋镖" : "GIF"}拍摄完成`);
    } catch (error) {
      toast.error(`${isBoomerang ? "回旋镖" : "GIF"}拍摄失败: ${error instanceof Error ? error.message : "未知错误"}`);
      setCaptured(false);
    }
  }, [addPhoto, selectedFilter]);

  // 视频录制逻辑
  const startVideoRecording = useCallback(() => {
    if (!videoRef.current || isRecordingVideo) return;

    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth || 1280;
    canvas.height = videoRef.current.videoHeight || 720;
    const ctx = canvas.getContext("2d");

    if (!ctx) {
      toast.error("无法创建录制画布");
      return;
    }

    const drawFrame = () => {
      if (videoRef.current && isRecordingVideoRef.current) {
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
        requestAnimationFrame(drawFrame);
      }
    };

    isRecordingVideoRef.current = true;
    drawFrame();

    try {
      const recorder = new VideoRecorder({
        framerate: VIDEO_CONFIG.framerate,
        mimeType: VideoRecorder.getRecommendedMimeType()
      });

      recorder.startRecording(canvas);
      videoRecorderRef.current = recorder;
      setIsRecordingVideo(true);
      setRecordingDuration(0);

      recordingTimerRef.current = setInterval(() => {
        const duration = recorder.getRecordingDuration();
        setRecordingDuration(duration);

        if (duration >= VIDEO_CONFIG.maxDuration) {
          stopVideoRecording();
        }
      }, 100);

      toast.info("开始录制视频");
    } catch (error) {
      isRecordingVideoRef.current = false;
      toast.error(`视频录制失败: ${error instanceof Error ? error.message : "未知错误"}`);
    }
  }, [isRecordingVideo]);

  const stopVideoRecording = useCallback(async () => {
    if (!videoRecorderRef.current || !isRecordingVideo) return;

    try {
      isRecordingVideoRef.current = false;
      setIsRecordingVideo(false);
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }

      toast.info("正在处理视频...");
      const videoBlob = await videoRecorderRef.current.stopRecording();

      addPhoto({
        blob: videoBlob,
        filter: FILTERS[selectedFilter],
        mediaType: "video"
      });

      toast.success("视频录制完成");
    } catch (error) {
      toast.error(`视频处理失败: ${error instanceof Error ? error.message : "未知错误"}`);
      setIsRecordingVideo(false);
    }
  }, [addPhoto, isRecordingVideo, selectedFilter]);

  // 统一拍摄入口
  const shoot = useCallback(() => {
    if (countdown !== null || isRecordingVideo) return;

    setShowPhotoActions(false);
    attendantPlayer.playForTiming("before_countdown");

    setCountdown(3);
    const t = window.setInterval(() => setCountdown(p => {
      if (p === null || p <= 1) {
        window.clearInterval(t);
        setCaptured(true);

        switch (captureMode) {
          case "photo":
            void captureFrame().then(success => {
              if (success) {
                setShowPhotoActions(true);
                window.setTimeout(() => setCaptured(false), 650);
              } else {
                setCaptured(false);
              }
            });
            break;
          case "gif":
            captureGif(false);
            break;
          case "boomerang":
            captureGif(true);
            break;
          case "video":
            startVideoRecording();
            setCaptured(false);
            break;
        }

        return null;
      }
      return p - 1;
    }), 1000);
  }, [captureFrame, captureGif, captureMode, countdown, isRecordingVideo, startVideoRecording]);

  // 切换拍摄模式
  const switchCaptureMode = useCallback((mode: CaptureMode) => {
    if (isRecordingVideo) {
      toast.warning("请先停止视频录制");
      return;
    }
    setCaptureMode(mode);
  }, [isRecordingVideo]);

  const paramHandlers: Record<string, (v: string) => void> = {
    ISO: (v) => updateCameraSetting("iso", v),
    "快门速度": (v) => updateCameraSetting("shutter_speed", v),
    "白平衡": (v) => updateCameraSetting("white_balance", v),
    "曝光": (v) => updateCameraSetting("exposure_compensation", v),
    "对焦": (v) => updateCameraSetting("focus_mode", v),
  };

  // 格式化录制时长
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <main className="flex-1 flex overflow-hidden">
      {/* Left strip - recent photos: 优先展示本次实际拍摄的照片 */}
      {isDesktop && (
        <nav className="w-20 border-r border-white/5 flex flex-col items-center gap-2 py-4 overflow-y-auto" aria-label="最近照片">
          {photos.length > 0 ? (
            photos.map((photo, i) => (
              <button
                key={photo.id}
                type="button"
                onClick={() => setSelectedPhoto(i)}
                aria-label={`选择照片 ${i + 1}`}
                className={`w-14 h-14 rounded-xl overflow-hidden border cursor-pointer hover:border-violet-500/50 transition-colors flex-shrink-0 bg-transparent p-0 ${selectedPhoto === i ? "border-violet-500" : "border-white/10"}`}>
                {photo.mediaType === "video" ? (
                  <video src={photo.url} className="w-full h-full object-cover pointer-events-none" muted />
                ) : (
                  <img src={photo.url}
                    alt={`最近拍摄 ${i + 1}`} className="w-full h-full object-cover pointer-events-none" loading="lazy" />
                )}
              </button>
            ))
          ) : (
            <div className="mt-2 flex w-14 flex-col items-center gap-1 text-center text-[10px] leading-tight text-white/30">
              <Camera size={18} />
              暂无照片
            </div>
          )}
          {photos.length > 0 && !eventId && (
            <div className="text-[9px] text-amber-300/70 text-center px-1 leading-tight">本地未上传</div>
          )}
        </nav>
      )}

      {/* Main camera view */}
      <section className="flex-1 relative flex flex-col">
        {/* Camera preview */}
        <div className="flex-1 relative bg-black overflow-hidden">
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className={`w-full h-full object-cover opacity-80 ${cameraReady ? "block" : "hidden"}`}
          />
          {!cameraReady && (
            <div className="w-full h-full flex flex-col items-center justify-center gap-3 bg-[#0a0f24]">
              <Camera size={40} className="text-white/25" />
              <div className="text-sm text-white/40">相机预览不可用</div>
              <div className="text-xs text-white/30">请检查相机连接与浏览器权限后重试</div>
            </div>
          )}
          {activePrintTemplate && (
            <TemplateCaptureOverlay
              layout={activePrintTemplate.layout}
              capturedPhotoCount={capturedTemplatePhotoCount}
            />
          )}
          {cameraError && (
            <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-sm px-3 py-1 rounded-lg text-xs text-amber-300">
              {cameraError}
            </div>
          )}

          {/* 相机状态指示器 */}
          <div className="absolute top-3 right-3 z-20 flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full animate-pulse ${
                cameraStatus === "connected" ? "bg-emerald-400" :
                cameraStatus === "connecting" ? "bg-amber-400" : "bg-red-400"
              }`}
            />
            <div className="bg-black/60 backdrop-blur-sm px-2 py-0.5 rounded text-[10px] text-white/70 font-mono">
              {cameraStatus === "connected"
                ? (cameraModel ?? "已连接")
                : cameraStatus === "connecting"
                  ? "检测中..."
                  : "Web Camera"}
            </div>
            {cameraControllerType !== "webcam" && (
              <div className="bg-violet-500/20 backdrop-blur-sm px-1.5 py-0.5 rounded text-[10px] text-violet-400">
                DSLR
              </div>
            )}
          </div>

          {/* Capture mode indicator bar - top center */}
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20">
            <div className="bg-black/60 backdrop-blur-sm rounded-lg p-1 flex gap-1">
              {CAPTURE_MODES.map(({ mode, label, icon }) => (
                <button
                  key={mode}
                  onClick={() => switchCaptureMode(mode)}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs transition-all ${
                    captureMode === mode
                      ? "bg-violet-500 text-white"
                      : "text-white/60 hover:bg-white/10 hover:text-white/80"
                  }`}
                >
                  {icon}
                  <span className={isMobile ? "hidden" : ""}>{label}</span>
                </button>
              ))}
            </div>
            {activePrintTemplate && (
              <div className="mx-auto mt-2 max-w-80 rounded-lg bg-emerald-500/20 px-2 py-1.5 text-[10px] text-emerald-200 backdrop-blur-sm">
                <div className="flex items-center justify-center gap-1.5">
                  <LayoutTemplate size={11} />
                  <span className="truncate">
                    {activePrintTemplate.name} · 已拍 {capturedTemplatePhotoCount}/{templatePhotoRequirement}
                  </span>
                </div>
                <div className="mt-1 text-center text-[10px] text-emerald-100/80">
                  {nextTemplatePhotoNumber ? `下一张拍照片 ${nextTemplatePhotoNumber}` : "模板照片已补齐，可进入打印预览"}
                </div>
                {templatePhotoSlots.length > 1 && (
                  <div className="mt-1 flex justify-center gap-1">
                    {templatePhotoSlots.map(slot => {
                      const isFilled = photos.length >= slot;
                      const isNext = !isFilled && photos.length + 1 === slot;
                      return (
                        <span
                          key={slot}
                          className={`grid h-5 w-5 place-items-center rounded-full border text-[10px] font-semibold ${
                            isFilled
                              ? "border-emerald-300 bg-emerald-300 text-black"
                              : isNext
                                ? "border-amber-300 bg-amber-300/20 text-amber-100"
                                : "border-white/20 bg-black/20 text-white/45"
                          }`}
                        >
                          {slot}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* GIF progress overlay */}
          <AnimatePresence>
            {captureMode === "gif" && captured && gifProgress > 0 && (
              <motion.div
                className="absolute top-16 left-1/2 -translate-x-1/2 z-20"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <div className="bg-black/60 backdrop-blur-sm px-4 py-2 rounded-lg text-center">
                  <div className="text-xs text-white/70 mb-1">
                    GIF拍摄中... {Math.round(gifProgress)}%
                  </div>
                  <div className="w-32 h-1.5 bg-white/20 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-violet-500 rounded-full"
                      animate={{ width: `${gifProgress}%` }}
                      transition={{ duration: 0.2 }}
                    />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Boomerang indicator */}
          <AnimatePresence>
            {captureMode === "boomerang" && captured && gifProgress > 0 && gifProgress < 100 && (
              <motion.div
                className="absolute top-16 left-1/2 -translate-x-1/2 z-20"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <div className="bg-black/60 backdrop-blur-sm px-4 py-2 rounded-lg text-center">
                  <div className="text-xs text-white/70 mb-1">
                    回旋镖 正放+倒放 {Math.round(gifProgress)}%
                  </div>
                  <div className="w-32 h-1.5 bg-white/20 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-emerald-500 rounded-full"
                      animate={{ width: `${gifProgress}%` }}
                      transition={{ duration: 0.2 }}
                    />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Video recording indicator */}
          <AnimatePresence>
            {captureMode === "video" && isRecordingVideo && (
              <motion.div
                className="absolute top-3 right-3 z-20 flex items-center gap-2"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
              >
                <div className="bg-red-500/80 backdrop-blur-sm px-3 py-1.5 rounded-lg flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                  <span className="text-xs text-white font-mono">{formatDuration(recordingDuration)}</span>
                </div>
                <button
                  onClick={stopVideoRecording}
                  className="bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg p-1.5 transition-colors"
                  aria-label="停止录制"
                >
                  <Square size={16} className="text-white" fill="white" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Countdown overlay */}
          <AnimatePresence>
            {countdown !== null && (
              <motion.div className="absolute inset-0 flex items-center justify-center bg-black/40"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <motion.div
                  key={countdown}
                  className="text-9xl font-black text-white"
                  style={{ textShadow: "0 0 60px rgba(139,92,246,0.8)" }}
                  initial={{ scale: 1.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.5, opacity: 0 }}
                  transition={{ duration: 0.4 }}
                >
                  {countdown}
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Flash effect */}
          <AnimatePresence>
            {captured && captureMode === "photo" && (
              <motion.div className="absolute inset-0 bg-white"
                initial={{ opacity: 0.8 }} animate={{ opacity: 0 }} transition={{ duration: 0.5 }} />
            )}
          </AnimatePresence>

          {/* Post-capture action buttons (photo mode only) */}
          <AnimatePresence>
            {showPhotoActions && captureMode === "photo" && (
              <motion.div
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className="absolute bottom-20 left-1/2 z-20 flex max-w-[760px] -translate-x-1/2 flex-wrap justify-center gap-3"
                onAnimationStart={() => {
                  attendantPlayer.playForTiming("after_capture");
                }}
              >
                <GlowBtn onClick={() => navigate("beauty")} variant="primary" size="lg">
                  <Sparkles size={16} /> 美颜编辑
                </GlowBtn>
                <GlowBtn onClick={openTemplateSelectionForCamera} variant="ghost" size="lg">
                  <LayoutTemplate size={16} /> {activePrintTemplate ? "更换模板" : "选择模板"}
                </GlowBtn>
                <GlowBtn onClick={openPrintPreview} variant="accent" size="lg">
                  <Printer size={16} /> {missingTemplatePhotoCount > 0 ? `还差 ${missingTemplatePhotoCount} 张` : "打印预览"}
                </GlowBtn>
                <GlowBtn onClick={discardLatestPhotoAndRetake} variant="ghost" size="lg">
                  <RotateCcw size={16} /> 重拍
                </GlowBtn>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Post-capture action buttons (gif/boomerang mode) */}
          <AnimatePresence>
            {captureMode !== "photo" && captureMode !== "video" && captured && gifProgress === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className="absolute bottom-20 left-1/2 z-20 flex max-w-[760px] -translate-x-1/2 flex-wrap justify-center gap-3"
              >
                <GlowBtn onClick={() => navigate("beauty")} variant="primary" size="lg">
                  <Sparkles size={16} /> 美颜编辑
                </GlowBtn>
                <GlowBtn onClick={openTemplateSelectionForCamera} variant="ghost" size="lg">
                  <LayoutTemplate size={16} /> {activePrintTemplate ? "更换模板" : "选择模板"}
                </GlowBtn>
                <GlowBtn onClick={openPrintPreview} variant="accent" size="lg">
                  <Printer size={16} /> {missingTemplatePhotoCount > 0 ? `还差 ${missingTemplatePhotoCount} 张` : "打印预览"}
                </GlowBtn>
                <GlowBtn onClick={() => {
                  setCaptured(false);
                  setGifProgress(0);
                }} variant="ghost" size="lg">
                  <RotateCcw size={16} /> 重新拍摄
                </GlowBtn>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Camera info overlay */}
          <div className="absolute bottom-3 left-0 right-0 flex items-center justify-center gap-6">
            {cameraSettingsStatus !== "reported" ? (
              <div className="bg-black/60 backdrop-blur-sm px-3 py-1 rounded-lg text-xs text-amber-200">
                {cameraSettingsStatus === "writable" ? "参数可设置，当前读值不可用" : "相机参数不可用"}
              </div>
            ) : (
              <>
                <div className="bg-black/60 backdrop-blur-sm px-3 py-1 rounded-lg text-xs text-white/70 font-mono">
                  ISO {cameraParams.iso}
                </div>
                <div className="bg-black/60 backdrop-blur-sm px-3 py-1 rounded-lg text-xs text-white/70 font-mono">
                  {cameraParams.shutter_speed}s
                </div>
                <div className="bg-black/60 backdrop-blur-sm px-3 py-1 rounded-lg text-xs text-white/70 font-mono">
                  {cameraParams.white_balance}
                </div>
              </>
            )}
            <div className="bg-black/60 backdrop-blur-sm px-3 py-1 rounded-lg text-xs text-white/70">
              {cameraReady && videoRef.current?.videoWidth ? `${videoRef.current.videoWidth} × ${videoRef.current.videoHeight}` : "预览占位"}
            </div>
          </div>
        </div>

        {/* Filter strip */}
        <div className="bg-black/80 px-4 py-2 flex items-center gap-3 border-t border-white/5">
          <div className="flex gap-2 flex-1 overflow-x-auto pb-1">
            {FILTERS.map((f, i) => (
              <button key={f} onClick={() => setSelectedFilter(i)}
                className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs transition-all ${i === selectedFilter ? "bg-violet-500 text-white" : "bg-white/10 text-white/60 hover:bg-white/20"}`}>
                {f}
              </button>
            ))}
          </div>
          <div className="text-xs text-white/40 flex-shrink-0">滤镜模式</div>
        </div>

        {/* Bottom controls */}
        <div className="bg-black/90 px-8 py-4 flex items-center justify-between border-t border-white/5">
          <div className="flex items-center gap-4">
            <button
              className="flex flex-col items-center gap-1"
              onClick={openTemplateSelectionForCamera}
            >
              <div className={`relative w-11 h-11 rounded-xl flex items-center justify-center ${activePrintTemplate ? "bg-emerald-500/20 ring-1 ring-emerald-400/40" : "bg-white/10"}`}>
                <Image size={18} className="text-white/70" />
                {activePrintTemplate && <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-emerald-300" />}
              </div>
              <span className={`text-[10px] ${activePrintTemplate ? "text-emerald-300" : "text-white/40"}`}>
                {activePrintTemplate ? "已选模板" : "模板"}
              </span>
            </button>
            <button className="flex flex-col items-center gap-1" onClick={shoot}>
              <div className="w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center">
                <Timer size={18} className="text-white/70" />
              </div>
              <span className="text-[10px] text-white/40">倒计时</span>
            </button>
            <button className="flex flex-col items-center gap-1" onClick={() => navigate("beauty")}>
              <div className="w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center">
                <Sliders size={18} className="text-white/70" />
              </div>
              <span className="text-[10px] text-white/40">美颜</span>
            </button>
          </div>

          {/* Shutter button - adapts to capture mode */}
          {captureMode === "video" ? (
            // 视频模式按钮
            isRecordingVideo ? (
              <motion.button
                onClick={stopVideoRecording}
                className={`relative flex items-center justify-center cursor-pointer ${isMobile ? 'w-25 h-25' : 'w-20 h-20'} rounded-full`}
                style={{ background: "radial-gradient(circle, #ef4444 60%, #b91c1c 100%)", boxShadow: "0 0 30px rgba(239,68,68,0.4)" }}
                whileTap={{ scale: 0.9 }}
                aria-label="停止录制"
              >
                <div className={`rounded-full border-2 border-white/50 flex items-center justify-center ${isMobile ? 'w-22 h-22' : 'w-16 h-16'}`}>
                  <Square size={isMobile ? 28 : 20} className="text-white" fill="white" />
                </div>
              </motion.button>
            ) : (
              <motion.button
                onClick={shoot}
                className={`relative flex items-center justify-center cursor-pointer ${isMobile ? 'w-25 h-25' : 'w-20 h-20'} rounded-full border-2 border-red-500`}
                style={{ background: "radial-gradient(circle, #fff 60%, #e0e0e0 100%)", boxShadow: "0 0 30px rgba(255,255,255,0.4), 0 0 60px rgba(139,92,246,0.3)" }}
                whileTap={{ scale: 0.9 }}
                aria-label="开始录制"
              >
                <div className={`rounded-full border-2 border-gray-300/50 flex items-center justify-center ${isMobile ? 'w-20 h-20' : 'w-12 h-12'}`}>
                  <div className="bg-red-500 rounded-sm" style={{ width: isMobile ? 28 : 20, height: isMobile ? 20 : 14 }} />
                </div>
              </motion.button>
            )
          ) : (
            // 照片/GIF/回旋镖模式按钮
            <motion.button
              onClick={shoot}
              className={`relative flex items-center justify-center cursor-pointer ${isMobile ? 'w-25 h-25' : 'w-20 h-20'} rounded-full`}
              style={{ background: "radial-gradient(circle, #fff 60%, #e0e0e0 100%)", boxShadow: "0 0 30px rgba(255,255,255,0.4), 0 0 60px rgba(139,92,246,0.3)" }}
              whileTap={{ scale: 0.9 }}
              aria-label="拍照"
            >
              <div className={`rounded-full border-2 border-gray-300/50 flex items-center justify-center ${isMobile ? 'w-22 h-22' : 'w-16 h-16'}`}>
                <CircleDot size={isMobile ? 36 : 28} className="text-gray-700" />
              </div>
            </motion.button>
          )}

          <div className="flex items-center gap-4">
            <button className="flex flex-col items-center gap-1" onClick={() => {
              const idx = FORMAT_OPTIONS.indexOf(aspectRatio as typeof FORMAT_OPTIONS[number]);
              setAspectRatio(FORMAT_OPTIONS[(idx + 1) % FORMAT_OPTIONS.length]);
            }}>
              <div className="w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center">
                <Grid3X3 size={18} className="text-white/70" />
              </div>
              <span className="text-[10px] text-white/40">{aspectRatio}</span>
            </button>
            <button className="flex flex-col items-center gap-1" onClick={() => navigate("beauty")}>
              <div className="w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center">
                <Wand2 size={18} className="text-white/70" />
              </div>
              <span className="text-[10px] text-white/40">AI美颜</span>
            </button>
            <button className="flex flex-col items-center gap-1" onClick={openPrintPreview}>
              <div className={`relative w-11 h-11 rounded-xl flex items-center justify-center ${
                activePrintTemplate && missingTemplatePhotoCount === 0 ? "bg-emerald-500/20 ring-1 ring-emerald-400/40" : "bg-white/10"
              }`}>
                <Printer size={18} className="text-white/70" />
                {activePrintTemplate && missingTemplatePhotoCount > 0 && (
                  <span className="absolute -right-1 -top-1 rounded-full bg-amber-400 px-1 text-[9px] font-semibold text-black">
                    -{missingTemplatePhotoCount}
                  </span>
                )}
              </div>
              <span className={`text-[10px] ${activePrintTemplate && missingTemplatePhotoCount === 0 ? "text-emerald-300" : "text-white/40"}`}>
                {!activePrintTemplate ? "选模板" : missingTemplatePhotoCount > 0 ? "补拍" : "打印"}
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* Right panel - camera settings */}
      <GlassCard className="w-52 rounded-none border-l border-white/5 p-4 space-y-4 overflow-y-auto">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-white/60 uppercase tracking-wider">相机参数</span>
            <div className={`mt-1 text-[10px] ${
              cameraSettingsStatus === "reported"
                ? "text-emerald-300"
                : cameraSettingsStatus === "unavailable"
                  ? "text-amber-300"
                  : "text-white/35"
            }`}>
              {cameraSettingsStatus === "reported"
                ? "真实参数"
                : cameraSettingsStatus === "unavailable"
                  ? "参数未读取"
                  : "可设置，读值不可用"}
            </div>
          </div>
          <button
            onClick={() => navigate("camera-wizard")}
            className="p-1 rounded hover:bg-violet-500/20 transition-colors"
            aria-label="相机设置向导"
          >
            <Wrench size={12} className="text-violet-400" />
          </button>
        </div>
        {[
          { label: "ISO", value: cameraParams.iso.toString(), key: "iso", options: ["100", "200", "400", "800", "1600", "3200"] },
          { label: "快门速度", value: cameraParams.shutter_speed, key: "shutter_speed", options: ["1/30", "1/60", "1/125", "1/250", "1/500"] },
          { label: "白平衡", value: cameraParams.white_balance, key: "white_balance", options: ["5200K", "5600K", "6500K"] },
          { label: "曝光", value: cameraParams.exposure_compensation, key: "exposure_compensation", options: ["-2.0", "-1.0", "0.0", "+1.0", "+2.0"] },
          { label: "对焦", value: cameraParams.focus_mode, key: "focus_mode", options: ["AF-S", "AF-C", "AF-F", "MF"] },
        ].map(p => (
          <div key={p.label} className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-white/40">{p.label}</span>
              <span className="text-xs font-mono text-violet-400">
                {cameraSettingsStatus === "reported" ? p.value : "--"}
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {p.options.map(o => (
                <button key={o} onClick={() => paramHandlers[p.label]?.(o)}
                  disabled={cameraSettingsStatus === "unavailable"}
                  className={`px-1.5 py-0.5 rounded text-[10px] transition-colors disabled:cursor-not-allowed disabled:opacity-35 ${cameraSettingsStatus === "reported" && p.value === o ? "bg-violet-500/30 text-violet-400" : "bg-white/5 hover:bg-violet-500/20 text-white/40 hover:text-violet-400"}`}>
                  {o}
                </button>
              ))}
            </div>
          </div>
        ))}

        <div className="pt-2 border-t border-white/5">
          <div className="flex items-center gap-1.5 mb-2">
            <Layers size={12} className="text-white/40" />
            <span className="text-xs font-semibold text-white/60 uppercase tracking-wider">绿幕设置</span>
          </div>
          <button
            onClick={() => navigate("green-screen")}
            className="w-full py-1.5 rounded-lg text-[10px] bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 transition-colors"
          >
            进入绿幕设置
          </button>
        </div>
      </GlassCard>
    </main>
  );
}
