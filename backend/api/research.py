import json
import time
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from backend.core.config import settings
from backend.database.postgres import AsyncSessionLocal
from backend.database.models import CrawlResult, RequestMetricsModel
from backend.llm.gemini import GeminiProvider
from backend.intelligence.research_loop import AutonomousResearchLoop
from backend.observability import start_metrics_tracking, track_stage_duration
from backend.core.rate_limit import check_rate_limit

router = APIRouter(prefix="/research", tags=["Research"])

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=settings.MAX_QUERY_LENGTH)
    max_iterations: Optional[int] = None
    max_subqueries: Optional[int] = None
    max_sources: Optional[int] = None
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    source_preference: Optional[str] = "balanced"
    date_preference: Optional[str] = "any_time"
    chat_history: Optional[List[Dict[str, Any]]] = None

class ResearchResponseModel(BaseModel):
    research_id: int
    query: str
    iterations: int
    subqueries: int
    sources_analyzed: int
    coverage_score: float
    contradictions: List[Dict[str, Any]]
    answer: str
    citations: List[Dict[str, Any]]
    evidences: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    research_metadata: Dict[str, Any]

from backend.intelligence.query_router import QueryRouter, QueryIntent
from backend.llm.prompts import CONVERSATIONAL_SYSTEM_INSTRUCTION, GENERAL_KNOWLEDGE_SYSTEM_INSTRUCTION

@router.post("/autonomous", response_model=ResearchResponseModel, dependencies=[Depends(check_rate_limit)])
async def perform_autonomous_research(request_body: ResearchRequest, request: Request):
    """
    Executes synchronous autonomous multi-step research or fast-path conversational query.
    """
    request_id = getattr(request.state, "request_id", "req_none")
    metrics_tracker = start_metrics_tracking(request_body.query, request_id)
    
    router_engine = QueryRouter()
    routing = await router_engine.route_query(request_body.query, selected_mode="research")

    if not routing["retrieval_used"]:
        provider = GeminiProvider()
        system_prompt = (
            CONVERSATIONAL_SYSTEM_INSTRUCTION 
            if routing["intent"] == QueryIntent.CONVERSATIONAL.value 
            else GENERAL_KNOWLEDGE_SYSTEM_INSTRUCTION
        )
        try:
            answer_text = await provider.generate(system_prompt, f"User Query: {request_body.query}")
        except Exception as e:
            print(f"Gemini LLM call failed for conversational query: {e}")
            if routing["intent"] == QueryIntent.CONVERSATIONAL.value:
                answer_text = "Hi! How can I help you today?"
            else:
                answer_text = "I'm IntelliSearch, your AI research assistant. How can I help you today?"

        return ResearchResponseModel(
            research_id=0,
            query=request_body.query,
            iterations=0,
            subqueries=0,
            sources_analyzed=0,
            coverage_score=1.0,
            contradictions=[],
            answer=answer_text.strip(),
            citations=[],
            evidences=[],
            sources=[],
            research_metadata={
                "total_ms": 100,
                "intent": routing["intent"],
                "retrieval_used": False,
                "stop_reason": "Conversational Intent"
            }
        )

    query_to_run = request_body.query
    reformulation_meta = {"original_query": request_body.query, "standalone_query": request_body.query, "reformulated": False}
    if request_body.chat_history and len(request_body.chat_history) > 0:
        reformulator = QueryReformulator()
        reformulation_meta = await reformulator.reformulate(request_body.query, request_body.chat_history)
        query_to_run = reformulation_meta["standalone_query"]

    state = None
    final_answer = None
    metrics = None
    
    try:
        loop = AutonomousResearchLoop()
        with track_stage_duration("total_ms"):
            state, final_answer, metrics = await loop.execute_research(
                query=query_to_run,
                max_iterations=request_body.max_iterations,
                max_subqueries=request_body.max_subqueries,
                max_sources=request_body.max_sources,
                include_domains=request_body.include_domains,
                exclude_domains=request_body.exclude_domains,
                source_preference=request_body.source_preference,
                date_preference=request_body.date_preference
            )
        
        # Fetch crawl pages to map URLs to correct source IDs (e.g. src_1, src_2)
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            stmt = select(CrawlResult).where(CrawlResult.search_id == state.search_id).order_by(CrawlResult.id)
            result = await session.execute(stmt)
            pages = result.scalars().all()
            
        # STEP 6: Filter out failed scrapes before presentation
        valid_pages = [p for p in pages if p.crawl_status == "SUCCESS" and p.word_count >= 30]
        url_to_source_id = {p.url: f"src_{idx + 1}" for idx, p in enumerate(valid_pages)}
        
        # Build citations and evidences list mapped to src_N
        frontend_citations = []
        frontend_evidences = []
        for c in final_answer.citations:
            evidence_id = f"ev_{c.id}"
            source_id = url_to_source_id.get(c.url, "src_1")
            
            # Fetch text content from state evidence
            ev_item = next((ev for ev in state.evidence if ev.chunk_id == c.chunk_id), None)
            score_pct = int(ev_item.similarity_score * 100) if ev_item else 85
            text_content = ev_item.text if ev_item else ""
            
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
            
        # Format contradictions list
        contradictions_list = []
        for contra in state.contradictions:
            contradictions_list.append({
                "topic": contra.topic,
                "claim_a": contra.claim_a,
                "source_a_url": contra.source_a,
                "claim_b": contra.claim_b,
                "source_b_url": contra.source_b,
                "resolution": contra.resolution
            })
            
        # Format valid sources list
        sources_list = []
        for idx, p in enumerate(valid_pages):
            sources_list.append({
                "id": f"src_{idx + 1}",
                "title": p.title or "Discovered Source",
                "url": p.url,
                "domain": p.url.split("//")[-1].split("/")[0],
                "excerpt": (p.extracted_text[:200] + "...") if p.extracted_text else ""
            })
            
        research_metadata = metrics or {}
        research_metadata["intent"] = routing["intent"]
        research_metadata["retrieval_used"] = True
        
        return ResearchResponseModel(
            research_id=state.search_id or 1,
            query=request_body.query,
            iterations=state.current_iteration,
            subqueries=len(state.subqueries_executed),
            sources_analyzed=len(valid_pages),
            coverage_score=state.coverage_score,
            contradictions=contradictions_list,
            answer=final_answer.answer,
            citations=frontend_citations,
            evidences=frontend_evidences,
            sources=sources_list,
            research_metadata=research_metadata
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Autonomous research failed: {str(e)}"
        )

