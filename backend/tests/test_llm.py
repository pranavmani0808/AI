import pytest
import asyncio
from typing import AsyncGenerator
from backend.rag.models import RetrievedChunk
from backend.llm.models import GroundingEvidence, Citation
from backend.llm.context_builder import build_grounding_context
from backend.llm.citation_validator import validate_and_repair_citations, extract_citation_indices
from backend.llm.provider import LLMProvider

# Define a mock LLM provider to test citation validation and repair logic
class MockLLMProvider(LLMProvider):
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.called_with = []

    async def generate(self, system_instruction: str, prompt: str) -> str:
        self.called_with.append((system_instruction, prompt))
        return self.response_text

    async def stream(self, system_instruction: str, prompt: str) -> AsyncGenerator[str, None]:
        yield self.response_text

def test_context_builder_filtering_and_budgeting():
    # Setup test chunks
    chunks = [
        RetrievedChunk(id="c1", search_id=1, url="http://url1.com", title="Title 1", domain="url1.com", chunk_index=0, text="React is a library.", score=0.8),
        RetrievedChunk(id="c2", search_id=1, url="http://url1.com", title="Title 1", domain="url1.com", chunk_index=1, text="React is a library.", score=0.7), # Duplicate content signature
        RetrievedChunk(id="c3", search_id=1, url="http://url2.com", title="Title 2", domain="url2.com", chunk_index=0, text="Next.js is a framework.", score=0.6),
        RetrievedChunk(id="c4", search_id=1, url="http://url3.com", title="Title 3", domain="url3.com", chunk_index=0, text="Low score chunk.", score=0.2), # Below default score 0.35
    ]
    
    context_str, evidences = build_grounding_context(chunks, min_score=0.35, max_chunks=3, max_chars=18000)
    
    # Assertions
    assert len(evidences) == 2  # c2 is duplicate of c1, c4 is low score
    assert evidences[0].chunk_id == "c1"
    assert evidences[0].citation_id == 1
    assert evidences[1].chunk_id == "c3"
    assert evidences[1].citation_id == 2
    
    assert "<evidence id=\"1\">" in context_str
    assert "Title: Title 1" in context_str
    assert "React is a library." in context_str
    assert "<evidence id=\"2\">" in context_str
    assert "Title: Title 2" in context_str
    assert "Next.js is a framework." in context_str
    assert "Low score chunk." not in context_str

def test_context_builder_max_chunks_limit():
    chunks = [
        RetrievedChunk(id=f"c{i}", search_id=1, url=f"http://url{i}.com", title=f"Title {i}", domain=f"url{i}.com", chunk_index=0, text=f"Text {i}.", score=0.9 - i*0.05)
        for i in range(10)
    ]
    
    # Set limit to 4
    context_str, evidences = build_grounding_context(chunks, min_score=0.3, max_chunks=4)
    assert len(evidences) == 4
    assert evidences[3].citation_id == 4

def test_context_builder_character_budget_limit():
    chunks = [
        RetrievedChunk(id=f"c{i}", search_id=1, url=f"http://url{i}.com", title=f"Title {i}", domain=f"url{i}.com", chunk_index=0, text=f"Text {i} with long description content.", score=0.8)
        for i in range(10)
    ]
    
    # Restrict character count to ~200 chars total
    context_str, evidences = build_grounding_context(chunks, max_chars=250)
    assert len(evidences) < 5
    assert len(context_str) <= 250

def test_extract_citation_indices():
    text = "React is a UI library [1]. Next.js is fullstack [2][3]. Some other statement [9]."
    indices = extract_citation_indices(text)
    assert indices == {1, 2, 3, 9}

@pytest.mark.anyio
async def test_citation_validation_successful_pass():
    evidences = [
        GroundingEvidence(citation_id=1, chunk_id="c1", search_id=1, title="T1", url="http://u1.com", domain="u1.com", text="React is a library.", score=0.8),
        GroundingEvidence(citation_id=2, chunk_id="c2", search_id=1, title="T2", url="http://u2.com", domain="u2.com", text="Next.js is a framework.", score=0.7)
    ]
    
    draft_answer = "React is a library [1]. Next.js builds on top of it [2]."
    mock_provider = MockLLMProvider("Repaired Text")
    
    text, citations, grounded = await validate_and_repair_citations(draft_answer, evidences, mock_provider)
    
    assert text == draft_answer
    assert len(citations) == 2
    assert citations[0].id == 1
    assert citations[0].url == "http://u1.com"
    assert citations[1].id == 2
    assert citations[1].url == "http://u2.com"
    assert grounded is True
    assert len(mock_provider.called_with) == 0  # No repair pass called

@pytest.mark.anyio
async def test_citation_validation_repair_successful():
    evidences = [
        GroundingEvidence(citation_id=1, chunk_id="c1", search_id=1, title="T1", url="http://u1.com", domain="u1.com", text="React is a library.", score=0.8),
        GroundingEvidence(citation_id=2, chunk_id="c2", search_id=1, title="T2", url="http://u2.com", domain="u2.com", text="Next.js is a framework.", score=0.7)
    ]
    
    # [7] is invalid (out of bounds)
    draft_answer = "React is a library [1]. Next.js builds on top of it [7]."
    repaired_draft = "React is a library [1]. Next.js builds on top of it [2]."
    mock_provider = MockLLMProvider(repaired_draft)
    
    text, citations, grounded = await validate_and_repair_citations(draft_answer, evidences, mock_provider)
    
    assert text == repaired_draft
    assert len(citations) == 2
    assert citations[0].id == 1
    assert citations[1].id == 2
    assert grounded is True
    assert len(mock_provider.called_with) == 1  # 1 Repair pass triggered

@pytest.mark.anyio
async def test_citation_validation_repair_failure_fallback():
    evidences = [
        GroundingEvidence(citation_id=1, chunk_id="c1", search_id=1, title="T1", url="http://u1.com", domain="u1.com", text="React is a library.", score=0.8)
    ]
    
    # [9] is invalid, and the model returns another invalid index [8] on repair
    draft_answer = "React is a library [1]. Something else [9]."
    repaired_draft = "React is a library [1]. Something else [8]."
    mock_provider = MockLLMProvider(repaired_draft)
    
    text, citations, grounded = await validate_and_repair_citations(draft_answer, evidences, mock_provider)
    
    # Should fallback to safety text and empty citations list
    assert "I couldn't find enough reliable evidence" in text
    assert len(citations) == 0
    assert grounded is False
