from celery import Celery
from backend.core.config import settings

celery_app = Celery(
    "ai_search_engine_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Auto-discover tasks in backend packages
celery_app.autodiscover_tasks(['backend.tasks'])

@celery_app.task(name="backend.core.celery_app.health_check_task")
def health_check_task() -> str:
    """Simple test task to verify Celery workers are functioning."""
    return "celery_worker_active"
