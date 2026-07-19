from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("")
async def send_chat_message(message: str):
    """Placeholder chat/LLM response endpoint."""
    return {
        "status": "success",
        "response": f"Mock chat response to message: '{message}' (Phase 1 Placeholder)"
    }
