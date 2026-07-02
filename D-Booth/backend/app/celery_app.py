from celery import Celery
from app.core.config import settings

# Create Celery application
celery_app = Celery(
    "aibooth",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.photo_tasks",
        "app.tasks.ai_tasks",
        "app.tasks.email_tasks",
        "app.tasks.beauty_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
    task_routes={
        "app.tasks.photo_tasks.*": {"queue": "photos"},
        "app.tasks.ai_tasks.*": {"queue": "ai"},
        "app.tasks.email_tasks.*": {"queue": "email"},
        "app.tasks.beauty_tasks.*": {"queue": "beauty"},
    },
)

# Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "cleanup-expired-shares": {
        "task": "app.tasks.photo_tasks.cleanup_expired_shares",
        "schedule": 3600.0,  # Every hour
    },
}


if __name__ == "__main__":
    celery_app.start()
