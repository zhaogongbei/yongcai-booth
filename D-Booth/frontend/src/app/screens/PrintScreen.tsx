import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import type React from "react";
import { ArrowLeft, Camera, Printer, Check, Share2, RefreshCw, FileText, LayoutTemplate } from "lucide-react";
import { motion } from "motion/react";
import { toast } from "sonner";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import { TemplatePrintPreview, getTemplateCanvasSize } from "../components/TemplatePrintPreview";
import { StatusPill } from "../components/StatusPill";
import { useCaptureFlow } from "../stores/useCaptureFlow";
import { cancelPrintQueueJob, createPrintJob, getPrintJob, printTestPage } from "../lib/api";
import { printerTone, useBoothHealth } from "../hooks/useBoothHealth";
import { getBoothPrinters, getDefaultBoothPrinter, isPreferredPrinter } from "../services/printerPolicy";
import {
  isPrintBusy,
  printStateLabel,
  printStateTone,
  stateFromPrintJob,
  transitionPrintState,
  type PrintRuntimeState,
} from "../services/printStateMachine";
import { MAX_PRINT_QTY } from "../constants";
import type { Screen } from "../types";
import type { PrinterInfo } from "../../lib/api";
import { getRequiredTemplatePhotoCount, getTemplatePhotoSlots } from "../utils/templateLayout";

function printerStatusLabel(status: PrinterInfo["status"]): string {
  const map: Record<string, string> = {
    ready: "就绪",
    offline: "离线",
    paper_out: "缺纸",
    ink_low: "墨水不足",
    error: "错误",
  };
  return map[status] ?? status;
}

function printerStatusColor(status: PrinterInfo["status"]): string {
  const map: Record<string, string> = {
    ready: "text-emerald-400",
    offline: "text-red-400",
    paper_out: "text-yellow-400",
    ink_low: "text-yellow-400",
    error: "text-red-400",
  };
  return map[status] ?? "text-white/40";
}

function printerStatusDot(status: PrinterInfo["status"]): string {
  const map: Record<string, string> = {
    ready: "bg-emerald-400",
    offline: "bg-red-400",
    paper_out: "bg-yellow-400",
    ink_low: "bg-yellow-400",
    error: "bg-red-400",
  };
  return map[status] ?? "bg-white/40";
}

function formatTemplatePaperSize(layout: { paperSize: { width: number; height: number } } | null): string {
  if (!layout) return "默认 2x6 英寸";
  const formatInches = (mm: number) => {
    const inches = mm / 25.4;
    return Number.isInteger(inches) ? String(inches) : inches.toFixed(1);
  };
  return `${formatInches(layout.paperSize.width)}x${formatInches(layout.paperSize.height)} 英寸`;
}

function isBackendTemplateId(templateId: string | undefined): boolean {
  return Boolean(templateId?.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i));
}

