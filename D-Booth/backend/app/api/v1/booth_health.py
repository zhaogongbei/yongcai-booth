from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter

from app.schemas.booth_health import (
    ApiHealth,
    BoothHealthResponse,
    CameraHealth,
    PrintQueueSummary,
)
from app.schemas.printer import PrinterInfo, PrinterStatus, PrintQueueItem
from app.services.camera_service import camera_manager
from app.services.printer_driver_service import PrinterDriverService

router = APIRouter()


@router.get("/health", response_model=BoothHealthResponse)
async def get_booth_health():
    """Aggregate local booth runtime health into one frontend-friendly payload."""
    api = ApiHealth(online=True, status="healthy")
    camera = await _get_camera_health()
    printers = await _discover_printers()
    selected_printer = _select_printer(printers)
    print_queue = await _get_print_queue(selected_printer)
    queue = _summarize_queue(print_queue)
    issues = _collect_issues(api, camera, printers, selected_printer, queue)
    overall = _overall_tone(api, camera, printers, selected_printer, queue)

    return BoothHealthResponse(
        overall=overall,
        ready=_is_ready(api, camera, printers, selected_printer, queue),
        issues=issues,
        api=api,
        camera=camera,
        printers=printers,
        selected_printer=selected_printer,
        print_queue=print_queue,
        queue=queue,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


async def _get_camera_health() -> CameraHealth:
    try:
        status = camera_manager.get_controller().get_status()
        return CameraHealth(
            connected=bool(status.get("connected", False)),
            model=status.get("model"),
            controller_type=status.get("controller_type"),
            battery_level=status.get("battery_level"),
            storage_remaining=status.get("storage_remaining"),
        )
    except Exception as exc:
        return CameraHealth(connected=False, error=str(exc))


async def _discover_printers() -> List[PrinterInfo]:
    try:
        return await PrinterDriverService.discover_printers()
    except Exception:
        return []


def _select_printer(printers: List[PrinterInfo]) -> Optional[PrinterInfo]:
    if not printers:
        return None
    return next((printer for printer in printers if printer.is_default), printers[0])


async def _get_print_queue(printer: Optional[PrinterInfo]) -> List[PrintQueueItem]:
    if not printer:
        return []
    try:
        return await PrinterDriverService.get_print_queue(printer.name)
    except Exception:
        return []


def _summarize_queue(print_queue: List[PrintQueueItem]) -> PrintQueueSummary:
    active = 0
    blocked = 0
    for job in print_queue:
        status = job.status.lower()
        if any(token in status for token in ("print", "queue", "spool")):
            active += 1
        if any(token in status for token in ("error", "offline", "paused", "paper")):
            blocked += 1
    return PrintQueueSummary(total=len(print_queue), active=active, blocked=blocked)


def _collect_issues(
    api: ApiHealth,
    camera: CameraHealth,
    printers: List[PrinterInfo],
    selected_printer: Optional[PrinterInfo],
    queue: PrintQueueSummary,
) -> List[str]:
    issues: List[str] = []
    if not api.online:
        issues.append(api.error or "后端服务离线")
    if not camera.connected:
        issues.append(f"相机不可用：{camera.error}" if camera.error else "相机未连接")
    if not printers:
        issues.append("未检测到打印机")
    if selected_printer and selected_printer.status not in (PrinterStatus.READY, PrinterStatus.INK_LOW):
        issues.append(f"默认打印机状态：{selected_printer.status.value}")
    if queue.blocked > 0:
        issues.append(f"打印队列存在 {queue.blocked} 个阻塞任务")
    return issues


def _overall_tone(
    api: ApiHealth,
    camera: CameraHealth,
    printers: List[PrinterInfo],
    selected_printer: Optional[PrinterInfo],
    queue: PrintQueueSummary,
) -> str:
    if not api.online or not printers or queue.blocked > 0:
        return "error"
    if not camera.connected:
        return "warn"
    if selected_printer and selected_printer.status == PrinterStatus.READY and queue.total == 0:
        return "ok"
    return "warn"


def _is_ready(
    api: ApiHealth,
    camera: CameraHealth,
    printers: List[PrinterInfo],
    selected_printer: Optional[PrinterInfo],
    queue: PrintQueueSummary,
) -> bool:
    if not api.online or not camera.connected or not printers or queue.blocked > 0:
        return False
    return bool(selected_printer and selected_printer.status in (PrinterStatus.READY, PrinterStatus.INK_LOW))
