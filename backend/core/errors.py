from enum import Enum
from typing import Dict

class ErrorCategory(str, Enum):
    SEARCH_FAILED = "SEARCH_FAILED"
    CRAWL_TIMEOUT = "CRAWL_TIMEOUT"
    CRAWL_BLOCKED = "CRAWL_BLOCKED"
    ROBOTS_DENIED = "ROBOTS_DENIED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EMBEDDING_FAILED = "EMBEDDING_FAILED"
    QDRANT_UNAVAILABLE = "QDRANT_UNAVAILABLE"
    RETRIEVAL_FAILED = "RETRIEVAL_FAILED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    LLM_AUTH_FAILED = "LLM_AUTH_FAILED"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    DATABASE_ERROR = "DATABASE_ERROR"
    RESEARCH_TIMEOUT = "RESEARCH_TIMEOUT"

# Human-readable user-friendly messages representing standard errors
USER_ERROR_MESSAGES: Dict[ErrorCategory, str] = {
    ErrorCategory.SEARCH_FAILED: "The metasearch service failed to retrieve search candidates. Please verify search engine status.",
    ErrorCategory.CRAWL_TIMEOUT: "Request timed out while downloading source web content.",
    ErrorCategory.CRAWL_BLOCKED: "Security access restriction prevented scraping of source content.",
    ErrorCategory.ROBOTS_DENIED: "Website robots.txt rules restrict automated analysis of this source.",
    ErrorCategory.EXTRACTION_FAILED: "Failed to parse text nodes or clean document HTML content.",
    ErrorCategory.EMBEDDING_FAILED: "Could not generate vector embeddings for evidence chunks.",
    ErrorCategory.QDRANT_UNAVAILABLE: "Vector storage database connection is unavailable.",
    ErrorCategory.RETRIEVAL_FAILED: "Retrieval query against semantic vectors failed.",
    ErrorCategory.INSUFFICIENT_EVIDENCE: "I couldn't find enough reliable evidence in the retrieved sources to answer this confidently.",
    ErrorCategory.LLM_RATE_LIMIT: "The AI text generator is currently rate-limited. Retrying with fallback options.",
    ErrorCategory.LLM_AUTH_FAILED: "AI service authentication error. Verify configuration keys.",
    ErrorCategory.LLM_TIMEOUT: "Generative model timed out while synthesizing response.",
    ErrorCategory.DATABASE_ERROR: "Database operations error occurred. Session metrics could not be logged.",
    ErrorCategory.RESEARCH_TIMEOUT: "Autonomous deep research loop exceeded time budget limits."
}

class AppError(Exception):
    """
    Standardized Application Exception mapping backend errors to category and user-facing messages.
    """
    def __init__(self, category: ErrorCategory, detail: Optional[str] = None):
        self.category = category
        self.detail = detail
        self.user_message = USER_ERROR_MESSAGES.get(category, "An unexpected application error occurred.")
        super().__init__(self.user_message)

from typing import Optional
