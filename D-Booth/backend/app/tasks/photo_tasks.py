import asyncio
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import aioboto3
import requests
from botocore.exceptions import ClientError
from celery import shared_task
from PIL import Image, ImageEnhance, ImageFilter

from app.celery_app import celery_app
from app.core.config import settings
from app.core.logging import logger


def _r2_public_url(object_key: str) -> str:
    """Build a publicly reachable R2 URL for a stored object key.

    The R2 S3 API endpoint does not serve anonymous GETs, so a configured
    public base (pub-*.r2.dev or a custom domain) must be used when present.
    """
    public_base = settings.R2_PUBLIC_URL.rstrip("/")
    if public_base:
        return f"{public_base}/{object_key}"
    return f"{settings.R2_ENDPOINT_URL}/{settings.R2_BUCKET_NAME}/{object_key}"


def get_s3_client():
    """Get synchronous S3 client for Celery tasks (legacy)"""
    if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
        return None

    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name=settings.R2_REGION,
    )


async def upload_to_s3_async(
    file_data: bytes, filename: str, content_type: str, folder: str
) -> str:
    """
    Asynchronous S3 upload using aioboto3.
    Much faster than synchronous uploads, allows Celery worker to handle more tasks.
    """
    from uuid import uuid4

    if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
        raise RuntimeError("S3 credentials not configured")
    file_ext = filename.split(".")[-1] if "." in filename else ""
    unique_filename = f"{uuid4()}.{file_ext}" if file_ext else str(uuid4())
    object_key = f"{folder}/{unique_filename}"

    session = aioboto3.Session()
    try:
        async with session.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name=settings.R2_REGION,
        ) as s3:
            await s3.put_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=object_key,
                Body=file_data,
                ContentType=content_type,
                CacheControl="public, max-age=31536000",
            )

            public_url = _r2_public_url(object_key)
            logger.info(f"Async upload completed: {object_key}")
            return public_url

    except ClientError as e:
        logger.error(f"Failed to upload to S3 (async): {e}")
        raise


@celery_app.task(bind=True, max_retries=3)
def process_photo(self, photo_url: str, photo_id: str, operations: dict = None):
    """
    Process a photo with various operations (resize, filter, enhance).
    Uses async S3 upload for better performance.

    Args:
        photo_url: URL of the photo to process
        photo_id: Database ID of the photo
        operations: Dict of operations to apply
    """
    try:
        logger.info(f"Processing photo {photo_id}")

        # Download photo
        response = requests.get(photo_url, timeout=30)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))

        operations = operations or {}

        # Apply operations
        if operations.get("resize"):
            size = operations["resize"]
            image = image.resize((size["width"], size["height"]), Image.Resampling.LANCZOS)

        if operations.get("brightness"):
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(operations["brightness"])

        if operations.get("contrast"):
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(operations["contrast"])

        if operations.get("blur"):
            image = image.filter(ImageFilter.GaussianBlur(operations["blur"]))

        if operations.get("sharpen"):
            image = image.filter(ImageFilter.SHARPEN)

        # Save processed image
        output = BytesIO()
        image.save(output, format="JPEG", quality=90)
        processed_data = output.getvalue()

        # Upload processed image (asynchronous for better performance)
        if settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                processed_url = loop.run_until_complete(
                    upload_to_s3_async(
                        file_data=processed_data,
                        filename=f"processed_{photo_id}.jpg",
                        content_type="image/jpeg",
                        folder="photos/processed",
                    )
                )
            finally:
                loop.close()
        else:
            logger.warning("S3 client not available, saving locally")
            local_dir = Path("uploads/photos/processed")
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / f"processed_{photo_id}.jpg"
            local_path.write_bytes(processed_data)
            processed_url = f"/uploads/photos/processed/processed_{photo_id}.jpg"

        logger.info(f"Photo {photo_id} processed successfully")

        return {"status": "completed", "photo_id": photo_id, "processed_url": processed_url}

    except Exception as e:
        logger.error(f"Failed to process photo {photo_id}: {e}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def generate_collage(self, photo_urls: list, layout: str = "grid"):
    """
    Generate a collage from multiple photos.
    Uses async S3 upload for better performance.

    Args:
        photo_urls: List of photo URLs
        layout: Collage layout type
    """
    try:
        logger.info(f"Generating collage with {len(photo_urls)} photos")

        images = []
        for url in photo_urls:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            images.append(Image.open(BytesIO(response.content)))

        # Create grid collage
        if layout == "grid":
            cols = 2
            rows = (len(images) + cols - 1) // cols
            cell_width = 400
            cell_height = 400

            collage = Image.new("RGB", (cols * cell_width, rows * cell_height), "white")

            for idx, img in enumerate(images):
                img.thumbnail((cell_width, cell_height), Image.Resampling.LANCZOS)
                x = (idx % cols) * cell_width
                y = (idx // cols) * cell_height
                collage.paste(img, (x, y))

        # Save collage
        output = BytesIO()
        collage.save(output, format="JPEG", quality=90)
        collage_data = output.getvalue()

        # Upload (asynchronous for better performance)
        if settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                collage_url = loop.run_until_complete(
                    upload_to_s3_async(
                        file_data=collage_data,
                        filename="collage.jpg",
                        content_type="image/jpeg",
                        folder="photos/collages",
                    )
                )
            finally:
                loop.close()
        else:
            logger.warning("S3 client not available, saving locally")
            local_dir = Path("uploads/photos/collages")
            local_dir.mkdir(parents=True, exist_ok=True)
            collage_name = f"collage_{uuid4().hex}.jpg"
            local_path = local_dir / collage_name
            local_path.write_bytes(collage_data)
            collage_url = f"/uploads/photos/collages/{collage_name}"

        logger.info("Collage generated successfully")

        return {"status": "completed", "collage_url": collage_url}

    except Exception as e:
        logger.error(f"Failed to generate collage: {e}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task
def cleanup_expired_shares():
    """Periodic task to clean up expired share links"""
    try:
        logger.info("Running cleanup for expired shares")

        import asyncio
        from datetime import datetime, timezone

        from sqlalchemy import delete

        from app.core.database import async_session_maker
        from app.models.models import Share

        async def _cleanup():
            async with async_session_maker() as db:
                stmt = delete(Share).where(Share.expires_at < datetime.now(timezone.utc))
                result = await db.execute(stmt)
                await db.commit()
                return result.rowcount

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            deleted_count = loop.run_until_complete(_cleanup())
        finally:
            loop.close()

        logger.info(f"Cleaned up {deleted_count} expired shares")

        return {"status": "completed", "deleted": deleted_count}

    except Exception as e:
        logger.error(f"Failed to cleanup expired shares: {e}")
        return {"status": "failed", "error": str(e)}
