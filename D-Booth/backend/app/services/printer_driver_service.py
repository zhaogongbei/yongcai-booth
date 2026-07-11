import asyncio
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from typing import List, Optional

from app.schemas.printer import CalibrationParams, PrinterInfo, PrinterStatus, PrintQueueItem

logger = logging.getLogger(__name__)


def _printer_name_from_enum_entry(entry) -> Optional[str]:
    """Return printer name from pywin32 EnumPrinters dict/tuple variants."""
    if isinstance(entry, dict):
        return entry.get("pPrinterName")
    if isinstance(entry, (tuple, list)) and len(entry) >= 3:
        return entry[2]
    return None


# 平台兼容性：Windows特有导入
try:
    import win32api
    import win32print

    WINDOWS_AVAILABLE = True
except ImportError:
    win32print = None
    win32api = None
    WINDOWS_AVAILABLE = False
    logger.warning(
        "Windows printer APIs (win32print/win32api) not available, printer service will be limited"
    )


class PrinterDriverService:
    @staticmethod
    def _get_printer_status_from_code(
        status_code: int, work_offline: bool = False
    ) -> PrinterStatus:
        """转换Windows打印机状态码为统一枚举"""
        if work_offline or status_code & 0x00000080:  # PRINTER_STATUS_OFFLINE
            return PrinterStatus.OFFLINE
        if status_code == 0:
            return PrinterStatus.READY
        if status_code & (0x00000010 | 0x00000040):  # PAPER_OUT / PAPER_PROBLEM
            return PrinterStatus.PAPER_OUT
        if status_code & (0x00020000 | 0x00040000):  # TONER_LOW / NO_TONER
            return PrinterStatus.INK_LOW
        if status_code & (
            0x00000002 | 0x00000008 | 0x00100000 | 0x00400000
        ):  # ERROR / PAPER_JAM / USER_INTERVENTION / DOOR_OPEN
            return PrinterStatus.ERROR
        return PrinterStatus.READY

    @staticmethod
    async def discover_printers() -> List[PrinterInfo]:
        """发现系统所有打印机"""
        printers = []
        if not WINDOWS_AVAILABLE:
            logger.warning("Printer discovery not available on non-Windows platform")
            return printers
        try:
            # 使用win32print枚举打印机
            for printer_entry in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1):
                name = _printer_name_from_enum_entry(printer_entry)
                if not name:
                    continue
                printer_handle = None
                try:
                    printer_handle = win32print.OpenPrinter(name)
                    printer_info = win32print.GetPrinter(printer_handle, 2)

                    status_code = printer_info["Status"]
                    work_offline = (
                        printer_info["Attributes"] & win32print.PRINTER_ATTRIBUTE_WORK_OFFLINE
                    ) != 0
                    status = PrinterDriverService._get_printer_status_from_code(
                        status_code, work_offline
                    )

                    is_default = name == win32print.GetDefaultPrinter()

                    printers.append(
                        PrinterInfo(
                            name=name,
                            status=status,
                            is_default=is_default,
                            location=printer_info.get("pLocation", ""),
                            driver_name=printer_info.get("pDriverName", ""),
                            port_name=printer_info.get("pPortName", ""),
                        )
                    )
                except Exception as e:
                    print(f"Error getting printer info for {name}: {e}")
                finally:
                    if printer_handle:
                        win32print.ClosePrinter(printer_handle)
        except Exception as e:
            print(f"Error discovering printers: {e}")
            # 降级方案：使用wmic命令
            try:
                result = subprocess.run(
                    ["wmic", "printer", "get", "name,printerstatus,workoffline,default,location"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                lines = result.stdout.strip().split("\n")[1:]  # 跳过表头
                for line in lines:
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) < 4:
                        continue
                    name = " ".join(parts[:-3])
                    status_code = int(parts[-3])
                    work_offline = parts[-2].lower() == "true"
                    is_default = parts[-1].lower() == "true"

                    status = PrinterDriverService._get_printer_status_from_code(
                        status_code, work_offline
                    )

                    printers.append(PrinterInfo(name=name, status=status, is_default=is_default))
            except Exception as e2:
                print(f"Fallback wmic discovery failed: {e2}")

        return printers

    @staticmethod
    async def get_printer_status(printer_name: str) -> PrinterStatus:
        """获取打印机状态"""
        try:
            printer_handle = win32print.OpenPrinter(printer_name)
            try:
                printer_info = win32print.GetPrinter(printer_handle, 2)
                status_code = printer_info["Status"]
                work_offline = (
                    printer_info["Attributes"] & win32print.PRINTER_ATTRIBUTE_WORK_OFFLINE
                ) != 0
                return PrinterDriverService._get_printer_status_from_code(status_code, work_offline)
            finally:
                win32print.ClosePrinter(printer_handle)
        except Exception as e:
            print(f"Error getting printer status: {e}")
            return PrinterStatus.OFFLINE

    @staticmethod
    async def print_file(printer_name: str, file_path: str, copies: int = 1) -> bool:
        """发送文件到打印机。

        优先使用能反馈退出码的 PowerShell ``Start-Process -Verb Print -Wait``，
        因为 ``ShellExecute`` 是异步触发 shell 的 print 动词、不反馈打印结果，
        且其 ``/d:`` 参数会被多数打印处理程序忽略而打到默认打印机——据此把任务
        标记为成功会掩盖真实失败并可能打错打印机。仅在 PowerShell 不可用时退回
        ``ShellExecute``。
        """
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False

        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    (
                        "$ErrorActionPreference='Stop'; "
                        f'Start-Process -FilePath "{file_path}" -Verb Print '
                        f'-ArgumentList "/d:{printer_name}" -Wait -PassThru | Out-Null'
                    ),
                ],
                capture_output=True,
                timeout=60,
            )
            if result.returncode == 0:
                return True
            print(
                "PowerShell print failed "
                f"(rc={result.returncode}): {result.stderr.decode(errors='ignore')}"
            )
            return False
        except Exception as e:
            print(f"PowerShell print failed, fallback to ShellExecute: {e}")

        try:
            # 退路：ShellExecute 不反馈打印结果，只能保证已把文件交给 shell。
            win32api.ShellExecute(0, "print", file_path, f'/d:"{printer_name}"', ".", 0)
            return True
        except Exception as e2:
            print(f"ShellExecute print failed: {e2}")
            return False

    @staticmethod
    async def get_print_queue(printer_name: str) -> List[PrintQueueItem]:
        """获取打印队列"""
        queue = []
        try:
            printer_handle = win32print.OpenPrinter(printer_name)
            try:
                jobs = win32print.EnumJobs(printer_handle, 0, -1, 1)
                for job in jobs:
                    submitted_time = (
                        datetime.fromtimestamp(job["Submitted"]).isoformat()
                        if job.get("Submitted")
                        else ""
                    )
                    queue.append(
                        PrintQueueItem(
                            job_id=job["JobId"],
                            document=job["pDocument"],
                            user=job["pUserName"],
                            status=win32print.JOB_STATUS_CODES.get(job["Status"], "Unknown"),
                            pages_total=job["TotalPages"],
                            pages_printed=job["PagesPrinted"],
                            submitted_time=submitted_time,
                        )
                    )
                return queue
            finally:
                win32print.ClosePrinter(printer_handle)
        except Exception as e:
            print(f"Error getting print queue: {e}")
            return []

    @staticmethod
    async def cancel_print_job(printer_name: str, job_id: int) -> bool:
        """取消打印任务"""
        try:
            printer_handle = win32print.OpenPrinter(printer_name)
            try:
                win32print.SetJob(printer_handle, job_id, 0, None, win32print.JOB_CONTROL_DELETE)
                return True
            finally:
                win32print.ClosePrinter(printer_handle)
        except Exception as e:
            print(f"Error canceling print job: {e}")
            return False

    @staticmethod
    async def print_test_page(printer_name: str) -> bool:
        """打印测试页"""
        try:
            # 创建临时测试页
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as f:
                f.write("=== 打印机测试页 ===\n")
                f.write(f"打印机: {printer_name}\n")
                f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("\n如果您能看到此页，说明打印机工作正常。\n")
                f.write("\n校准测试:")
                f.write("\n□ 左上角对齐标记")
                f.write("\n□ 右上角对齐标记")
                f.write("\n□ 左下角对齐标记")
                f.write("\n□ 右下角对齐标记")
                f.write("\n" * 5)
                temp_path = f.name

            success = await PrinterDriverService.print_file(printer_name, temp_path)
            os.unlink(temp_path)
            return success
        except Exception as e:
            print(f"Error printing test page: {e}")
            return False
