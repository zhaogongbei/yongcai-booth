"""
Celery async tasks for beauty processing.
Offloads heavy CPU work from the web server to background workers.
"""

from uuid import UUID

from celery import shared_task

from app.celery_app import celery_app
from app.core.logging import logger


@celery_app.task(bind=True, max_retries=2, soft_time_limit=30, time_limit=45)
def apply_beauty_task(
    self,
    photo_id: str,
    image_url: str,
    params: dict,
    quality: str = "full",
) -> dict:
    """
    Apply beauty processing to an already-uploaded photo.

    1. Download original from storage (R2 / local)
    2. Run BeautyProcessor pipeline
    3. Upload result back to storage
    4. Update Photo record with processed_url

    Returns: {"status": "completed", "photo_id": ..., "processed_url": ...}
    """
    import asyncio
    import io

    import requests

    from app.services.beauty_service import BeautyParams, beauty_processor
    from app.tasks.photo_tasks import upload_to_s3_async

    logger.info(f"beauty task started: photo={photo_id}  q={quality}")

    try:
        # 1. Download original
        resp = requests.get(image_url, timeout=20)
        resp.raise_for_status()
        image_bytes = resp.content

        # 2. Build params
        bp = BeautyParams(**{k: params.get(k, 50) for k in BeautyParams.model_fields})

        # 3. Process
        result = beauty_processor.process_image(image_bytes, bp, quality=quality)

        # 4. Upload result to storage
        from app.core.config import settings

        safe_name = f"beauty_{photo_id}.jpg"
        if settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                processed_url = loop.run_until_complete(
                    upload_to_s3_async(
                        file_data=result,
                        filename=safe_name,
                        content_type="image/jpeg",
                        folder="photos/beauty",
                    )
                )
            finally:
                loop.close()
        else:
            from pathlib import Path

            target_dir = Path("uploads/photos/beauty")
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / safe_name
            target_path.write_bytes(result)
            processed_url = f"/uploads/photos/beauty/{safe_name}"

        # 5. Update photo record in DB
        from sqlalchemy import update

        from app.core.database import async_session_maker
        from app.models.models import Photo

        async def _update():
            async with async_session_maker() as db:
                stmt = (
                    update(Photo)
                    .where(Photo.id == UUID(photo_id))
                    .values(processed_url=processed_url)
                )
                await db.execute(stmt)
                await db.commit()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_update())
        finally:
            loop.close()

        logger.info(f"beauty task completed: photo={photo_id}")
        return {"status": "completed", "photo_id": photo_id, "processed_url": processed_url}

    except Exception as e:
        logger.error(f"beauty task failed: photo={photo_id}  {e}")
        raise self.retry(exc=e, countdown=30)
