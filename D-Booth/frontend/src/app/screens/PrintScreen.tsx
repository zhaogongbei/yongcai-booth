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
import { PRINT_HISTORY, MAX_PRINT_QTY } from "../constants";
import type { Screen } from "../types";
import type { PrinterInfo } from "../../lib/api";

function formatTemplatePaperSize(layout: { paperSize: { width: number; height: number } } | null): string {
  if (!layout) return "默认 2x6 英寸";
  const formatInches = (mm: number) => {
    const inches = mm / 25.4;
    return Number.isInteger(inches) ? String(inches) : inches.toFixed(1);
  };
  return `${formatInches(layout.paperSize.width)}x${formatInches(layout.paperSize.height)} 英寸`;
}

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
  const printUnavailableReason = useMemo(() => {
    if (!hasPrintablePhoto) return "请先完成拍照";
    if (!authToken) return "请从真实活动进入拍照后再打印";
    if (!printPhoto?.serverPhotoId) {
      return printPhoto?.uploadError ? "照片上传失败，无法打印" : "照片正在上传，完成后可打印";
    }
    if (!selectedPrinter) return "请先选择打印机";
    return null;
  }, [authToken, hasPrintablePhoto, printPhoto?.serverPhotoId, printPhoto?.uploadError, selectedPrinter]);
  const printButtonLabel = useMemo(() => {
    if (!printUnavailableReason) {
      return isPrintBusy(printStatus) || printStatus === "completed" ? printStateLabel(printStatus) : "打印照片";
    }
    if (!hasPrintablePhoto) return "请先拍照";
    if (!authToken) return "无法打印";
    if (printPhoto?.uploadError) return "上传失败";
    if (!printPhoto?.serverPhotoId) return "等待上传";
    return "请选择打印机";
  }, [authToken, hasPrintablePhoto, printPhoto?.serverPhotoId, printPhoto?.uploadError, printStatus, printUnavailableReason]);

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

  const openTemplateSelectionForPrint = useCallback(() => {
    setTemplateSelectionReturnScreen("print");
    navigate("templates");
  }, [navigate, setTemplateSelectionReturnScreen]);

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

    const photoId = printPhoto?.serverPhotoId;
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
  }, [activePrintTemplate?.id, authToken, hasPrintablePhoto, printPhoto?.serverPhotoId, printUnavailableReason, qty, selectedPrinter, sendPrintEvent, stopPolling]);

  // 使用当前选中照片优先，其余照片按拍摄顺序补齐多照片框。
  const printPreviewImages = useMemo(() => {
    if (printPhoto) {
      return [printPhoto.url, ...photos.filter(photo => photo.id !== printPhoto.id).map(photo => photo.url)];
    }
    if (photos.length > 0) {
      return photos.map(photo => photo.url);
    }
    return [];
  }, [photos, printPhoto]);

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

  const paperSizeLabel = useMemo(
    () => formatTemplatePaperSize(activePrintTemplate?.layout ?? null),
    [activePrintTemplate?.layout],
  );

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
              <div className="bg-white rounded-xl p-4 shadow-[0_0_60px_rgba(139,92,246,0.2)]" style={{ width: 260, height: 620 }}>
                {printPreviewImages.map((src, i) => (
                  <div key={i} className="mb-3 rounded-lg overflow-hidden" style={{ height: printPhoto ? 560 : 175 }}>
                    <img src={src}
                      alt={`print ${i + 1}`} className="w-full h-full object-cover" loading="lazy" />
                  </div>
                ))}
                {!selectedPhoto && (
                  <div className="text-center mt-2">
                    <div className="text-xs font-bold text-pink-500">LOVE FOREVER</div>
                    <div className="text-[10px] text-gray-400">Thank You</div>
                  </div>
                )}
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
            {activePrintTemplate && (
              <div className="mt-3 flex items-center justify-center gap-1.5 text-xs text-emerald-300">
                <LayoutTemplate size={13} />
                {activePrintTemplate.name}
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

        {/* Print history */}
        <div className="border-t border-white/5 px-5 py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-white/60">打印记录</span>
            <span className="text-xs text-white/30">今日: 156 张</span>
          </div>
          <div className="flex gap-3 overflow-x-auto">
            {PRINT_HISTORY.map((p, i) => (
              <GlassCard key={i} className="flex-shrink-0 px-4 py-2.5 flex items-center gap-4">
                <Printer size={18} className="text-violet-400" />
                <div>
                  <div className="text-xs text-white">{p.name}</div>
                  <div className="text-[10px] text-white/40">已打印 {p.count} 张</div>
                </div>
                <div className="flex items-center gap-2 text-[10px]">
                  <div className="flex gap-1">
                    {["C", "M", "Y", "K"].map((c, j) => (
                      <div key={c} className="w-3 h-3 rounded-full" style={{ background: ["#06b6d4", "#ec4899", "#f59e0b", "#1f2937"][j] }} />
                    ))}
                  </div>
                  <span className="text-white/40">墨水 {p.ink}%</span>
                </div>
                <div className={`w-2 h-2 rounded-full ${p.status === "正常" ? "bg-emerald-400" : "bg-yellow-400"}`} />
              </GlassCard>
            ))}
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
            <span className="min-w-0 flex-1 truncate">{activePrintTemplate?.name ?? "未选择，使用默认预览"}</span>
          </div>
          <div className="mt-2 text-[10px] text-white/35">出纸尺寸：{paperSizeLabel}</div>
          <button
            type="button"
            onClick={openTemplateSelectionForPrint}
            className="mt-3 w-full rounded-lg border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-xs font-medium text-violet-200 hover:bg-violet-500/15"
          >
            {activePrintTemplate ? "从模板库重新选择" : "去模板库选择出纸版式"}
          </button>
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
          disabled={isPrintBusy(printStatus) || Boolean(printUnavailableReason)}
          onClick={handlePrint}
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
