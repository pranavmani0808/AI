import contextvars
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable that stays local to active async context
_request_id_var = contextvars.ContextVar("request_id", default="req_none")

def get_request_id() -> str:
    """Retrieves the active context-local Request ID."""
    return _request_id_var.get()

def set_request_id(request_id: str):
    """Overrides the active Request ID."""
    _request_id_var.set(request_id)

def generate_request_id() -> str:
    """Generates a UUID-based request tracker ID."""
    return f"req_{uuid.uuid4().hex[:16]}"

class RequestTrackerMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware ensuring every request receives a unique X-Request-ID.
    Saves the ID in the thread-safe contextvars local variable.
    """
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or generate_request_id()
        token = _request_id_var.set(request_id)
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            _request_id_var.reset(token)
