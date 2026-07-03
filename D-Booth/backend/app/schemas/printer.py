from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class PrinterStatus(str, Enum):
    READY = "ready"
    OFFLINE = "offline"
    PAPER_OUT = "paper_out"
    INK_LOW = "ink_low"
    ERROR = "error"


class PrinterInfo(BaseModel):
    name: str
    status: PrinterStatus
    is_default: bool
    location: Optional[str] = None
    driver_name: Optional[str] = None
    port_name: Optional[str] = None


class PrintQueueItem(BaseModel):
    job_id: int
    document: str
    user: str
    status: str
    pages_total: int
    pages_printed: int
    submitted_time: str


class CalibrationParams(BaseModel):
    scale: float = 1.0  # 缩放比例，0.9-1.1
    offset_x: int = 0  # 水平偏移，像素
    offset_y: int = 0  # 垂直偏移，像素
    rotation: int = 0  # 旋转角度，0/90/180/270度
