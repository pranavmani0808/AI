import logging
import json
import re
from typing import Any, Dict
from backend.observability.request_tracker import get_request_id

# Regex patterns to detect sensitive API keys/tokens in logging messages
API_KEY_PATTERNS = [
    re.compile(r"AQ\.[A-Za-z0-9_\-]+"), # Gemini keys
    re.compile(r"hf_[A-Za-z0-9]+"),      # HF tokens
    re.compile(r"bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE), # Auth headers
]

def redact_secrets(message: str) -> str:
    """Masks secret API tokens or database passwords in logging outputs."""
    if not isinstance(message, str):
        return message
        
    redacted = message
    for pattern in API_KEY_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
        
    return redacted

class StructuredJSONFormatter(logging.Formatter):
    """Formats log records into serialized JSON strings containing context IDs."""
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "request_id": get_request_id(),
            "component": record.name,
            "message": redact_secrets(record.getMessage())
        }
        
        # Capture additional context properties if passed
        for attr in ["duration_ms", "research_id", "status", "url", "query"]:
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)
                
        return json.dumps(log_data)

def setup_structured_logging():
    """Initializes JSON logging formatters on root logger stream handlers."""
    root_logger = logging.getLogger()
    
    # Avoid duplicate setups
    if root_logger.handlers:
        for handler in root_logger.handlers:
            if isinstance(handler.formatter, StructuredJSONFormatter):
                return
                
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = StructuredJSONFormatter(datefmt="%Y-%m-%dT%H:%M:%SZ")
    handler.setFormatter(formatter)
    
    # Clear existing default log handlers to ensure JSON exclusivity
    root_logger.handlers = [handler]

# Execute structured logging setup on package load
setup_structured_logging()
logger = logging.getLogger("ai_search_observability")
