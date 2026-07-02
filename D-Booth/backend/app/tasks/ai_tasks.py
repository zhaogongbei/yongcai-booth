import asyncio
import base64
from decimal import Decimal
from typing import Tuple
from uuid import UUID

from app.celery_app import celery_app
from app.core.config import settings
from app.core.logging import logger


PROVIDER_IMAGE_COSTS = {
    "openai": Decimal("0.04"),
    "stability": Decimal("0.04"),
}


async def _update_task_progress(task_id: UUID, progress: Decimal, status: str) -> None:
    from app.core.database import async_session_maker
    from app.services.ai_service import AIService

    async with async_session_maker() as db:
        await AIService(db).update_progress(task_id, progress, status)


async def _complete_task(task_id: UUID, result_url: str, actual_cost: Decimal) -> None:
    from app.core.database import async_session_maker
    from app.services.ai_service import AIService

    async with async_session_maker() as db:
        await AIService(db).complete_task(task_id, result_url, actual_cost)


async def _fail_task(task_id: UUID, error_message: str) -> None:
    from app.core.database import async_session_maker
    from app.services.ai_service import AIService

    async with async_session_maker() as db:
        await AIService(db).fail_task(task_id, error_message)


def _upload_base64_image(image_base64: str, filename: str) -> str:
    from app.services.storage_service import r2_storage

    if not r2_storage.is_available():
        raise RuntimeError("Generated image returned as base64, but R2 storage is not configured")

    image_bytes = base64.b64decode(image_base64)
    return asyncio.run(
        r2_storage.upload_file(
            image_bytes,
            filename,
            content_type="image/png",
            folder="ai-generated",
        )
    )


def _generate_openai_image(prompt: str) -> Tuple[str, Decimal]:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        n=1,
        size="1024x1024",
    )

    if not response.data:
        raise RuntimeError("OpenAI image response did not include image data")

    image = response.data[0]
    if getattr(image, "url", None):
        return image.url, PROVIDER_IMAGE_COSTS["openai"]

    image_base64 = getattr(image, "b64_json", None)
    if image_base64:
        return _upload_base64_image(image_base64, "openai-generated.png"), PROVIDER_IMAGE_COSTS["openai"]

    raise RuntimeError("OpenAI image response did not include a URL or base64 image")


def _generate_stability_image(prompt: str) -> Tuple[str, Decimal]:
    if not settings.STABILITY_API_KEY:
        raise ValueError("STABILITY_API_KEY is not configured")

    import requests

    response = requests.post(
        "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/text-to-image",
        headers={
            "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
            "Accept": "application/json",
        },
        json={
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "steps": 30,
        },
        timeout=120,
    )
    response.raise_for_status()

    artifacts = response.json().get("artifacts") or []
    if not artifacts or not artifacts[0].get("base64"):
        raise RuntimeError("Stability image response did not include base64 image data")

    result_url = _upload_base64_image(artifacts[0]["base64"], "stability-generated.png")
    return result_url, PROVIDER_IMAGE_COSTS["stability"]


def _generate_image(prompt: str, provider: str) -> Tuple[str, Decimal]:
    if provider == "openai":
        return _generate_openai_image(prompt)
    if provider == "stability":
        return _generate_stability_image(prompt)
    raise ValueError(f"Unsupported AI provider: {provider}")


@celery_app.task(bind=True, max_retries=3)
def generate_ai_image(self, task_id: str, prompt: str, provider: str = "openai"):
    """
    Generate an AI image and persist task progress/result to the database.

    Args:
        task_id: Database ID of the AI task
        prompt: Text prompt for image generation
        provider: AI provider (openai, stability)
    """
    task_uuid = UUID(task_id)

    try:
        logger.info(f"Generating AI image for task {task_id} with {provider}")
        asyncio.run(_update_task_progress(task_uuid, Decimal(10), "processing"))

        result_url, actual_cost = _generate_image(prompt, provider)
        asyncio.run(_complete_task(task_uuid, result_url, actual_cost))

        logger.info(f"AI image generated successfully for task {task_id}")
        return {
            "status": "completed",
            "task_id": task_id,
            "result_url": result_url,
            "actual_cost": str(actual_cost),
        }

    except Exception as e:
        logger.error(f"Failed to generate AI image for task {task_id}: {e}")
        try:
            asyncio.run(_fail_task(task_uuid, str(e)))
        except Exception as update_error:
            logger.error(f"Failed to mark AI task {task_id} as failed: {update_error}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def process_ai_photo_enhancement(self, photo_url: str, task_id: str):
    """
    Enhance photo quality using AI

    Args:
        photo_url: URL of the photo to enhance
        task_id: Database ID of the AI task
    """
    try:
        logger.info(f"Enhancing photo for task {task_id}")

        # Placeholder for AI enhancement logic
        # In production, integrate with services like:
        # - Replicate (Real-ESRGAN, CodeFormer)
        # - Cloudflare AI
        # - Custom ML models

        logger.info(f"Photo enhanced successfully for task {task_id}")

        return {
            "status": "completed",
            "task_id": task_id,
            "result_url": photo_url,
        }

    except Exception as e:
        logger.error(f"Failed to enhance photo for task {task_id}: {e}")
        raise self.retry(exc=e, countdown=60)
