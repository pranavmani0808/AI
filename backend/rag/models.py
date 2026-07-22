from pydantic import BaseModel, Field
from typing import List, Optional

class DocumentChunk(BaseModel):
    id: str = Field(..., description="Deterministic UUID identifier for the chunk")
    search_id: int = Field(..., description="Active search session parent identifier")
    subquery_id: Optional[int] = Field(default=None, description="Active subquery identifier")
    url: str = Field(..., description="URL source origin of the chunk")
    title: str = Field(..., description="Title of the source webpage")
    domain: str = Field(..., description="Domain address of the source")
    chunk_index: int = Field(..., description="Index sequence number of the chunk in the document")
    text: str = Field(..., description="Clean plain text snippet content")
    word_count: int = Field(..., description="Total words in the snippet")

class RetrievedChunk(BaseModel):
    id: str = Field(..., description="Unique chunk identifier")
    search_id: int = Field(..., description="Parent search session identifier")
    subquery_id: Optional[int] = Field(default=None, description="Parent subquery identifier")
    url: str = Field(..., description="Source URL link")
    title: str = Field(..., description="Title of the source webpage")
    domain: str = Field(..., description="Domain address of the source")
    chunk_index: int = Field(..., description="Index of the chunk in the document")
    text: str = Field(..., description="Scraped chunk text content")
    score: float = Field(..., description="Similarity confidence relevance score (0.0 - 1.0)")

class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The search term to run retrieval against")
    search_id: int = Field(..., description="Filter criteria to enforce session isolation")
    top_k: int = Field(default=8, ge=1, le=20, description="Max matching passages to retrieve")

class RetrievalResponse(BaseModel):
    query: str = Field(..., description="The query processed")
    search_id: int = Field(..., description="The session identifier filtered")
    total: int = Field(..., description="Total evidence items returned")
    results: List[RetrievedChunk] = Field(default=[], description="Semantically matching context chunks")
