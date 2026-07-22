import asyncio
import time
from datetime import datetime
from typing import List, Dict, Set, Any, Callable, Optional, Tuple
from urllib.parse import urlparse

from backend.core.config import settings
from backend.database.postgres import AsyncSessionLocal
from backend.database.models import SearchQuery, CrawlResult, GeneratedAnswerModel, ResearchSessionModel, ResearchSubqueryModel, ResearchSourceModel, ResearchContradictionModel
from backend.database.redis import get_cached_search, set_cached_search, get_cached_page, set_cached_page
from backend.crawler.crawler import crawl_urls_concurrently
from backend.crawler.models import CrawledDocument
from backend.search.models import SearchResult
from backend.services.searxng import search_searxng
from backend.search.deduplicator import deduplicate_results
from backend.search.ranker import rank_search_results
from backend.rag.pipeline import run_indexing_pipeline, run_retrieval_pipeline
from backend.rag.models import RetrievedChunk
from backend.llm.models import GeneratedAnswer
from backend.observability import track_stage_duration

from backend.intelligence.models import ResearchState, ResearchPlan, ResearchSubquery, ResearchSource, EvidenceItem, CoverageReport, Contradiction
from backend.intelligence.planner import ResearchPlanner
from backend.intelligence.query_decomposer import ResearchQueryDecomposer
from backend.intelligence.source_scorer import SourceScorer
from backend.intelligence.evidence_manager import EvidenceManager
from backend.intelligence.coverage_analyzer import CoverageAnalyzer
from backend.intelligence.contradiction_detector import ContradictionDetector
from backend.intelligence.synthesis import ResearchSynthesizer

def domain_in_url(url: str, domain: str) -> bool:
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    domain = domain.lower().strip()
    return netloc == domain or netloc.endswith("." + domain)

