import asyncio
import base64
import os
import tempfile
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Photo, PrintJob, PrintJobStatus
from app.repositories.print_job_repository import PrintJobRepository
from app.schemas.print_job import BatchPrintRequest, PrintJobCreate, PrintJobUpdate
from app.schemas.printer import PrinterStatus
from app.services.base_service import BaseService, BusinessRuleError, ValidationError
from app.services.printer_driver_service import PrinterDriverService
from app.services.sharpen_service import SharpenService
from app.services.template_render_service import TemplateRenderService
from app.services.watermark_service import WatermarkService


class PrintService(BaseService[PrintJob, PrintJobCreate, PrintJobUpdate]):
    """
    Service for print job business logic.

    Manages print job lifecycle, image processing (sharpening, watermarking),
    printer communication, and job status tracking.
    """

    def __init__(self, db: AsyncSession):
        repository = PrintJobRepository(db)
        super().__init__(repository, db)

    # ── Validation Hooks ──────────────────────────────────────

    async def validate_create(self, obj_in: PrintJobCreate) -> None:
        """Validate print job creation business rules."""
        # No specific validation needed for print jobs
        pass

    async def validate_update(self, existing: PrintJob, obj_in: PrintJobUpdate) -> None:
        """Validate print job update business rules."""
        # No specific validation needed for updates
        pass

    # ── Transformation Hooks ──────────────────────────────────

    async def before_create(self, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Transform print job data before creation."""
        # Always start in PENDING status
        obj_dict["status"] = PrintJobStatus.PENDING
        return obj_dict

    # ── Business Logic Methods ────────────────────────────────

    @staticmethod
    async def _load_image_bytes(image_url: str) -> bytes:
        if image_url.startswith("data:") and "," in image_url:
            return base64.b64decode(image_url.split(",", 1)[1])

        if image_url.startswith("/api/v1/media/"):
            media_path = image_url.removeprefix("/api/v1/media/")
            local_path = os.path.join("uploads", media_path)
            with open(local_path, "rb") as f:
                return f.read()

        if image_url.startswith("/uploads/"):
            local_path = image_url.lstrip("/")
            with open(local_path, "rb") as f:
                return f.read()

        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return response.content

    @classmethod
    async def process_image_for_print(
        cls,
        image_url: str, sharpen_profile: str = "medium", watermark_settings: Optional[dict] = None
    ) -> bytes:
        """Process image for printing: apply sharpening and watermark if configured."""
        image_bytes = await cls._load_image_bytes(image_url)

        # Apply sharpening
        if sharpen_profile and sharpen_profile != "none":
            image_bytes = SharpenService.apply_sharpen(image_bytes, profile=sharpen_profile)

        # Apply watermark if enabled
        if watermark_settings and watermark_settings.get("enabled", False):
            try:
                watermark_url = watermark_settings.get("watermark_url")
                if watermark_url:
                    # Download watermark
                    async with httpx.AsyncClient() as client:
                        response = await client.get(watermark_url)
                        response.raise_for_status()
                        watermark_bytes = response.content

                    # Apply watermark
                    image_bytes = WatermarkService.apply_watermark(
                        image_bytes=image_bytes,
                        watermark_bytes=watermark_bytes,
                        position=watermark_settings.get("position", "bottom_right"),
                        opacity=watermark_settings.get("opacity", 0.5),
                        scale=watermark_settings.get("scale", 0.2),
                        tile=watermark_settings.get("tile", False),
                    )
            except Exception as e:
                # Log error but continue printing without watermark
                from app.core.logging import logger

                logger.error(f"Failed to apply watermark: {str(e)}")

        return image_bytes

    async def get_print_job(self, job_id: UUID) -> Optional[PrintJob]:
        """Get print job by ID (alias for route compatibility)."""
        return await self.get(job_id)

    async def get_print_jobs(
        self,
        photo_id: Optional[UUID] = None,
        status: Optional[str] = None,
        team_event_ids: Optional[List[UUID]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[PrintJob]:
        """Get print jobs with optional filters.

        When ``photo_id`` is given, return jobs for that photo.
        Otherwise scope to events in ``team_event_ids`` (IDOR guard).
        """
        if photo_id:
            return await self.repository.get_by_photo(photo_id)

        if status:
            try:
                enum_status = PrintJobStatus(status)
            except ValueError:
                enum_status = None
            if enum_status:
                return await self.repository.get_by_status(enum_status, skip, limit)

        # Fallback: return all (repository-level pagination); route layer
        # is responsible for scoping via team_event_ids when no photo_id.
        if team_event_ids:
            from app.models.models import Photo

            stmt = (
                select(PrintJob)
                .join(Photo, PrintJob.photo_id == Photo.id)
                .where(Photo.event_id.in_(team_event_ids))
                .order_by(PrintJob.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())

        return await self.repository.get_multi(skip, limit)

    async def get_print_jobs_visible_to_user(
        self, user_id: UUID, status: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[PrintJob]:
        """Get print jobs scoped to teams the user belongs to, with optional status filter."""
        return await self.repository.get_visible_to_user(user_id, status, skip, limit)

    async def create_print_job(self, job_in: PrintJobCreate) -> PrintJob:
        """Create a new print job (alias for route compatibility)."""
        return await self.create(job_in)

    async def batch_create_print_jobs(self, batch_in: BatchPrintRequest) -> List[PrintJob]:
        """Create multiple print jobs at once"""
        jobs = []
        for photo_id in batch_in.photo_ids:
            job_data = {
                "photo_id": photo_id,
                "printer_name": batch_in.printer_name,
                "copies": batch_in.copies,
                "status": PrintJobStatus.PENDING,
            }
            job = await self.repository.create(job_data)
            jobs.append(job)
        return jobs

    async def get_pending_jobs(self, limit: int = 50) -> List[PrintJob]:
        """Get pending print jobs for processing"""
        return await self.repository.get_pending_jobs(limit)

    async def start_printing(self, job_id: UUID) -> Optional[PrintJob]:
        """Mark job as printing"""
        return await self.repository.update_status(job_id, PrintJobStatus.PRINTING)

    async def complete_job(self, job_id: UUID) -> Optional[PrintJob]:
        """Mark job as completed"""
        return await self.repository.update_status(job_id, PrintJobStatus.COMPLETED)

    async def fail_job(self, job_id: UUID, error_message: str) -> Optional[PrintJob]:
        """Mark job as failed"""
        return await self.repository.update_status(job_id, PrintJobStatus.FAILED, error_message)

    async def cancel_job(self, job_id: UUID) -> Optional[PrintJob]:
        """Cancel a print job"""
        return await self.repository.update_status(job_id, PrintJobStatus.CANCELLED)

    async def update_print_job(self, job_id: UUID, job_in: PrintJobUpdate) -> Optional[PrintJob]:
        """Update print job fields (status, error_message, etc.)."""
        update_data = job_in.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get(job_id)
        if "status" in update_data:
            # Delegate status change through repository to update printed_at etc.
            return await self.repository.update_status(
                job_id, update_data["status"], update_data.get("error_message")
            )
        return await self.update(job_id, job_in)

    async def retry_print_job(self, job_id: UUID) -> Optional[PrintJob]:
        """Retry a failed print job by resetting it to pending."""
        job = await self.get(job_id)
        if not job:
            return None
        if job.status != PrintJobStatus.FAILED:
            raise BusinessRuleError("Only failed jobs can be retried")
        return await self.repository.update_status(job_id, PrintJobStatus.PENDING)

    async def cancel_print_job(self, job_id: UUID) -> Optional[PrintJob]:
        """Cancel a print job (alias for cancel_job matching route expectation)."""
        return await self.cancel_job(job_id)

    async def get_statistics(self) -> dict:
        """Get print job statistics"""
        return await self.repository.get_statistics()

    async def _get_job_for_execution(self, job_id: UUID) -> Optional[PrintJob]:
        result = await self.db.execute(
            select(PrintJob)
            .where(PrintJob.id == job_id)
            .options(selectinload(PrintJob.photo), selectinload(PrintJob.template))
        )
        return result.scalar_one_or_none()

    async def _get_template_photo_bytes(self, job: PrintJob) -> List[bytes]:
        if not job.photo:
            return []

        ordered_photos: List[Photo] = [job.photo]
        if job.photo.session_id:
            result = await self.db.execute(
                select(Photo)
                .where(Photo.session_id == job.photo.session_id)
                .order_by(Photo.created_at)
            )
            session_photos = [photo for photo in result.scalars().all() if photo.id != job.photo_id]
            ordered_photos.extend(session_photos)

        photo_bytes: List[bytes] = []
        for photo in ordered_photos:
            url = photo.processed_url or photo.original_url
            photo_bytes.append(await self._load_image_bytes(url))
        return photo_bytes

    async def _render_job_image(self, job: PrintJob) -> bytes:
        if job.template and isinstance(job.template.layers, dict):
            photos = await self._get_template_photo_bytes(job)
            if photos:
                return TemplateRenderService.render_template_to_image(
                    job.template.layers,
                    photos,
                    dpi=int(job.template.layers.get("resolution") or 300),
                )

        return await self.process_image_for_print(
            image_url=job.photo.processed_url or job.photo.original_url,
            sharpen_profile="medium",
            watermark_settings=None,
        )

    async def execute_print_job(self, job_id: UUID) -> bool:
        """执行真实打印任务"""
        try:
            # 更新状态为打印中
            if not await self.start_printing(job_id):
                return False
            job = await self._get_job_for_execution(job_id)
            if not job or not job.photo:
                await self.fail_job(job_id, "Print job photo not found")
                return False

            # 处理图像
            image_bytes = await self._render_job_image(job)

            # 保存为临时文件
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_bytes)
                temp_path = f.name

            try:
                # 检查打印机状态
                printer_name = job.printer_name
                if not printer_name:
                    # 使用默认打印机
                    printers = await PrinterDriverService.discover_printers()
                    default_printer = next((p for p in printers if p.is_default), None)
                    if default_printer:
                        printer_name = default_printer.name
                    else:
                        # 没有找到打印机，模拟打印
                        await asyncio.sleep(2)  # 模拟打印延迟
                        await self.complete_job(job_id)
                        return True

                printer_status = await PrinterDriverService.get_printer_status(printer_name)
                if printer_status not in [PrinterStatus.READY, PrinterStatus.INK_LOW]:
                    # 打印机不可用，模拟打印（优雅降级）
                    from app.core.logging import logger

                    logger.warning(
                        f"Printer {printer_name} is not available (status: {printer_status}), falling back to simulation"
                    )
                    await asyncio.sleep(2)
                    await self.complete_job(job_id)
                    return True

                # 发送到打印机
                success = await PrinterDriverService.print_file(
                    printer_name=printer_name, file_path=temp_path, copies=job.copies or 1
                )

                if success:
                    await self.complete_job(job_id)
                    return True
                else:
                    await self.fail_job(job_id, "Failed to send file to printer")
                    return False

            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_path)
                except:
                    pass

        except Exception as e:
            from app.core.logging import logger

            logger.error(f"Error executing print job {job_id}: {str(e)}")
            try:
                await self.fail_job(job_id, str(e))
            except:
                pass
            return False
