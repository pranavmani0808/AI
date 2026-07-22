from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import asyncio
import time
from datetime import datetime
from typing import List, Optional
from backend.rag.retriever import retrieve_evidence
from backend.llm.models import GeneratedAnswer, Citation
from backend.llm.context_builder import build_grounding_context
from backend.llm.answer_generator import generate_grounded_answer
from backend.llm.gemini import GeminiProvider
from backend.llm.prompts import SYSTEM_INSTRUCTION
from backend.llm.citation_validator import validate_and_repair_citations
from backend.database.postgres import AsyncSessionLocal
from backend.database.models import GeneratedAnswerModel
from backend.core.config import settings

router = APIRouter(prefix="/answer", tags=["Answer"])

class AnswerRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=settings.MAX_QUERY_LENGTH)
    search_id: int

async def save_answer_to_db(search_id: int, query: str, answer: str, grounded: bool, duration_ms: int):
    """Helper to persist generated answers in PostgreSQL."""
    async with AsyncSessionLocal() as session:
        try:
            db_answer = GeneratedAnswerModel(
                search_id=search_id,
                query=query,
                answer=answer,
                provider="gemini",
                model=settings.GEMINI_MODEL,
                generation_time_ms=duration_ms,
                grounded=grounded,
                created_at=datetime.utcnow()
            )
            session.add(db_answer)
            await session.commit()
        except Exception as e:
            print(f"Failed to save generated answer to database: {e}")

@router.post("/generate", response_model=GeneratedAnswer)
async def generate_sync_answer(request: AnswerRequest):
    """
    Synchronous grounded answer generation API:
    Retrieves semantic context from Qdrant, runs quality filters, builds grounding prompts,
    queries Google Gemini, validates citation markers, and stores metadata in PostgreSQL.
    """
    try:
        start_time = time.time()
        # 1. Retrieve similar chunks from vector store
        chunks = await retrieve_evidence(request.query, request.search_id, top_k=settings.RAG_TOP_K)
        
        # 2. Invoke generator workflow
        provider = GeminiProvider()
        answer_result = await generate_grounded_answer(
            query=request.query,
            search_id=request.search_id,
            retrieved_chunks=chunks,
            provider=provider
        )
        
        # 3. Save to database
        duration_ms = int((time.time() - start_time) * 1000)
        await save_answer_to_db(
            search_id=request.search_id,
            query=request.query,
            answer=answer_result.answer,
            grounded=answer_result.grounded,
            duration_ms=duration_ms
        )
        
        return answer_result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(e)}"
        )

