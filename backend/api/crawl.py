from fastapi import APIRouter

router = APIRouter(prefix="/crawl", tags=["Crawl"])

@router.get("/status")
async def get_crawl_status():
    """Placeholder crawl module status check for Phase 1."""
    return {
        "module": "crawler",
        "status": "ready",
        "phase": "placeholder"
    }
