from fastapi import APIRouter, status, Response
from sqlalchemy import text
from typing import Dict, Any

from backend.database.postgres import AsyncSessionLocal
from backend.database.redis import check_redis_health
from backend.services.qdrant import check_qdrant_health
from backend.services.searxng import check_searxng_health
from backend.core.config import settings

router = APIRouter(tags=["System Status"])

async def check_postgres_health() -> bool:
    """Executes SELECT 1 on database session to verify Postgres operational health."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"Postgres health check failed: {e}")
        return False

@router.get("/health")
async def get_system_health():
    """
    Check operational statuses of Redis, Postgres, Qdrant, and SearXNG.
    Does NOT call external LLM models.
    """
    pg_ok = await check_postgres_health()
    redis_ok = await check_redis_health()
    qdrant_ok = await check_qdrant_health()
    searxng_ok = await check_searxng_health()
    
    overall = "healthy" if (pg_ok and redis_ok and qdrant_ok and searxng_ok) else "degraded"
    
    return {
        "status": overall,
        "services": {
            "postgres": "healthy" if pg_ok else "unhealthy",
            "redis": "healthy" if redis_ok else "unhealthy",
            "qdrant": "healthy" if qdrant_ok else "unhealthy",
            "searxng": "healthy" if searxng_ok else "unhealthy"
        }
    }

@router.get("/ready")
async def get_system_readiness(response: Response):
    """
    Determines if the application is ready to accept research requests.
    Checks critical configurations and service states.
    Returns HTTP 503 if critical dependencies are down.
    """
    pg_ok = await check_postgres_health()
    qdrant_ok = await check_qdrant_health()
    searxng_ok = await check_searxng_health()
    
    # Embedding config check: verify local embedding provider works
    embedding_ok = True
    try:
        from backend.rag.vector_store import get_qdrant_client
        client = get_qdrant_client()
        collections = client.get_collections().collections
        embedding_ok = any(c.name == settings.QDRANT_COLLECTION for c in collections)
    except Exception as e:
        print(f"Readiness check - embedding collection missing or client error: {e}")
        embedding_ok = False
        
    config_ok = bool(settings.GEMINI_API_KEY)
    
    is_ready = pg_ok and qdrant_ok and searxng_ok and embedding_ok and config_ok
    
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "reason": "Critical dependencies are offline or unconfigured.",
            "checks": {
                "postgres": "ok" if pg_ok else "error",
                "qdrant": "ok" if qdrant_ok else "error",
                "searxng": "ok" if searxng_ok else "error",
                "embedding_collection": "ok" if embedding_ok else "error",
                "gemini_config": "configured" if config_ok else "missing_api_key"
            }
        }
        
    return {
        "status": "ready",
        "message": "All critical systems operational and configurations loaded."
    }