export function PrintScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const [selectedPrinter, setSelectedPrinter] = useState("");
  const [printStatus, setPrintStatus] = useState<PrintRuntimeState>("idle");
  const [qty, setQty] = useState(1);
  const boothHealth = useBoothHealth(selectedPrinter);

  // 从 useBoothHealth 轮询数据中过滤出支持的 Booth 打印机（每 8s 自动刷新）
  const boothPrinters = useMemo(
    () => getBoothPrinters(boothHealth.printers),
    [boothHealth.printers],
  );

  // 当轮询检测到新打印机时，自动选择默认打印机
  useEffect(() => {
    if (!selectedPrinter && boothPrinters.length > 0) {
      const defaultPrinter = getDefaultBoothPrinter(boothPrinters);
      setSelectedPrinter(defaultPrinter ? defaultPrinter.name : boothPrinters[0].name);
    }
  }, [boothPrinters, selectedPrinter]);

  const { selectedPhoto, photos, authToken, activePrintTemplate, setTemplateSelectionReturnScreen } = useCaptureFlow();
  const pollTimerRef = useRef<number | null>(null);
  const hasPrintablePhoto = photos.length > 0;
  const printPhoto = selectedPhoto ?? photos[0];
  const orderedPrintPhotos = useMemo(() => {
    if (activePrintTemplate) return photos;
    if (printPhoto) {
      return [printPhoto, ...photos.filter(photo => photo.id !== printPhoto.id)];
    }
    return [];
  }, [activePrintTemplate, photos, printPhoto]);
  const printPreviewImages = useMemo(() => orderedPrintPhotos.map(photo => photo.url), [orderedPrintPhotos]);
  const requiredTemplatePhotoCount = useMemo(
    () => getRequiredTemplatePhotoCount(activePrintTemplate?.layout),
    [activePrintTemplate?.layout],
  );
  const templatePhotoSlots = useMemo(
    () => getTemplatePhotoSlots(activePrintTemplate?.layout),
    [activePrintTemplate?.layout],
  );
  const templatePhotoRequirement = activePrintTemplate ? Math.max(requiredTemplatePhotoCount, 1) : 0;
  const missingTemplatePhotoCount = activePrintTemplate
    ? Math.max(0, templatePhotoRequirement - orderedPrintPhotos.length)
    : 0;
  const hasUnsavedPrintTemplate = Boolean(activePrintTemplate && !isBackendTemplateId(activePrintTemplate.id));
  const printJobPhotos = activePrintTemplate
    ? orderedPrintPhotos.slice(0, templatePhotoRequirement)
    : (printPhoto ? [printPhoto] : []);
  const pendingUploadPhoto = printJobPhotos.find(photo => !photo.serverPhotoId);
  const printUnavailableReason = useMemo(() => {
    if (!hasPrintablePhoto) return "请先完成拍照";
    if (!authToken) return "请从真实活动进入拍照后再打印";
    if (!activePrintTemplate) return "请先选择打印模板";
    if (hasUnsavedPrintTemplate) {
      return "当前模板尚未保存，请重新选择或保存模板后打印";
    }
    if (missingTemplatePhotoCount > 0) {
      return `当前模板需要 ${templatePhotoRequirement} 张照片，还差 ${missingTemplatePhotoCount} 张`;
    }
    if (pendingUploadPhoto) {
      return pendingUploadPhoto.uploadError ? "照片上传失败，无法打印" : "照片正在上传，完成后可打印";
    }
    if (!selectedPrinter) return "请先选择打印机";
    return null;
  }, [activePrintTemplate, authToken, hasPrintablePhoto, hasUnsavedPrintTemplate, missingTemplatePhotoCount, pendingUploadPhoto, selectedPrinter, templatePhotoRequirement]);
  const printButtonLabel = useMemo(() => {
    if (!printUnavailableReason) {
      return isPrintBusy(printStatus) || printStatus === "completed" ? printStateLabel(printStatus) : "打印照片";
    }
    if (!hasPrintablePhoto) return "请先拍照";
    if (!authToken) return "无法打印";
    if (!activePrintTemplate) return "选择模板";
    if (hasUnsavedPrintTemplate) return "重新选择模板";
    if (missingTemplatePhotoCount > 0) return "继续拍照";
    if (pendingUploadPhoto?.uploadError) return "上传失败";
    if (pendingUploadPhoto) return "等待上传";
    return "请选择打印机";
  }, [activePrintTemplate, authToken, hasPrintablePhoto, hasUnsavedPrintTemplate, missingTemplatePhotoCount, pendingUploadPhoto, printStatus, printUnavailableReason]);
  const paperSizeLabel = useMemo(
    () => formatTemplatePaperSize(activePrintTemplate?.layout ?? null),
    [activePrintTemplate?.layout],
  );

  const openTemplateSelectionForPrint = useCallback(() => {
    setTemplateSelectionReturnScreen("print");
    navigate("templates");
  }, [navigate, setTemplateSelectionReturnScreen]);

  // 手动刷新打印机列表
  const handleRefreshPrinters = useCallback(async () => {
    await boothHealth.refresh();
    toast.success("打印机列表已刷新");
  }, [boothHealth]);

  const handlePrintTestPage = useCallback(async (printerName: string) => {
    try {
      const result = await printTestPage(printerName);
      if (result.success) {
        toast.success(`测试页已发送到 ${printerName}`);
      } else {
        toast.error("打印测试页失败");
      }
    } catch (err) {
      console.error("打印测试页失败:", err);
      toast.error("打印测试页失败");
    }
  }, []);

  const handleCancelQueueJob = useCallback(async (jobId: number) => {
    if (!selectedPrinter) return;
    try {
      await cancelPrintQueueJob(selectedPrinter, jobId);
      await boothHealth.refresh();
      toast.success("打印队列任务已取消");
    } catch (err) {
      console.error("取消打印队列任务失败:", err);
      toast.error("取消打印队列任务失败");
    }
  }, [boothHealth, selectedPrinter]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const sendPrintEvent = useCallback((event: Parameters<typeof transitionPrintState>[1]) => {
    setPrintStatus((state) => transitionPrintState(state, event));
  }, []);

  const handlePrint = useCallback(async () => {
    if (!hasPrintablePhoto) {
      toast.error("请先完成拍照，再进入打印");
      return;
    }

    if (printUnavailableReason) {
      toast.error(printUnavailableReason);
      return;
    }

    const photoId = printJobPhotos[0]?.serverPhotoId;
    if (!photoId || !authToken) return;

    sendPrintEvent("SUBMIT");
    try {
      const job = await createPrintJob({
        photoId,
        templateId: activePrintTemplate?.id,
        printerName: selectedPrinter,
        copies: qty,
        token: authToken,
      });
      setPrintStatus(stateFromPrintJob(job));
      // 轮询打印任务状态
      stopPolling();
      pollTimerRef.current = window.setInterval(async () => {
        try {
          const updated = await getPrintJob(job.id, authToken);
          setPrintStatus(stateFromPrintJob(updated));
          if (updated.status === "completed") {
            stopPolling();
            toast.success("打印完成");
            window.setTimeout(() => sendPrintEvent("RESET"), 4000);
          } else if (updated.status === "failed" || updated.status === "cancelled") {
            stopPolling();
            toast.error(updated.error_message || `打印${updated.status === "failed" ? "失败" : "已取消"}`);
          }
        } catch {
          stopPolling();
          sendPrintEvent("FAIL");
          toast.error("打印状态查询失败");
        }
      }, 2000);
      // 安全兜底：30s 未完成则停止轮询
      window.setTimeout(() => {
        stopPolling();
        setPrintStatus((state) => isPrintBusy(state) ? "failed" : state);
      }, 30000);
    } catch (err) {
      sendPrintEvent("FAIL");
      toast.error(err instanceof Error ? err.message : "提交打印任务失败");
    }
  }, [activePrintTemplate?.id, authToken, hasPrintablePhoto, printJobPhotos, printUnavailableReason, qty, selectedPrinter, sendPrintEvent, stopPolling]);

  const handlePrimaryPrintAction = useCallback(() => {
    if (!hasPrintablePhoto) {
      navigate("camera");
      return;
    }
    if (!activePrintTemplate) {
      openTemplateSelectionForPrint();
      return;
    }
    if (hasUnsavedPrintTemplate) {
      openTemplateSelectionForPrint();
      return;
    }
    if (missingTemplatePhotoCount > 0) {
      navigate("camera");
      return;
    }
    void handlePrint();
  }, [activePrintTemplate, handlePrint, hasPrintablePhoto, hasUnsavedPrintTemplate, missingTemplatePhotoCount, navigate, openTemplateSelectionForPrint]);

  const templatePreviewSize = useMemo(() => {
    if (!activePrintTemplate) return null;
    const canvas = getTemplateCanvasSize(activePrintTemplate.layout);
    const maxWidth = canvas.width >= canvas.height ? 520 : 360;
    const maxHeight = 620;
    let width = maxWidth;
    let height = width * canvas.height / canvas.width;
    if (height > maxHeight) {
      height = maxHeight;
      width = height * canvas.width / canvas.height;
    }
    return {
      width,
      height,
      scale: width / canvas.width,
    };
  }, [activePrintTemplate]);

  return (
    <main className="flex-1 flex overflow-hidden">
      {/* Preview area */}
      <section className="flex-1 flex flex-col">
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate("camera")} className="text-xs text-white/40 hover:text-white/70 flex items-center gap-1">
              <ArrowLeft size={14} />返回
            </button>
            <span className="text-sm font-semibold text-white">打印预览</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/40">出纸尺寸：</span>
            <span className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-white/70">{paperSizeLabel}</span>
          </div>
        </div>

        <div className="flex-1 flex items-center justify-center p-8">
          <div className="relative">
            {activePrintTemplate && templatePreviewSize ? (
              <div
                className="overflow-hidden rounded-xl bg-white shadow-[0_0_60px_rgba(139,92,246,0.2)]"
                style={{
                  width: templatePreviewSize.width,
                  height: templatePreviewSize.height,
                  "--template-preview-scale": templatePreviewSize.scale,
                } as React.CSSProperties}
              >
                <TemplatePrintPreview
                  layout={activePrintTemplate.layout}
                  photoUrls={printPreviewImages}
                />
              </div>
            ) : hasPrintablePhoto ? (
              <div className="flex flex-col items-center gap-4">
                <div className="max-w-[360px] rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4 text-center">
                  <div className="flex items-center justify-center gap-2 text-sm font-semibold text-amber-100">
                    <LayoutTemplate size={16} />
                    未选择打印模板
                  </div>
                  <div className="mt-2 text-xs leading-5 text-amber-100/70">
                    先选择模板可直接看到最终出纸效果，避免现场打印后才发现版式不合适。
                  </div>
                  <GlowBtn className="mt-4 w-full justify-center" size="sm" variant="primary" onClick={openTemplateSelectionForPrint}>
                    <LayoutTemplate size={14} />选择模板生成预览
                  </GlowBtn>
                </div>
                <div className="bg-white rounded-xl p-4 shadow-[0_0_60px_rgba(139,92,246,0.2)]" style={{ width: 260, height: 620 }}>
                  {printPreviewImages.map((src, i) => (
                    <div key={i} className="mb-3 rounded-lg overflow-hidden" style={{ height: printPhoto ? 560 : 175 }}>
                      <img src={src}
                        alt={`print ${i + 1}`} className="w-full h-full object-cover" loading="lazy" />
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <GlassCard className="w-[320px] p-6 text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10 text-white/50">
                  <Camera size={24} />
                </div>
                <div className="mt-4 text-sm font-semibold text-white">还没有可打印照片</div>
                <div className="mt-2 text-xs leading-5 text-white/45">请先完成拍照，再选择模板和提交打印。</div>
                <GlowBtn className="mt-5 w-full justify-center" size="sm" variant="primary" onClick={() => navigate("camera")}>
                  <Camera size={14} />返回拍照
                </GlowBtn>
              </GlassCard>
            )}
            {hasPrintablePhoto && (
              <div className={`mx-auto mt-4 flex max-w-[520px] items-center justify-between gap-3 rounded-xl border px-3 py-2 text-xs ${
                activePrintTemplate
                  ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-200"
                  : "border-white/10 bg-white/5 text-white/55"
              }`}>
                <div className="flex min-w-0 items-center gap-1.5">
                  <LayoutTemplate size={13} className="flex-shrink-0" />
                  <div className="min-w-0">
                    <div className="truncate">
                      {activePrintTemplate
                        ? `${activePrintTemplate.name} · 照片 ${Math.min(orderedPrintPhotos.length, templatePhotoRequirement)}/${templatePhotoRequirement}`
                        : "当前未选择打印模板"}
                    </div>
                    {activePrintTemplate && templatePhotoSlots.length > 1 && (
                      <div className="mt-1 flex gap-1">
                        {templatePhotoSlots.map(slot => {
                          const isFilled = orderedPrintPhotos.length >= slot;
                          return (
                            <span
                              key={slot}
                              className={`grid h-4 w-4 place-items-center rounded-full text-[9px] font-semibold ${
                                isFilled ? "bg-emerald-300 text-black" : "bg-amber-300/20 text-amber-100"
                              }`}
                            >
                              {slot}
                            </span>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex flex-shrink-0 items-center gap-2">
                  {activePrintTemplate && missingTemplatePhotoCount > 0 && (
                    <button
                      type="button"
                      className="text-amber-100 hover:text-white"
                      onClick={() => navigate("camera")}
                    >
                      继续拍照
                    </button>
                  )}
                  <button
                    type="button"
                    className={activePrintTemplate ? "text-emerald-100 hover:text-white" : "text-violet-300 hover:text-violet-200"}
                    onClick={openTemplateSelectionForPrint}
                  >
                    {activePrintTemplate ? "更换模板" : "选择模板"}
                  </button>
                </div>
              </div>
            )}
            <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 text-xs text-white/30">100%</div>
          </div>
        </div>

        {/* Print completed - share button */}
        {printStatus === "completed" && (
          <div className="px-5 pb-3 flex justify-center">
            <GlowBtn onClick={() => navigate("sharing")} variant="accent" size="lg">
              <Share2 size={16} /> 分享照片
            </GlowBtn>
          </div>
        )}

        <div className="border-t border-white/5 px-5 py-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/60">系统打印队列</span>
            <span className="text-xs text-white/30">{selectedPrinter || "未选择打印机"}</span>
          </div>
          <div className="mt-2 flex gap-3 overflow-x-auto">
            {boothHealth.printQueue.length === 0 ? (
              <div className="rounded-xl border border-white/5 px-4 py-3 text-xs text-white/30">
                当前没有系统队列任务
              </div>
            ) : (
              boothHealth.printQueue.slice(0, 5).map((job) => (
                <GlassCard key={job.job_id} className="flex-shrink-0 px-4 py-2.5 flex items-center gap-3">
                  <Printer size={18} className="text-violet-400" />
                  <div className="min-w-0">
                    <div className="max-w-40 truncate text-xs text-white">{job.document || `任务 ${job.job_id}`}</div>
                    <div className="text-[10px] text-white/40">
                      {job.status} · {job.pages_printed}/{job.pages_total || 1} 页
                    </div>
                  </div>
                </GlassCard>
              ))
            )}
          </div>
        </div>
      </section>

      {/* Right settings panel */}
      <GlassCard className="w-72 rounded-none border-l border-white/5 p-5 space-y-4 overflow-y-auto">
        <div className="text-sm font-semibold text-white/80">打印设置</div>
        <GlassCard className="p-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <span className="text-xs text-white/40">当前模板</span>
            <button
              className="text-xs text-violet-400 hover:text-violet-300"
              onClick={openTemplateSelectionForPrint}
            >
              {activePrintTemplate ? "更换" : "选择"}
            </button>
          </div>
          <div className="flex items-center gap-2 text-xs text-white/80">
            <LayoutTemplate size={14} className={activePrintTemplate ? "text-emerald-300" : "text-white/30"} />
            <span className="min-w-0 flex-1 truncate">{activePrintTemplate?.name ?? "未选择模板"}</span>
          </div>
          <div className="mt-2 text-[10px] text-white/35">
            出纸尺寸：{paperSizeLabel}
            {activePrintTemplate && ` · 照片 ${Math.min(orderedPrintPhotos.length, templatePhotoRequirement)}/${templatePhotoRequirement}`}
          </div>
          {activePrintTemplate && templatePhotoSlots.length > 1 && (
            <div className="mt-3 flex items-center gap-1.5">
              {templatePhotoSlots.map(slot => {
                const isFilled = orderedPrintPhotos.length >= slot;
                const isNext = !isFilled && orderedPrintPhotos.length + 1 === slot;
                return (
                  <span
                    key={slot}
                    className={`grid h-6 w-6 place-items-center rounded-full border text-[10px] font-semibold ${
                      isFilled
                        ? "border-emerald-300 bg-emerald-300 text-black"
                        : isNext
                          ? "border-amber-300 bg-amber-300/15 text-amber-100"
                          : "border-white/10 bg-white/[0.03] text-white/35"
                    }`}
                  >
                    {slot}
                  </span>
                );
              })}
            </div>
          )}
        </GlassCard>
        <GlassCard className="p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs text-white/40">现场打印状态</span>
            <div className="flex items-center gap-1.5">
              <StatusPill label={printStateLabel(printStatus)} tone={printStateTone(printStatus)} />
              <StatusPill
                label={selectedPrinter ? printerStatusLabel(boothHealth.selectedPrinter?.status ?? "offline") : "未选择"}
                tone={printerTone(boothHealth.selectedPrinter)}
              />
            </div>
          </div>
          {printUnavailableReason && (
            <div className="mb-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-2 py-1.5 text-[10px] text-amber-200">
              {printUnavailableReason}
            </div>
          )}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg bg-white/[0.03] p-2">
              <div className="text-white/35">队列任务</div>
              <div className="mt-1 text-lg font-semibold text-white">{boothHealth.printQueue.length}</div>
            </div>
            <div className="rounded-lg bg-white/[0.03] p-2">
              <div className="text-white/35">后端服务</div>
              <div className={`mt-1 text-sm font-semibold ${boothHealth.api.online ? "text-emerald-300" : "text-red-300"}`}>
                {boothHealth.api.online ? boothHealth.api.status : "离线"}
              </div>
            </div>
          </div>
        </GlassCard>

        {/* Printer selection */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/40">选择打印机</span>
            <button
              onClick={handleRefreshPrinters}
              disabled={boothHealth.loading}
              className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1 disabled:opacity-50"
            >
              <RefreshCw size={12} className={boothHealth.loading ? "animate-spin" : ""} /> 刷新
            </button>
          </div>

          {boothHealth.loading && (
            <div className="text-xs text-white/30 py-4 text-center">正在扫描打印机...</div>
          )}

          {!boothHealth.loading && boothPrinters.length === 0 && (
            <div className="text-xs text-white/30 py-4 text-center border border-white/5 rounded-xl">
              未检测到打印机
            </div>
          )}

          <div className="max-h-48 overflow-y-auto space-y-1">
            {boothPrinters.map(p => (
              <button key={p.name} onClick={() => setSelectedPrinter(p.name)}
                className={`w-full flex items-center gap-3 p-2.5 rounded-lg border transition-all ${selectedPrinter === p.name ? "border-violet-500/50 bg-violet-500/10" : "border-white/5 bg-white/3 hover:bg-white/5"}`}>
                <Printer size={15} className={selectedPrinter === p.name ? "text-violet-400" : "text-white/40"} />
                <div className="flex-1 text-left min-w-0">
                  <div className="text-xs font-medium text-white truncate">{p.name}</div>
                  <div className={`text-[10px] ${printerStatusColor(p.status)}`}>
                    <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1 ${printerStatusDot(p.status)}`} />
                    {printerStatusLabel(p.status)}
                    {isPreferredPrinter(p) && <span className="text-emerald-300 ml-1">(Booth)</span>}
                    {p.is_default && <span className="text-white/20 ml-1">(默认)</span>}
                  </div>
                </div>
                {selectedPrinter === p.name && <Check size={13} className="text-violet-400 flex-shrink-0" />}
                {/* Test page button */}
                <button
                  onClick={(e) => { e.stopPropagation(); handlePrintTestPage(p.name); }}
                  className="p-1 rounded text-white/20 hover:text-violet-400 hover:bg-violet-500/10 flex-shrink-0"
                  title="打印测试页"
                >
                  <FileText size={13} />
                </button>
              </button>
            ))}
          </div>
        </div>

        {/* Quantity */}
        <div className="space-y-2">
          <div className="text-xs text-white/40">打印数量</div>
          <div className="flex items-center gap-3">
            <button onClick={() => setQty(Math.max(1, qty - 1))} className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/60 text-lg">-</button>
            <input type="number" min={1} max={MAX_PRINT_QTY} value={qty}
              onChange={e => setQty(Math.max(1, Math.min(MAX_PRINT_QTY, Number(e.target.value) || 1)))}
              className="flex-1 text-center text-xl font-bold text-white bg-transparent outline-none" />
            <button onClick={() => setQty(Math.min(MAX_PRINT_QTY, qty + 1))} className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/60 text-lg">+</button>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-xs text-white/40">系统打印队列</div>
            <button
              onClick={() => void boothHealth.refreshQueue()}
              className="text-xs text-violet-400 hover:text-violet-300"
            >
              刷新
            </button>
          </div>
          <div className="max-h-40 space-y-2 overflow-y-auto">
            {boothHealth.printQueue.length === 0 ? (
              <div className="rounded-xl border border-white/5 py-4 text-center text-xs text-white/30">
                当前队列为空
              </div>
            ) : (
              boothHealth.printQueue.map((job) => (
                <div key={job.job_id} className="rounded-xl border border-white/5 bg-white/[0.03] p-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-xs font-medium text-white">{job.document || `任务 ${job.job_id}`}</div>
                      <div className="mt-1 text-[10px] text-white/35">
                        {job.status} · {job.pages_printed}/{job.pages_total || 1} 页
                      </div>
                    </div>
                    <button
                      onClick={() => void handleCancelQueueJob(job.job_id)}
                      className="rounded-lg border border-red-500/20 px-2 py-1 text-[10px] text-red-300 hover:bg-red-500/10"
                    >
                      取消
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <motion.button
          className="w-full py-4 rounded-2xl font-semibold text-white text-base disabled:opacity-50"
          style={{ background: "linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%)", boxShadow: "0 0 30px rgba(139,92,246,0.4)" }}
          whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
          disabled={isPrintBusy(printStatus)}
          onClick={handlePrimaryPrintAction}
        >
          <div className="flex items-center justify-center gap-2">
            <Printer size={20} />
            {printButtonLabel}
          </div>
        </motion.button>
      </GlassCard>
    </main>
  );
}
