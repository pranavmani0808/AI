from pydantic import BaseModel, Field
from typing import List, Optional

class GroundingEvidence(BaseModel):
    citation_id: int = Field(..., description="1-indexed sequence identifier within context prompt")
    chunk_id: str = Field(..., description="Origin chunk UUID string")
    search_id: int = Field(..., description="Parent search session identifier")
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Origin URL link")
    domain: str = Field(..., description="Source domain name")
    text: str = Field(..., description="Context passage string")
    score: float = Field(..., description="Vector search score")

class GenerationRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User search query")
    search_id: int = Field(..., description="Session identifier")
    evidences: List[GroundingEvidence] = Field(default=[], description="Clean grounding evidence array")

class Citation(BaseModel):
    id: int = Field(..., description="The user facing citation ID (e.g. 1)")
    title: str = Field(..., description="The page title")
    url: str = Field(..., description="The verified link")
    domain: str = Field(..., description="Domain address")
    chunk_id: str = Field(..., description="Chunk UUID reference")

class GeneratedAnswer(BaseModel):
    query: str = Field(..., description="User search query")
    search_id: int = Field(..., description="Session identifier")
    answer: str = Field(..., description="Grounded response text")
    citations: List[Citation] = Field(default=[], description="Valid list of visual citations mapping URL details")
    grounded: bool = Field(..., description="True if LLM response is fully grounded in context facts")
    model: str = Field(..., description="Name of LLM model variant used")
    generation_time_ms: int = Field(..., description="Time taken to run query generation")
