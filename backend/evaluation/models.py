from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class TestCaseResult(BaseModel):
    query_id: str
    query: str
    category: str
    success: bool
    latency_ms: int
    error_code: Optional[str] = None
    citation_metrics: Dict[str, Any]
    retrieval_metrics: Dict[str, Any]
    research_metrics: Dict[str, Any]
    answer: str

class BenchmarkReport(BaseModel):
    total_queries: int
    successful: int
    failed: int
    avg_latency_ms: int
    avg_citation_validity: float
    avg_citation_coverage: float
    avg_evidence_coverage: float
    avg_unique_sources: float
    avg_iterations: float
    stop_reasons: Dict[str, int]
    results: List[TestCaseResult]
