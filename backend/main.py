from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.database.postgres import check_postgres_health
from backend.database.redis import check_redis_health
from backend.services.qdrant import check_qdrant_health
from backend.services.searxng import check_searxng_health
from backend.api import search, crawl, chat

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend foundation for AI Search Engine with Autonomous Web Intelligence",
    version="1.0.0"
)

# Configure CORS dynamically using ALLOWED_ORIGINS config
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")] if settings.ALLOWED_ORIGINS else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers mounted with the /api prefix
app.include_router(search.router, prefix="/api")
app.include_router(crawl.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

@app.get("/", status_code=status.HTTP_200_OK)
async def read_root():
    """Verify application operational status."""
    return {
        "name": "AI Search Engine with Autonomous Web Intelligence",
        "status": "running"
    }

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Verify operational health of downstream system dependencies."""
    postgres_ok = await check_postgres_health()
    redis_ok = await check_redis_health()
    qdrant_ok = await check_qdrant_health()
    searxng_ok = await check_searxng_health()

    services_status = {
        "postgres": "connected" if postgres_ok else "unavailable",
        "redis": "connected" if redis_ok else "unavailable",
        "qdrant": "connected" if qdrant_ok else "unavailable",
        "searxng": "connected" if searxng_ok else "unavailable"
    }

    # If any dependency goes down, we report "degraded" health without crashing Uvicorn
    overall_status = "healthy" if all([postgres_ok, redis_ok, qdrant_ok, searxng_ok]) else "degraded"

    return {
        "status": overall_status,
        "services": services_status
    }
