from typing import List, Optional

from pydantic import BaseModel

from app.schemas.printer import PrinterInfo, PrintQueueItem


class ApiHealth(BaseModel):
    online: bool
    status: str
    error: Optional[str] = None


class CameraHealth(BaseModel):
    connected: bool
    model: Optional[str] = None
    controller_type: Optional[str] = None
    battery_level: Optional[int] = None
    storage_remaining: Optional[int] = None
    error: Optional[str] = None


class PrintQueueSummary(BaseModel):
    total: int = 0
    active: int = 0
    blocked: int = 0


class BoothHealthResponse(BaseModel):
    overall: str
    ready: bool
    issues: List[str]
    api: ApiHealth
    camera: CameraHealth
    printers: List[PrinterInfo]
    selected_printer: Optional[PrinterInfo] = None
    print_queue: List[PrintQueueItem]
    queue: PrintQueueSummary
    timestamp: str
