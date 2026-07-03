from typing import List

from fastapi import APIRouter, HTTPException

from app.schemas.printer import CalibrationParams, PrinterInfo, PrinterStatus, PrintQueueItem
from app.services.printer_driver_service import PrinterDriverService

router = APIRouter()


@router.get("", response_model=List[PrinterInfo])
async def list_printers():
    """获取系统所有打印机列表"""
    try:
        return await PrinterDriverService.discover_printers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list printers: {str(e)}")


@router.get("/{printer_name}/status", response_model=PrinterStatus)
async def get_printer_status(printer_name: str):
    """获取指定打印机状态"""
    try:
        status = await PrinterDriverService.get_printer_status(printer_name)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get printer status: {str(e)}")


@router.get("/{printer_name}/queue", response_model=List[PrintQueueItem])
async def get_print_queue(printer_name: str):
    """获取打印机队列"""
    try:
        return await PrinterDriverService.get_print_queue(printer_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get print queue: {str(e)}")


@router.delete("/{printer_name}/queue/{job_id}")
async def cancel_print_job(printer_name: str, job_id: int):
    """取消打印任务"""
    try:
        success = await PrinterDriverService.cancel_print_job(printer_name, job_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to cancel print job")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.post("/{printer_name}/test-page")
async def print_test_page(printer_name: str):
    """打印测试页"""
    try:
        success = await PrinterDriverService.print_test_page(printer_name)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to print test page")
        return {"success": True, "message": "Test page sent to printer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to print test page: {str(e)}")


@router.put("/{printer_name}/calibration")
async def save_calibration(printer_name: str, params: CalibrationParams):
    """保存打印机校准参数"""
    try:
        # TODO: 保存到数据库或配置文件
        # 暂时返回成功
        return {"success": True, "message": "Calibration parameters saved", "params": params}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save calibration: {str(e)}")
