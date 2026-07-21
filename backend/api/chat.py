from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/status")
async def get_chat_status():
    """Placeholder chat module status check for Phase 1."""
    return {
        "module": "chat",
        "status": "ready",
        "phase": "placeholder"
    }
