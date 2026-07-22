from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class StageTiming(BaseModel):
    planning_ms: Optional[int] = None
    search_ms: Optional[int] = None
    crawl_ms: Optional[int] = None
    extraction_ms: Optional[int] = None
    embedding_ms: Optional[int] = None
    retrieval_ms: Optional[int] = None
    coverage_analysis_ms: Optional[int] = None
    llm_generation_ms: Optional[int] = None
    total_ms: Optional[int] = None

class ObservabilityMetrics(BaseModel):
    request_id: str
    research_id: Optional[int] = None
    query: str
    status: str
    timings: StageTiming = Field(default_factory=StageTiming)
    llm_calls: int = 0
    search_requests: int = 0
    pages_crawled: int = 0
    chunks_indexed: int = 0
    failed_crawls: int = 0
    error_code: Optional[str] = None
