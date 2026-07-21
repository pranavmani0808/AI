from fastapi import APIRouter

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/status")
async def get_search_status():
    """Placeholder search module status check for Phase 1."""
    return {
        "module": "search",
        "status": "ready",
        "phase": "placeholder"
    }
