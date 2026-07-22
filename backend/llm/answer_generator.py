import time
from typing import List, Tuple, Optional
from datetime import datetime
from backend.rag.models import RetrievedChunk
from backend.llm.models import GeneratedAnswer, GroundingEvidence
from backend.llm.context_builder import build_grounding_context
from backend.llm.prompts import SYSTEM_INSTRUCTION
from backend.llm.gemini import GeminiProvider
from backend.llm.citation_validator import validate_and_repair_citations
from backend.core.config import settings

async def generate_grounded_answer(
    query: str,
    search_id: int,
    retrieved_chunks: List[RetrievedChunk],
    provider: GeminiProvider = None
) -> GeneratedAnswer:
    """
    Coordinates context building, prompt assembly, Gemini generation,
    and post-generation citation validation checks.
    """
    start_time = time.time()
    
    if provider is None:
        provider = GeminiProvider()
        
    # 1. Build Grounding Context
    context_str, evidences = build_grounding_context(retrieved_chunks)
    
    # 2. Fallback if no relevant evidence is found
    if not evidences:
        generation_time = int((time.time() - start_time) * 1000)
        fallback_msg = "I couldn't find enough reliable evidence in the retrieved sources to answer this confidently."
        return GeneratedAnswer(
            query=query,
            search_id=search_id,
            answer=fallback_msg,
            citations=[],
            grounded=False,
            model=settings.GEMINI_MODEL,
            generation_time_ms=generation_time
        )
        
    # 3. Assemble Prompt & Invoke LLM API
    prompt = (
        f"User Search Query: {query}\n\n"
        f"Reference Evidence Chunks:\n{context_str}\n\n"
        f"Answer:"
    )
    
    try:
        raw_answer = await provider.generate(SYSTEM_INSTRUCTION, prompt)
        raw_answer = raw_answer.strip()
        
        # 4. Validate and Repair Citations
        validated_text, citations, grounded = await validate_and_repair_citations(
            raw_answer, 
            evidences, 
            provider
        )
        
    except Exception as e:
        print(f"Grounded answer generation failed: {e}. Synthesizing fallback summary from top retrieved evidence.")
        summary_parts = []
        citations = []
        for idx, ev in enumerate(evidences[:4], start=1):
            clean_text = ev.text.strip().replace("\n", " ")
            if len(clean_text) > 180:
                clean_text = clean_text[:180] + "..."
            summary_parts.append(f"{clean_text} [{idx}]")
            citations.append(GroundingEvidence(
                id=idx, 
                chunk_id=ev.chunk_id, 
                url=ev.url, 
                title=ev.title, 
                text=ev.text, 
                similarity_score=ev.similarity_score
            ))
        
        validated_text = "Based on retrieved sources: " + " ".join(summary_parts)
        grounded = True
        
    generation_time = int((time.time() - start_time) * 1000)
    
    return GeneratedAnswer(
        query=query,
        search_id=search_id,
        answer=validated_text,
        citations=citations,
        grounded=grounded,
        model=settings.GEMINI_MODEL,
        generation_time_ms=generation_time
    )
