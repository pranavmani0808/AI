from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import httpx

from backend.core.config import settings
from backend.database.postgres import check_postgres_health
from backend.database.redis import check_redis_health
from backend.api import search, crawl, chat

app = FastAPI(
    title="AI Search Engine API",
    description="Backend services for AI Search Engine (Phase 1 Setup)",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(search.router)
app.include_router(crawl.router)
app.include_router(chat.router)


async def check_qdrant_health() -> bool:
    """Verifies Qdrant connection health via HTTP endpoint."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}/")
            return res.status_code == 200
    except Exception as e:
        print(f"Qdrant health check failed: {e}")
        return False


async def check_searxng_health() -> bool:
    """Verifies SearXNG connection health via HTTP endpoint."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # We hit the home page of SearXNG which should return 200 OK
            res = await client.get(f"{settings.SEARXNG_URL}/")
            return res.status_code == 200
    except Exception as e:
        print(f"SearXNG health check failed: {e}")
        return False


@app.get("/health", status_code=status.HTTP_200_OK)
async def liveness_check():
    """Liveness check to verify the FastAPI application is running."""
    return {"status": "healthy", "service": "backend"}


@app.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """Readiness check verifying all downstream dependencies are reachable."""
    postgres_ok = await check_postgres_health()
    redis_ok = await check_redis_health()
    qdrant_ok = await check_qdrant_health()
    searxng_ok = await check_searxng_health()

    status_dict = {
        "postgres": "up" if postgres_ok else "down",
        "redis": "up" if redis_ok else "down",
        "qdrant": "up" if qdrant_ok else "down",
        "searxng": "up" if searxng_ok else "down",
    }

    if not all([postgres_ok, redis_ok, qdrant_ok, searxng_ok]):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unready", "dependencies": status_dict}
        )

    return {"status": "ready", "dependencies": status_dict}
