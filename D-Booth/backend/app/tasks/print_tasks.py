from celery import shared_task
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from app.services.print_service import PrintService
from app.core.logging import logger


@shared_task(bind=True, max_retries=3)
def execute_print_job_task(self, print_job_id: str):
    """Celery task to execute print job asynchronously"""
    import asyncio

    async def process_job():
        async with async_session() as db:
            print_service = PrintService(db)
            try:
                job_id = UUID(print_job_id)
                success = await print_service.execute_print_job(job_id)
                if not success:
                    logger.error(f"Print job {print_job_id} failed")
                    # 重试最多3次
                    if self.request.retries < 3:
                        self.retry(countdown=5 ** (self.request.retries + 1))
            except Exception as e:
                logger.error(f"Error processing print job {print_job_id}: {str(e)}")
                if self.request.retries < 3:
                    self.retry(exc=e, countdown=5 ** (self.request.retries + 1))

    asyncio.run(process_job())


@shared_task
def monitor_printers_task():
    """定时任务监控打印机状态"""
    import asyncio
    from app.services.printer_driver_service import PrinterDriverService

    async def monitor():
        try:
            printers = await PrinterDriverService.discover_printers()
            for printer in printers:
                if printer.status in ["paper_out", "ink_low", "error", "offline"]:
                    logger.warning(f"Printer {printer.name} status: {printer.status}")
                    # TODO: 发送告警通知
            logger.info(f"Printer monitor completed: {len(printers)} printers checked")
        except Exception as e:
            logger.error(f"Printer monitor failed: {str(e)}")

    asyncio.run(monitor())
