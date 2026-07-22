from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ResearchSubquery(BaseModel):
    id: int
    query: str
    purpose: str
    priority: str = "medium" # low, medium, high
    status: str = "pending" # pending, running, completed, failed

class ResearchPlan(BaseModel):
    original_query: str
    search_id: int
    objective: str
    subqueries: List[ResearchSubquery] = []
    max_iterations: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ResearchSource(BaseModel):
    url: str
    title: Optional[str] = None
    domain: Optional[str] = None
    source_type: str = "Unknown" # Primary / Official, High-quality secondary, Secondary, Unknown
    authority_score: float = 0.0
    relevance_score: float = 0.0
    freshness_score: float = 0.0
    overall_score: float = 0.0

class EvidenceItem(BaseModel):
    id: str # Can match chunk_id
    search_id: int
    subquery_id: int
    chunk_id: str
    citation_id: Optional[int] = None
    title: str
    url: str
    domain: str
    text: str
    similarity_score: float
    source_quality_score: float

class CoverageReport(BaseModel):
    covered_topics: List[str] = []
    missing_topics: List[str] = []
    coverage_score: float = 0.0
    needs_more_research: bool = True

class Contradiction(BaseModel):
    topic: str
    claim_a: str
    source_a: str # URL
    claim_b: str
    source_b: str # URL
    severity: str = "low" # low, medium, high

class ResearchState(BaseModel):
    search_id: int
    original_query: str
    iteration: int = 1
    subqueries: List[ResearchSubquery] = []
    sources: List[ResearchSource] = []
    evidence: List[EvidenceItem] = []
    coverage: Optional[CoverageReport] = None
    contradictions: List[Contradiction] = []
    status: str = "running" # running, completed, failed, timeout
