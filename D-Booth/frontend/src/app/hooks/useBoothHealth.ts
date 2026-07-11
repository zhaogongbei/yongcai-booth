import { useCallback, useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import {
  getBackendHealth,
  getBoothHealth,
  getPrintQueue,
  getPrinters,
  request,
  type BoothHealthResponse,
  type PrintQueueItem,
  type PrinterInfo,
} from "../../lib/api";
import { getBoothPrinters, getDefaultBoothPrinter } from "../services/printerPolicy";
import { useSettings } from "../stores/useSettings";

export type HealthTone = "ok" | "warn" | "error" | "idle";

export interface CameraHealth {
  connected: boolean;
  model?: string | null;
  controllerType?: string | null;
  error?: string;
}

export interface BoothHealth {
  overall: HealthTone;
  ready: boolean;
  issues: string[];
  api: {
    online: boolean;
    status: "healthy" | "degraded" | "offline" | "unknown";
    error?: string;
  };
  camera: CameraHealth;
  printers: PrinterInfo[];
  selectedPrinter?: PrinterInfo;
  printQueue: PrintQueueItem[];
  queue: {
    total: number;
    active: number;
    blocked: number;
  };
  loading: boolean;
  lastUpdated: number | null;
  refresh: () => Promise<void>;
  refreshQueue: () => Promise<void>;
}

interface CameraStatusResponse {
  connected: boolean;
  model?: string | null;
  controller_type?: string | null;
}

interface ApiHealthResponse {
  status?: "healthy" | "degraded" | string;
}

export function useBoothHealth(selectedPrinterName?: string): BoothHealth {
  const { settings } = useSettings();
  const preferredPrinterName = settings.print.preferredPrinterName.trim() || undefined;
  const [api, setApi] = useState<BoothHealth["api"]>({ online: false, status: "unknown" });
  const [camera, setCamera] = useState<CameraHealth>({ connected: false });
  const [printers, setPrinters] = useState<PrinterInfo[]>([]);
  const [printQueue, setPrintQueue] = useState<PrintQueueItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  const selectedPrinter = useMemo(() => {
    if (!printers.length) return undefined;
    const boothPrinters = getBoothPrinters(printers, preferredPrinterName);
    if (!boothPrinters.length) return undefined;
    return boothPrinters.find((printer) => printer.name === selectedPrinterName)
      ?? getDefaultBoothPrinter(boothPrinters, preferredPrinterName);
  }, [printers, selectedPrinterName, preferredPrinterName]);

  const refreshQueue = useCallback(async () => {
    if (!selectedPrinter?.name) {
      setPrintQueue([]);
      return;
    }
    try {
      const queue = await getPrintQueue(selectedPrinter.name);
      setPrintQueue(queue);
    } catch {
      setPrintQueue([]);
    }
  }, [selectedPrinter?.name]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      try {
        const boothHealth = await getBoothHealth();
        applyBoothHealthResponse(boothHealth, setApi, setCamera, setPrinters, setPrintQueue);
        setLastUpdated(Date.parse(boothHealth.timestamp) || Date.now());
        return;
      } catch {
        // Keep compatibility with older backend builds that do not expose /booth/health yet.
      }

      const [apiResult, cameraResult, printersResult] = await Promise.allSettled([
        getBackendHealth(),
        request<CameraStatusResponse>("/camera/status"),
        getPrinters(),
      ]);

      if (apiResult.status === "fulfilled") {
        const status = apiResult.value.status === "degraded" ? "degraded" : "healthy";
        setApi({ online: true, status });
      } else {
        setApi({ online: false, status: "offline", error: readableError(apiResult.reason) });
      }

      if (cameraResult.status === "fulfilled") {
        setCamera({
          connected: cameraResult.value.connected,
          model: cameraResult.value.model,
          controllerType: cameraResult.value.controller_type,
        });
      } else {
        setCamera({ connected: false, error: readableError(cameraResult.reason) });
      }

      if (printersResult.status === "fulfilled") {
        setPrinters(printersResult.value);
      } else {
        setPrinters([]);
      }

      setLastUpdated(Date.now());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 8000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    let cancelled = false;
    async function loadQueue() {
      if (!selectedPrinter?.name) {
        setPrintQueue([]);
        return;
      }
      try {
        const queue = await getPrintQueue(selectedPrinter.name);
        if (!cancelled) setPrintQueue(queue);
      } catch {
        if (!cancelled) setPrintQueue([]);
      }
    }
    void loadQueue();
    const timer = window.setInterval(() => void loadQueue(), 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [selectedPrinter?.name]);

  const queue = useMemo(() => {
    const active = printQueue.filter((job) => {
      const status = job.status.toLowerCase();
      return status.includes("print") || status.includes("queue") || status.includes("spool");
    }).length;
    const blocked = printQueue.filter((job) => {
      const status = job.status.toLowerCase();
      return status.includes("error") || status.includes("offline") || status.includes("paused");
    }).length;
    return { total: printQueue.length, active, blocked };
  }, [printQueue]);

  const issues = useMemo(() => {
    const next: string[] = [];
    if (!api.online) next.push(api.error ? `后端离线：${api.error}` : "后端服务离线");
    if (api.online && api.status === "degraded") next.push("后端服务处于降级状态");
    if (!camera.connected) next.push(camera.error ? `相机不可用：${camera.error}` : "相机未连接");
    if (!printers.length) next.push("未检测到打印机");
    if (selectedPrinter && selectedPrinter.status !== "ready" && selectedPrinter.status !== "ink_low") {
      next.push(`默认打印机状态：${printerStatusLabel(selectedPrinter.status)}`);
    }
    if (queue.blocked > 0) next.push(`打印队列存在 ${queue.blocked} 个阻塞任务`);
    return next;
  }, [api, camera, printers.length, queue.blocked, selectedPrinter]);

  const overall = useMemo<HealthTone>(() => {
    if (!api.online || !printers.length) return "error";
    if (queue.blocked > 0) return "error";
    if (!camera.connected || api.status === "degraded" || selectedPrinter?.status === "ink_low" || queue.total > 0) return "warn";
    if (selectedPrinter?.status === "ready") return "ok";
    return "warn";
  }, [api.online, api.status, camera.connected, printers.length, queue.blocked, queue.total, selectedPrinter?.status]);

  return {
    overall,
    ready: overall === "ok" || overall === "warn",
    issues,
    api,
    camera,
    printers,
    selectedPrinter,
    printQueue,
    queue,
    loading,
    lastUpdated,
    refresh,
    refreshQueue,
  };
}

export function apiTone(api: BoothHealth["api"]): HealthTone {
  if (!api.online) return "error";
  return api.status === "degraded" ? "warn" : "ok";
}

export function cameraTone(camera: CameraHealth): HealthTone {
  if (camera.error) return "warn";
  return camera.connected ? "ok" : "warn";
}

export function printerTone(printer?: PrinterInfo): HealthTone {
  if (!printer) return "warn";
  if (printer.status === "ready") return "ok";
  if (printer.status === "paper_out" || printer.status === "ink_low") return "warn";
  return "error";
}

function readableError(error: unknown): string {
  return error instanceof Error ? error.message : "状态不可用";
}

function printerStatusLabel(status: PrinterInfo["status"]): string {
  const map: Record<PrinterInfo["status"], string> = {
    ready: "就绪",
    offline: "离线",
    paper_out: "缺纸",
    ink_low: "墨水不足",
    error: "错误",
  };
  return map[status];
}

function applyBoothHealthResponse(
  response: BoothHealthResponse,
  setApi: Dispatch<SetStateAction<BoothHealth["api"]>>,
  setCamera: Dispatch<SetStateAction<CameraHealth>>,
  setPrinters: Dispatch<SetStateAction<PrinterInfo[]>>,
  setPrintQueue: Dispatch<SetStateAction<PrintQueueItem[]>>,
) {
  setApi({
    online: response.api.online,
    status: apiStatus(response.api.status),
    error: response.api.error ?? undefined,
  });
  setCamera({
    connected: response.camera.connected,
    model: response.camera.model,
    controllerType: response.camera.controller_type,
    error: response.camera.error ?? undefined,
  });
  setPrinters(response.printers);
  setPrintQueue(response.print_queue);
}

function apiStatus(status: string): BoothHealth["api"]["status"] {
  if (status === "healthy" || status === "degraded" || status === "offline" || status === "unknown") {
    return status;
  }
  return "unknown";
}