@router.post("/stream")
async def generate_streaming_answer(request_body: AnswerRequest, client_request: Request):
    """
    Real-time Server-Sent Events (SSE) streaming API:
    - Yields status updates, raw text tokens, citations mapping, and completion metadata.
    - Employs active client disconnection monitoring to terminate LLM generation early.
    """
    async def sse_generator():
        start_time = time.time()
        provider = GeminiProvider()
        query = request_body.query
        search_id = request_body.search_id
        
        # Helper to format SSE events
        def make_sse_event(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        try:
            # Stage 1: Retrieve evidence
            if await client_request.is_disconnected():
                return
            yield make_sse_event("status", {"stage": "retrieving", "message": "Retrieving semantic vectors..."})
            chunks = await retrieve_evidence(query, search_id, top_k=settings.RAG_TOP_K)
            
            # Stage 2: Filter and Build Context
            context_str, evidences = build_grounding_context(chunks)
            
            # Fallback if no relevant evidence is found
            if not evidences:
                fallback_msg = "I couldn't find enough reliable evidence in the retrieved sources to answer this confidently."
                yield make_sse_event("token", {"text": fallback_msg})
                yield make_sse_event("status", {"stage": "completed"})
                
                done_payload = {
                    "query": query,
                    "search_id": search_id,
                    "answer": fallback_msg,
                    "citations": [],
                    "grounded": False,
                    "model": settings.GEMINI_MODEL,
                    "generation_time_ms": int((time.time() - start_time) * 1000)
                }
                yield make_sse_event("done", done_payload)
                await save_answer_to_db(search_id, query, fallback_msg, False, done_payload["generation_time_ms"])
                return

            # Stage 3: LLM generation started
            if await client_request.is_disconnected():
                return
            yield make_sse_event("status", {"stage": "generating", "message": "Synthesizing answer..."})
            
            prompt = (
                f"User Search Query: {query}\n\n"
                f"Reference Evidence Chunks:\n{context_str}\n\n"
                f"Answer:"
            )
            
            tokens_collected = []
            try:
                # Retrieve async iterator from Gemini provider stream
                stream_generator = provider.stream(SYSTEM_INSTRUCTION, prompt)
                
                async for token in stream_generator:
                    if await client_request.is_disconnected():
                        print("Client disconnected. Aborting streaming generation.")
                        return
                    tokens_collected.append(token)
                    yield make_sse_event("token", {"text": token})
            except Exception as e:
                print(f"Streaming token generation crashed: {e}")
                err_msg = "\n\nAn internal error occurred during answer generation."
                yield make_sse_event("token", {"text": err_msg})
                yield make_sse_event("status", {"stage": "failed"})
                return

            # Stage 4: Citation Validation and Repairs
            full_answer = "".join(tokens_collected).strip()
            yield make_sse_event("status", {"stage": "verifying", "message": "Validating inline citation references..."})
            
            validated_text, citations, grounded = await validate_and_repair_citations(
                full_answer, 
                evidences, 
                provider
            )
            
            # Fetch crawl pages to map URLs to correct source IDs (e.g. src_1, src_2)
            from sqlalchemy import select
            from backend.database.models import CrawlResult
            
            async with AsyncSessionLocal() as session:
                stmt = select(CrawlResult).where(CrawlResult.search_id == search_id).order_by(CrawlResult.id)
                result = await session.execute(stmt)
                pages = result.scalars().all()
                
            url_to_source_id = {}
            for idx, p in enumerate(pages):
                url_to_source_id[p.url] = f"src_{idx + 1}"
                
            # Create frontend compatible citations and evidences lists
            frontend_citations = []
            frontend_evidences = []
            
            for c in citations:
                evidence_id = f"ev_{c.id}"
                source_id = url_to_source_id.get(c.url)
                
                # If URL is missing from crawled pages, try domain matching or default to src_1
                if not source_id:
                    # Look for domain matching
                    matched_page = next((p for p in pages if c.domain in p.url), None)
                    source_id = f"src_{pages.index(matched_page) + 1}" if matched_page else "src_1"
                
                # Fetch text content and score from matched grounding context chunk
                ev_chunk = next((ev for ev in evidences if ev.chunk_id == c.chunk_id), None)
                score_pct = int(ev_chunk.score * 100) if ev_chunk else 85
                text_content = ev_chunk.text if ev_chunk else ""
                
                frontend_evidences.append({
                    "id": evidence_id,
                    "sourceId": source_id,
                    "content": text_content,
                    "relevanceScore": score_pct
                })
                
                frontend_citations.append({
                    "id": c.id,
                    "sourceId": source_id,
                    "evidenceId": evidence_id
                })
            
            # Send citations metadata list
            yield make_sse_event("citations", {
                "citations": frontend_citations,
                "evidences": frontend_evidences
            })
            
            # If the repair step modified the text, send the final complete verified answer text
            if validated_text != full_answer:
                yield make_sse_event("repaired_text", {"text": validated_text})
                
            yield make_sse_event("status", {"stage": "completed"})
            
            # Final stats
            generation_time = int((time.time() - start_time) * 1000)
            done_payload = {
                "query": query,
                "search_id": search_id,
                "answer": validated_text,
                "citations": frontend_citations,
                "evidences": frontend_evidences,
                "grounded": grounded,
                "model": settings.GEMINI_MODEL,
                "generation_time_ms": generation_time
            }
            yield make_sse_event("done", done_payload)
            
            # Save final results in DB
            await save_answer_to_db(search_id, query, validated_text, grounded, generation_time)
            
        except Exception as e:
            print(f"SSE generator encountered exception: {e}")
            yield make_sse_event("error", {"message": "Internal streaming retrieval generation error occurred."})
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