@router.post("/autonomous/stream")
async def perform_autonomous_research_stream(request_body: ResearchRequest, client_request: Request):
    """
    Streams multi-step progress, topic status, evidence discovery, and final response via SSE.
    Includes QueryRouter fast-path for conversational queries.
    """
    router_engine = QueryRouter()
    routing = await router_engine.route_query(request_body.query, selected_mode="research")

    # Fast-path for conversational queries in streaming endpoint
    if not routing["retrieval_used"]:
        async def fast_sse_generator():
            provider = GeminiProvider()
            system_prompt = (
                CONVERSATIONAL_SYSTEM_INSTRUCTION 
                if routing["intent"] == QueryIntent.CONVERSATIONAL.value 
                else GENERAL_KNOWLEDGE_SYSTEM_INSTRUCTION
            )
            
            yield f"event: status\ndata: {json.dumps({'stage': 'conversational', 'message': 'Direct answer response'})}\n\n"
            
            try:
                answer_text = await provider.generate(system_prompt, f"User Query: {request_body.query}")
            except Exception as e:
                print(f"Gemini LLM streaming call failed for conversational query: {e}")
                if routing["intent"] == QueryIntent.CONVERSATIONAL.value:
                    answer_text = "Hi! How can I help you today?"
                else:
                    answer_text = "I'm IntelliSearch, your AI research assistant. How can I help you today?"
            answer_clean = answer_text.strip()
            
            yield f"event: token\ndata: {json.dumps({'text': answer_clean})}\n\n"
            
            done_payload = {
                "research_id": 0,
                "query": request_body.query,
                "intent": routing["intent"],
                "retrieval_used": False,
                "answer": answer_clean,
                "citations": [],
                "evidences": [],
                "sources": [],
                "coverage_score": 1.0,
                "contradictions": [],
                "researchPlan": {"objective": request_body.query, "topics": []},
                "researchCoverage": {"score": 1.0, "missing": [], "covered": []},
                "research_metadata": {
                    "total_ms": 150,
                    "intent": routing["intent"],
                    "retrieval_used": False,
                    "stop_reason": "Conversational Intent"
                }
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

        return StreamingResponse(fast_sse_generator(), media_type="text/event-stream")

    async def sse_generator():
        loop = AutonomousResearchLoop()
        queue = asyncio.Queue()
        
        async def callback(event: str, data: dict):
            await queue.put((event, data))
            
        def make_sse_event(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"
            
        research_task = asyncio.create_task(
            loop.execute_research(
                query=request_body.query,
                status_callback=callback,
                max_iterations=request_body.max_iterations,
                max_subqueries=request_body.max_subqueries,
                max_sources=request_body.max_sources,
                include_domains=request_body.include_domains,
                exclude_domains=request_body.exclude_domains,
                source_preference=request_body.source_preference,
                date_preference=request_body.date_preference
            )
        )
        
        try:
            while not (research_task.done() and queue.empty()):
                if await client_request.is_disconnected():
                    print("Client disconnected. Canceling autonomous research task.")
                    research_task.cancel()
                    break
                    
                try:
                    event, data = await asyncio.wait_for(queue.get(), timeout=0.5)
                    
                    # Intercept done event to format citation source mappings for frontend
                    if event == "done":
                        search_id = data["search_id"]
                        
                        from sqlalchemy import select
                        async with AsyncSessionLocal() as session:
                            stmt = select(CrawlResult).where(CrawlResult.search_id == search_id).order_by(CrawlResult.id)
                            result = await session.execute(stmt)
                            pages = result.scalars().all()
                            
                        # STEP 6: Filter valid pages only
                        valid_pages = [p for p in pages if p.crawl_status == "SUCCESS" and p.word_count >= 30]
                        url_to_source_id = {p.url: f"src_{idx + 1}" for idx, p in enumerate(valid_pages)}
                        
                        # Remap citations and evidences
                        remaped_citations = []
                        remaped_evidences = []
                        
                        for idx, c in enumerate(data["citations"]):
                            evidence_id = f"ev_{c['id']}"
                            # Read original URL/text from the citation details
                            url = c.get("url")
                            if not url:
                                # Fallback lookup
                                continue
                            source_id = url_to_source_id.get(url, "src_1")
                            
                            remaped_evidences.append({
                                "id": evidence_id,
                                "sourceId": source_id,
                                "content": c.get("text", ""),
                                "relevanceScore": int(c.get("score", 0.85) * 100)
                            })
                            
                            remaped_citations.append({
                                "id": c["id"],
                                "sourceId": source_id,
                                "evidenceId": evidence_id
                            })
                            
                        # Format valid sources list
                        sources_list = []
                        for idx, p in enumerate(valid_pages):
                            sources_list.append({
                                "id": f"src_{idx + 1}",
                                "title": p.title or "Discovered Source",
                                "url": p.url,
                                "domain": p.url.split("//")[-1].split("/")[0]
                            })
                            
                        data["intent"] = routing["intent"]
                        data["retrieval_used"] = True
                        data["citations"] = remaped_citations
                        data["evidences"] = remaped_evidences
                        data["sources"] = sources_list
                        
                    yield make_sse_event(event, data)
                except asyncio.TimeoutError:
                    if research_task.done():
                        break
                    # Keep-alive heartbeat ping
                    yield ": ping\n\n"
                    
            # Ensure any background errors in task are surfaced
            if research_task.done() and not research_task.cancelled():
                # This will raise any exceptions thrown inside the loop
                await research_task
                
        except Exception as e:
            print(f"Autonomous research streaming crashed: {e}")
            yield make_sse_event("error", {"message": "Streaming research loop error occurred."})
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@router.get("/metrics/summary")
async def get_metrics_summary():
    """
    Returns aggregate operational statistics.
    Excludes sensitive infrastructure info.
    """
    from sqlalchemy import select, func
    async with AsyncSessionLocal() as session:
        try:
            total_stmt = select(func.count(RequestMetricsModel.id))
            success_stmt = select(func.count(RequestMetricsModel.id)).where(RequestMetricsModel.status == "success")
            fail_stmt = select(func.count(RequestMetricsModel.id)).where(RequestMetricsModel.status == "failed")
            
            total_res = await session.execute(total_stmt)
            total_count = total_res.scalar() or 0
            
            success_res = await session.execute(success_stmt)
            success_count = success_res.scalar() or 0
            
            fail_res = await session.execute(fail_stmt)
            fail_count = fail_res.scalar() or 0
            
            avg_stmt = select(
                func.avg(RequestMetricsModel.total_duration_ms),
                func.avg(RequestMetricsModel.sources_analyzed),
                func.avg(RequestMetricsModel.coverage_score)
            ).where(RequestMetricsModel.status == "success")
            
            avg_res = await session.execute(avg_stmt)
            avg_row = avg_res.fetchone()
            
            avg_response_ms = int(avg_row[0]) if avg_row and avg_row[0] is not None else 0
            avg_sources = round(float(avg_row[1]), 1) if avg_row and avg_row[1] is not None else 0.0
            avg_coverage = round(float(avg_row[2]), 2) if avg_row and avg_row[2] is not None else 0.0
            
            return {
                "total_searches": total_count,
                "successful_searches": success_count,
                "failed_searches": fail_count,
                "average_response_ms": avg_response_ms,
                "average_sources": avg_sources,
                "average_coverage": avg_coverage
            }
        except Exception as e:
            print(f"Failed to query metrics summary: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve metrics analytics."
            )

@router.get("/{research_id}/debug")
async def get_research_debug_details(research_id: int):
    """
    Returns diagnostic details for a specific research session.
    Protected or disabled in production modes.
    """
    if settings.APP_ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Diagnostics endpoint disabled in production mode."
        )
        
    from sqlalchemy import select
    from backend.database.models import ResearchSessionModel, ResearchSubqueryModel, ResearchSourceModel, ResearchContradictionModel
    
    async with AsyncSessionLocal() as session:
        sess_db = await session.get(ResearchSessionModel, research_id)
        if not sess_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research session {research_id} not found."
            )
            
        sub_stmt = select(ResearchSubqueryModel).where(ResearchSubqueryModel.research_id == research_id)
        sub_res = await session.execute(sub_stmt)
        subqueries = sub_res.scalars().all()
        
        src_stmt = select(ResearchSourceModel).where(ResearchSourceModel.research_id == research_id)
        src_res = await session.execute(src_stmt)
        sources = src_res.scalars().all()
        
        contra_stmt = select(ResearchContradictionModel).where(ResearchContradictionModel.research_id == research_id)
        contra_res = await session.execute(contra_stmt)
        contradictions = contra_res.scalars().all()
        
        metric_stmt = select(RequestMetricsModel).where(RequestMetricsModel.research_id == research_id)
        metric_res = await session.execute(metric_stmt)
        metrics_db = metric_res.scalars().first()
        
        timings = {}
        if metrics_db:
            timings = {
                "total_ms": metrics_db.total_duration_ms,
                "search_ms": metrics_db.search_duration_ms,
                "crawl_ms": metrics_db.crawl_duration_ms,
                "rag_ms": metrics_db.rag_duration_ms,
                "generation_ms": metrics_db.generation_duration_ms
            }
            
        return {
            "research_id": research_id,
            "query": sess_db.query,
            "status": sess_db.status,
            "iterations": sess_db.iterations,
            "coverage_score": sess_db.coverage_score,
            "sources_analyzed": sess_db.sources_analyzed,
            "started_at": sess_db.started_at,
            "completed_at": sess_db.completed_at,
            "timings": timings,
            "subqueries": [
                {
                    "query": s.query,
                    "purpose": s.purpose,
                    "status": s.status,
                    "iteration": s.iteration
                }
                for s in subqueries
            ],
            "sources": [
                {
                    "url": src.url,
                    "domain": src.domain,
                    "overall_score": src.overall_score
                }
                for src in sources
            ],
            "contradictions_detected": len(contradictions)
        }

