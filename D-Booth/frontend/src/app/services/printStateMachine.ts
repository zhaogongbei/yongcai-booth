import type { PrintJobResponse } from "../../lib/api";
import type { HealthTone } from "../hooks/useBoothHealth";

export type PrintRuntimeState =
  | "idle"
  | "submitting"
  | "queued"
  | "printing"
  | "completed"
  | "failed"
  | "cancelled";

export type PrintRuntimeEvent =
  | "SUBMIT"
  | "QUEUE"
  | "START"
  | "COMPLETE"
  | "FAIL"
  | "CANCEL"
  | "RESET";

const transitions: Record<PrintRuntimeState, Partial<Record<PrintRuntimeEvent, PrintRuntimeState>>> = {
  idle: { SUBMIT: "submitting", RESET: "idle" },
  submitting: { QUEUE: "queued", START: "printing", COMPLETE: "completed", FAIL: "failed", CANCEL: "cancelled", RESET: "idle" },
  queued: { START: "printing", COMPLETE: "completed", FAIL: "failed", CANCEL: "cancelled", RESET: "idle" },
  printing: { COMPLETE: "completed", FAIL: "failed", CANCEL: "cancelled", RESET: "idle" },
  completed: { RESET: "idle" },
  failed: { SUBMIT: "submitting", RESET: "idle" },
  cancelled: { SUBMIT: "submitting", RESET: "idle" },
};

export function transitionPrintState(current: PrintRuntimeState, event: PrintRuntimeEvent): PrintRuntimeState {
  return transitions[current][event] ?? current;
}

export function stateFromPrintJob(job: PrintJobResponse): PrintRuntimeState {
  const map: Record<PrintJobResponse["status"], PrintRuntimeState> = {
    pending: "queued",
    queued: "queued",
    printing: "printing",
    completed: "completed",
    failed: "failed",
    cancelled: "cancelled",
  };
  return map[job.status];
}

export function printStateLabel(state: PrintRuntimeState): string {
  const map: Record<PrintRuntimeState, string> = {
    idle: "待命",
    submitting: "提交中",
    queued: "排队中",
    printing: "打印中",
    completed: "打印完成",
    failed: "打印失败",
    cancelled: "已取消",
  };
  return map[state];
}

export function printStateTone(state: PrintRuntimeState): HealthTone {
  if (state === "completed") return "ok";
  if (state === "queued" || state === "printing" || state === "submitting") return "warn";
  if (state === "failed" || state === "cancelled") return "error";
  return "idle";
}

export function isPrintBusy(state: PrintRuntimeState): boolean {
  return state === "submitting" || state === "queued" || state === "printing";
}
