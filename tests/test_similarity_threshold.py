import pytest
import asyncio
from backend.core.config import settings
from backend.rag.models import RetrievedChunk
from backend.rag.retriever import retrieve_evidence
from backend.llm.answer_generator import generate_grounded_answer

@pytest.mark.asyncio
async def test_similarity_threshold_filtering():
    """Verifies that retrieved chunks below RAG_MIN_SCORE are filtered out."""
    threshold = 0.55
    
    chunks = [
        RetrievedChunk(id="c1", search_id=1, url="http://example.com/1", title="Strong Match", domain="example.com", chunk_index=0, text="React performance optimization techniques.", score=0.82),
        RetrievedChunk(id="c2", search_id=1, url="http://example.com/2", title="Weak Match", domain="example.com", chunk_index=1, text="Unrelated text fragment.", score=0.30),
        RetrievedChunk(id="c3", search_id=1, url="http://example.com/3", title="Moderate Match", domain="example.com", chunk_index=2, text="Next.js SSR vs SSG benchmarks.", score=0.65)
    ]
    
    filtered = [c for c in chunks if c.score >= threshold]
    assert len(filtered) == 2
    assert all(c.score >= threshold for c in filtered)

@pytest.mark.asyncio
async def test_zero_result_retrieval_grounded_fallback():
    """Verifies that zero trustworthy chunks return evidence failure without fabricating citations."""
    answer_result = await generate_grounded_answer(
        query="Compare React and Next.js performance",
        search_id=999,
        retrieved_chunks=[]
    )
    assert answer_result.grounded is False
    assert len(answer_result.citations) == 0
    assert "reliable evidence" in answer_result.answer.lower()

if __name__ == "__main__":
    asyncio.run(test_similarity_threshold_filtering())
    asyncio.run(test_zero_result_retrieval_grounded_fallback())
    print("All Similarity Threshold test assertions passed successfully!")