@router.get("/history")
async def get_research_history(q: Optional[str] = None):
    """
    Returns recent research sessions.
    Supports filtering by query search term.
    """
    from sqlalchemy import select, desc
    from backend.database.models import ResearchSessionModel
    
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(ResearchSessionModel)
            if q:
                stmt = stmt.where(ResearchSessionModel.query.ilike(f"%{q}%"))
            stmt = stmt.order_by(desc(ResearchSessionModel.started_at)).limit(30)
            
            res = await session.execute(stmt)
            sessions = res.scalars().all()
            
            return [
                {
                    "research_id": s.id,
                    "query": s.query,
                    "status": s.status,
                    "iterations": s.iterations,
                    "coverage_score": s.coverage_score,
                    "sources_analyzed": s.sources_analyzed,
                    "started_at": s.started_at,
                    "completed_at": s.completed_at
                }
                for s in sessions
            ]
        except Exception as e:
            print(f"Failed to fetch research history: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve history."
            )

@router.get("/{research_id}", response_model=ResearchResponseModel)
async def get_research_session_details(research_id: int):
    """
    Retrieves full details of a past research session for client rendering.
    Includes sources, citations, evidence, and answer details.
    """
    from sqlalchemy import select
    from backend.database.models import ResearchSessionModel, GeneratedAnswerModel, CrawlResult, ResearchSourceModel, ResearchContradictionModel
    
    async with AsyncSessionLocal() as session:
        sess_db = await session.get(ResearchSessionModel, research_id)
        if not sess_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research session {research_id} not found."
            )
            
        ans_stmt = select(GeneratedAnswerModel).where(GeneratedAnswerModel.search_id == research_id)
        ans_res = await session.execute(ans_stmt)
        answer_db = ans_res.scalars().first()
        
        crawl_stmt = select(CrawlResult).where(CrawlResult.search_id == research_id).order_by(CrawlResult.id)
        crawl_res = await session.execute(crawl_stmt)
        pages = crawl_res.scalars().all()
        
        url_to_source_id = {p.url: f"src_{idx + 1}" for idx, p in enumerate(pages)}
        
        sources_list = []
        for idx, p in enumerate(pages):
            sources_list.append({
                "id": f"src_{idx + 1}",
                "title": p.title or "Discovered Source",
                "url": p.url,
                "domain": p.url.split("//")[-1].split("/")[0]
            })
            
        frontend_citations = []
        frontend_evidences = []
        answer_text = ""
        
        if answer_db:
            answer_text = answer_db.answer
            import re
            citations_found = re.findall(r'\[(\d+)\]', answer_text)
            unique_cits = sorted(list(set(int(c) for c in citations_found)))
            
            for cit_idx in unique_cits:
                evidence_id = f"ev_{cit_idx}"
                mapped_p = pages[cit_idx - 1] if cit_idx <= len(pages) else None
                if mapped_p:
                    source_id = url_to_source_id.get(mapped_p.url, "src_1")
                    frontend_evidences.append({
                        "id": evidence_id,
                        "sourceId": source_id,
                        "content": mapped_p.extracted_text[:300] if mapped_p.extracted_text else "Crawled segment summary",
                        "relevanceScore": 90
                    })
                    frontend_citations.append({
                        "id": cit_idx,
                        "sourceId": source_id,
                        "evidenceId": evidence_id
                    })
                    
        contra_stmt = select(ResearchContradictionModel).where(ResearchContradictionModel.research_id == research_id)
        contra_res = await session.execute(contra_stmt)
        contradictions = contra_res.scalars().all()
        
        contradictions_list = [
            {
                "topic": c.topic,
                "claim_a": c.claim_a,
                "source_a_url": c.source_a_url,
                "claim_b": c.claim_b,
                "source_b_url": c.source_b_url,
                "severity": c.severity
            }
            for c in contradictions
        ]
        
        return ResearchResponseModel(
            research_id=research_id,
            query=sess_db.query,
            iterations=sess_db.iterations,
            subqueries=0,
            sources_analyzed=sess_db.sources_analyzed,
            coverage_score=sess_db.coverage_score,
            contradictions=contradictions_list,
            answer=answer_text,
            citations=frontend_citations,
            evidences=frontend_evidences,
            sources=sources_list,
            research_metadata={"status": sess_db.status}
        )
