from celery import Celery
from backend.core.config import settings

celery_app = Celery(
    "ai_search_engine_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Optional configuration overrides
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Auto-discover tasks in backend packages if needed later
# celery_app.autodiscover_tasks(['backend.api'])