class AutonomousResearchLoop:
    """
    Coordinates the iterative research-scrape-embed-evaluate-synthesis loop
    enforcing hard safety resource budgets, timeout controls, and gap detection.
    """
    def __init__(self, provider: Any = None):
        self.planner = ResearchPlanner(provider)
        self.decomposer = ResearchQueryDecomposer(provider)
        self.scorer = SourceScorer()
        self.evidence_manager = EvidenceManager()
        self.coverage_analyzer = CoverageAnalyzer(provider)
        self.contradiction_detector = ContradictionDetector(provider)
        self.synthesizer = ResearchSynthesizer(provider)
        self.semaphore = asyncio.Semaphore(settings.RESEARCH_MAX_PARALLEL_SEARCHES)

    async def execute_research(
        self,
        query: str,
        status_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        max_iterations: Optional[int] = None,
        max_subqueries: Optional[int] = None,
        max_sources: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        source_preference: Optional[str] = "balanced",
        date_preference: Optional[str] = "any_time"
    ) -> Tuple[ResearchState, GeneratedAnswer, Dict[str, Any]]:
        start_time = time.time()
        
        # Enforce budget configurations fallbacks
        max_iterations = max_iterations or settings.RESEARCH_MAX_ITERATIONS
        max_subqueries = max_subqueries or settings.RESEARCH_MAX_SUBQUERIES
        max_sources = max_sources or settings.RESEARCH_MAX_SOURCES
        
        # Budget tracking statistics
        metrics = {
            "pages_crawled": 0,
            "chunks_indexed": 0,
            "llm_calls": 0,
            "search_requests": 0,
            "skipped_duplicate_queries": 0,
            "failed_crawls": 0
        }
        
        # --- 1. SESSION INITIALIZATION ---
        search_id = None
        async with AsyncSessionLocal() as session:
            try:
                db_query = SearchQuery(
                    query=query,
                    result_count=0,
                    duration_ms=0,
                    created_at=datetime.utcnow()
                )
                session.add(db_query)
                await session.commit()
                await session.refresh(db_query)
                search_id = db_query.id
                
                db_session = ResearchSessionModel(
                    id=search_id,
                    query=query,
                    status="running",
                    iterations=0,
                    coverage_score=0.0,
                    sources_analyzed=0,
                    started_at=datetime.utcnow()
                )
                session.add(db_session)
                await session.commit()
            except Exception as db_err:
                print(f"Failed to save initial research session to Postgres: {db_err}")
                if search_id is None:
                    search_id = int(time.time()) # Local fallback if Postgres is down
                    
        if status_callback:
            await status_callback("research_started", {"search_id": search_id, "query": query})
            
        # --- 2. PLAN & INITIAL DECOMPOSITION ---
        if status_callback:
            await status_callback("status", {"stage": "planning", "message": "Analyzing question & planning objectives..."})
            
        with track_stage_duration("planning_ms"):
            plan_output = await self.planner.plan(query)
            metrics["llm_calls"] += 1
            
            if status_callback:
                await status_callback("plan", {"objective": plan_output.objective, "topics": plan_output.topics})
                
            initial_subqueries = await self.decomposer.decompose(query, plan_output.objective, plan_output.topics, set())
            initial_subqueries = initial_subqueries[:max_subqueries]
            metrics["llm_calls"] += 1
        
        # Save subqueries to Postgres
        async with AsyncSessionLocal() as session:
            try:
                for subq in initial_subqueries:
                    db_sub = ResearchSubqueryModel(
                        research_id=search_id,
                        query=subq.query,
                        purpose=subq.purpose,
                        priority=subq.priority,
                        status="pending",
                        iteration=1
                    )
                    session.add(db_sub)
                await session.commit()
            except Exception as db_err:
                print(f"Failed to save subqueries: {db_err}")

        # Initialize Loop State
        state = ResearchState(
            search_id=search_id,
            original_query=query,
            iteration=1,
            subqueries=initial_subqueries,
            sources=[],
            evidence=[],
            coverage=None,
            contradictions=[],
            status="running"
        )
        
        crawled_urls: Set[str] = set()
        domain_counts: Dict[str, int] = {}
        executed_queries: Set[str] = set()
        
        # --- 3. AUTONOMOUS RESEARCH LOOP ---
        stop_reason = "max_iterations_reached"
        
        # FIX: Initialize aggregated evidence accumulators OUTSIDE the loop so
        # evidence from ALL iterations is preserved, not just the last one.
        aggregated_chunks: List[RetrievedChunk] = []
        seen_chunk_ids: Set[str] = set()

        while state.iteration <= max_iterations:
            # Check resource budget timeouts
            elapsed = time.time() - start_time
            if elapsed >= settings.RESEARCH_TIMEOUT_SECONDS:
                stop_reason = "time_budget_reached"
                state.status = "timeout"
                break
                
            iteration_queries = [sub for sub in state.subqueries if sub.status == "pending"]
            if not iteration_queries:
                stop_reason = "no_new_queries_generated"
                break
                
            if status_callback:
                await status_callback("status", {
                    "stage": "searching",
                    "message": f"Iteration {state.iteration}: Researching {len(iteration_queries)} target subqueries..."
                })
                
            # Process subqueries concurrently with bounded semaphore limits
            async def run_single_subquery(subq: ResearchSubquery) -> List[SearchResult]:
                async with self.semaphore:
                    subq.status = "running"
                    q_normalized = subq.query.lower().strip()
                    
                    if q_normalized in executed_queries:
                        metrics["skipped_duplicate_queries"] += 1
                        subq.status = "completed"
                        return []
                        
                    executed_queries.add(q_normalized)
                    
                    # Call SearXNG (checking Redis first)
                    cached = await get_cached_search(q_normalized)
                    metrics["search_requests"] += 1
                    
                    if cached:
                        results = [SearchResult(**item) for item in cached]
                    else:
                        try:
                            time_range = None
                            if date_preference == "past_year":
                                time_range = "year"
                            elif date_preference == "past_month":
                                time_range = "month"
                            elif date_preference == "past_week":
                                time_range = "week"
                                
                            raw = await search_searxng(subq.query, limit=15, time_range=time_range)
                            
                            # Filter domains
                            if exclude_domains:
                                raw = [r for r in raw if not any(domain_in_url(r.url, d) for d in exclude_domains)]
                            if include_domains:
                                raw = [r for r in raw if any(domain_in_url(r.url, d) for d in include_domains)]
                                
                            unique = deduplicate_results(raw)
                            results = rank_search_results(unique, subq.query)
                            await set_cached_search(q_normalized, [r.model_dump() for r in results])
                        except Exception as search_err:
                            print(f"SearXNG failed for subquery '{subq.query}': {search_err}")
                            results = []
                            
                    subq.status = "completed"
                    return results
                    
            tasks = [run_single_subquery(sub) for sub in iteration_queries]
            with track_stage_duration("search_ms"):
                search_results_list = await asyncio.gather(*tasks)
            
            # Aggregate discovered URLs and score them
            all_candidates = []
            for results_set in search_results_list:
                for rank_idx, res in enumerate(results_set):
                    scored_source = self.scorer.score_source(res.url, res.title, res.snippet, query, rank_idx + 1, source_preference)
                    # Use SearXNG structure but carry scoring info
                    res_copy = res.model_copy(update={
                        "score": scored_source.overall_score
                    })
                    all_candidates.append((scored_source, res_copy))
                    
            # Sort candidates globally by overall source quality score
            all_candidates.sort(key=lambda x: x[0].overall_score, reverse=True)
            
            # Apply domain diversity cap and global url deduplication
            scored_sources_list = [c[0] for c in all_candidates]
            candidate_results = [c[1] for c in all_candidates]
            
            approved_results = self.evidence_manager.filter_and_deduplicate(
                candidate_results,
                crawled_urls,
                domain_counts
            )
            
            # Restrict crawl candidate list to remaining sources budget
            remaining_sources = max(0, max_sources - len(crawled_urls))
            approved_results = approved_results[:remaining_sources]
            
            # Save approved source metadata records
            async with AsyncSessionLocal() as session:
                try:
                    for src in scored_sources_list:
                        if src.url.strip().lower() in crawled_urls:
                            db_src = ResearchSourceModel(
                                research_id=search_id,
                                url=src.url,
                                domain=src.domain,
                                authority_score=src.authority_score,
                                relevance_score=src.relevance_score,
                                freshness_score=src.freshness_score,
                                overall_score=src.overall_score
                            )
                            session.add(db_src)
                            # Register source in state
                            if src.url not in {s.url for s in state.sources}:
                                state.sources.append(src)
                    await session.commit()
                except Exception as db_err:
                    print(f"Failed to save source scoring entries: {db_err}")
                    
            # Crawl approved URLs
            urls_to_crawl = []
            crawled_documents = []
            
            for res in approved_results:
                cached_page = await get_cached_page(res.url)
                if cached_page:
                    crawled_documents.append(CrawledDocument(**cached_page))
                else:
                    urls_to_crawl.append(res.url)
                    
            if urls_to_crawl:
                if status_callback:
                    await status_callback("status", {
                        "stage": "crawling",
                        "message": f"Crawling {len(urls_to_crawl)} new sources..."
                    })
                with track_stage_duration("crawl_ms"):
                    fresh_docs = await crawl_urls_concurrently(urls_to_crawl, search_id=search_id)
                
                # Check for failed crawls
                for url_attempt in urls_to_crawl:
                    found = any(doc.url == url_attempt and doc.crawl_status == "SUCCESS" for doc in fresh_docs)
                    if not found:
                        metrics["failed_crawls"] += 1
                        
                for doc in fresh_docs:
                    crawled_documents.append(doc)
                    await set_cached_page(doc.url, doc.model_dump())
                    
                    # Save crawl metadata to Postgres
                    async with AsyncSessionLocal() as session:
                        try:
                            db_crawl = CrawlResult(
                                search_id=search_id,
                                url=doc.url,
                                title=doc.title,
                                status_code=doc.status_code,
                                crawl_status=doc.crawl_status,
                                word_count=doc.word_count,
                                extracted_text=doc.text,
                                crawled_at=datetime.utcnow()
                            )
                            session.add(db_crawl)
                            await session.commit()
                        except Exception as db_err:
                            print(f"Failed to save crawl: {db_err}")
                            
            metrics["pages_crawled"] += len(urls_to_crawl)
            
            # Clean, chunk, embed, and index into Qdrant using the RAG pipeline
            if crawled_documents:
                with track_stage_duration("embedding_ms"):
                    indexing_results = await run_indexing_pipeline(crawled_documents, search_id)
                metrics["chunks_indexed"] += indexing_results.get("chunks_indexed", 0)
                
            # --- 4. RETRIEVED CHUNKS AGGREGATION & EVALUATION ---
            if status_callback:
                await status_callback("status", {"stage": "evaluating", "message": "Evaluating evidence coverage..."})
                
            # Retrieve semantically matching evidence from Qdrant for each planned topic.
            # aggregated_chunks/seen_chunk_ids live OUTSIDE the loop and accumulate across iterations.
            with track_stage_duration("retrieval_ms"):
                for topic in plan_output.topics:
                    # Retrieve top 5 matching chunks per topic (increased from 3 for richer context)
                    topic_chunks = await run_retrieval_pipeline(topic, search_id, top_k=5)
                    print(f"[Retrieval] Iteration {state.iteration} topic='{topic[:55]}' -> {len(topic_chunks)} chunks")
                    for chunk in topic_chunks:
                        if chunk.id not in seen_chunk_ids:
                            seen_chunk_ids.add(chunk.id)
                            aggregated_chunks.append(chunk)

                        
            # Map RetrievedChunk list to EvidenceItem model objects
            state.evidence = []
            for c in aggregated_chunks:
                # Find corresponding source overall score for quality metadata
                source_q_score = 0.5
                for src in state.sources:
                    if src.url == c.url:
                        source_q_score = src.overall_score
                        break
                        
                state.evidence.append(EvidenceItem(
                    id=c.id,
                    search_id=search_id,
                    subquery_id=c.subquery_id if c.subquery_id else 0,
                    chunk_id=c.id,
                    title=c.title,
                    url=c.url,
                    domain=c.domain,
                    text=c.text,
                    similarity_score=c.score,
                    source_quality_score=source_q_score
                ))
                
            # Run Coverage Analyzer
            with track_stage_duration("coverage_analysis_ms"):
                state.coverage = await self.coverage_analyzer.analyze_coverage(plan_output.topics, state.evidence)
            metrics["llm_calls"] += 1
            
            if status_callback:
                await status_callback("coverage", {
                    "score": state.coverage.coverage_score,
                    "missing": state.coverage.missing_topics,
                    "covered": state.coverage.covered_topics
                })
                
            # Run Contradiction Detector
            state.contradictions = await self.contradiction_detector.detect_contradictions(plan_output.topics, state.evidence)
            metrics["llm_calls"] += len(state.contradictions) # Log LLM calls used by contradictions check
            
            if state.contradictions:
                # Save contradictions to Postgres
                async with AsyncSessionLocal() as session:
                    try:
                        for contra in state.contradictions:
                            db_contra = ResearchContradictionModel(
                                research_id=search_id,
                                topic=contra.topic,
                                claim_a=contra.claim_a,
                                source_a_url=contra.source_a,
                                claim_b=contra.claim_b,
                                source_b_url=contra.source_b,
                                severity=contra.severity
                            )
                            session.add(db_contra)
                        await session.commit()
                    except Exception as db_err:
                        print(f"Failed to log contradiction: {db_err}")
                        
            # Update research session progress details in Postgres
            async with AsyncSessionLocal() as session:
                try:
                    db_sess = await session.get(ResearchSessionModel, search_id)
                    if db_sess:
                        db_sess.iterations = state.iteration
                        db_sess.coverage_score = state.coverage.coverage_score
                        db_sess.sources_analyzed = len(state.sources)
                        await session.commit()
                except Exception as db_err:
                    print(f"Failed to update session stats: {db_err}")
                    
            # --- 5. CHECK STOP CONDITIONS ---
            if not state.coverage.needs_more_research:
                stop_reason = "coverage_threshold_reached"
                break
                
            if len(state.sources) >= max_sources:
                stop_reason = "max_sources_reached"
                break
                
            # Check if subquery quota is already full
            remaining_subqueries = max_subqueries - len(state.subqueries)
            if remaining_subqueries <= 0:
                stop_reason = "max_subqueries_reached"
                break
                
            # Generate targeted follow-up subqueries for missing topics
            follow_up_subqueries = await self.decomposer.generate_follow_up(
                query,
                state.coverage.missing_topics,
                executed_queries
            )
            follow_up_subqueries = follow_up_subqueries[:remaining_subqueries]
            metrics["llm_calls"] += 1
            
            if not follow_up_subqueries:
                stop_reason = "no_new_queries_generated"
                break
                
            if status_callback:
                await status_callback("follow_up", {
                    "queries": [sub.query for sub in follow_up_subqueries],
                    "iteration": state.iteration
                })
                
            # Save follow-up subqueries to Postgres
            async with AsyncSessionLocal() as session:
                try:
                    for subq in follow_up_subqueries:
                        db_sub = ResearchSubqueryModel(
                            research_id=search_id,
                            query=subq.query,
                            purpose=subq.purpose,
                            priority=subq.priority,
                            status="pending",
                            iteration=state.iteration + 1
                        )
                        session.add(db_sub)
                    await session.commit()
                except Exception as db_err:
                    print(f"Failed to save follow-up subqueries: {db_err}")
                    
            # Append new subqueries and progress iteration
            state.subqueries.extend(follow_up_subqueries)
            state.iteration += 1
            
        # Loop finished, set status
        state.status = "completed"
        
        # --- 5b. FINAL BROAD RETRIEVAL PASS (post-loop) ---
        # Run a broad full-query retrieval to supplement topic-level chunks.
        # Guarantees synthesis receives sufficient evidence even if topic-level retrieval
        # was sparse. Uses the full original query for maximum semantic coverage.
        if status_callback:
            await status_callback("status", {"stage": "synthesizing", "message": "Performing final evidence aggregation..."})
            
        with track_stage_duration("retrieval_ms"):
            broad_chunks = await run_retrieval_pipeline(query, search_id, top_k=settings.RAG_TOP_K)
            broad_added = 0
            for chunk in broad_chunks:
                if chunk.id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk.id)
                    aggregated_chunks.append(chunk)
                    broad_added += 1
        
        # Diagnostic summary
        print(f"[Research Loop] Final broad pass: {len(broad_chunks)} retrieved, {broad_added} new unique added")
        print(f"[Research Loop] Total aggregated_chunks for synthesis: {len(aggregated_chunks)}")
        print(f"[Research Loop] stop_reason: {stop_reason}, iterations: {state.iteration}")
        if state.coverage:
            print(f"[Research Loop] coverage_score: {state.coverage.coverage_score}, "
                  f"covered: {state.coverage.covered_topics}, missing: {state.coverage.missing_topics}")
        
        # --- 6. ANSWER SYNTHESIS ---
        if status_callback:
            await status_callback("status", {"stage": "synthesizing", "message": "Synthesizing final grounded response..."})
            
        with track_stage_duration("llm_generation_ms"):
            final_answer = await self.synthesizer.synthesize(
                query,
                search_id,
                aggregated_chunks,
                state.contradictions
            )
        metrics["llm_calls"] += 1

        
        # Save synthesis response to GeneratedAnswer PostgreSQL table
        async with AsyncSessionLocal() as session:
            try:
                db_sess = await session.get(ResearchSessionModel, search_id)
                if db_sess:
                    db_sess.status = "completed"
                    db_sess.completed_at = datetime.utcnow()
                    
                db_answer = GeneratedAnswerModel(
                    search_id=search_id,
                    query=query,
                    answer=final_answer.answer,
                    provider=settings.LLM_PROVIDER,
                    model=settings.GEMINI_MODEL,
                    generation_time_ms=final_answer.generation_time_ms,
                    grounded=final_answer.grounded
                )
                session.add(db_answer)
                await session.commit()
            except Exception as db_err:
                print(f"Failed to save final grounded response details: {db_err}")
                
        # Append budget metrics
        metrics_dict = {
            "pages_crawled": metrics["pages_crawled"],
            "chunks_indexed": metrics["chunks_indexed"],
            "llm_calls": metrics["llm_calls"],
            "search_requests": metrics["search_requests"],
            "skipped_duplicate_queries": metrics["skipped_duplicate_queries"],
            "failed_crawls": metrics["failed_crawls"],
            "stop_reason": stop_reason
        }
        
        if status_callback:
            await status_callback("done", {
                "search_id": search_id,
                "iterations": state.iteration,
                "coverage_score": state.coverage.coverage_score if state.coverage else 0.0,
                "sources_analyzed": len(state.sources),
                "answer": final_answer.answer,
                "citations": [c.model_dump() for c in final_answer.citations],
                "research_metadata": metrics_dict
            })
            
        return state, final_answer, metrics_dict
