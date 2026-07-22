import os
import sys
import json
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

# Set workspace path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.config import settings
from backend.llm.gemini import GeminiProvider
from backend.intelligence.research_loop import AutonomousResearchLoop
from backend.evaluation.citation_eval import evaluate_citations
from backend.evaluation.retrieval_eval import evaluate_retrieval
from backend.evaluation.research_eval import evaluate_research_flow
from backend.evaluation.answer_eval import evaluate_answer
from backend.evaluation.models import TestCaseResult, BenchmarkReport

async def run_benchmark():
    print("==================================================")
    print("AI Search Engine: Starting Benchmark Evaluation Runs")
    print("==================================================")
    
    # Load benchmark dataset
    dataset_path = os.path.join(os.path.dirname(__file__), "datasets", "benchmark.json")
    if not os.path.exists(dataset_path):
        print(f"Error: Benchmark dataset file missing at {dataset_path}")
        return
        
    with open(dataset_path, "r") as f:
        cases = json.load(f)
        
    print(f"Loaded {len(cases)} benchmark queries for evaluation.")
    
    results = []
    successful = 0
    failed = 0
    total_start_time = time.time()
    
    provider = GeminiProvider()
    
    # Ensure directory output exists
    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    
    for case in cases:
        query_id = case["id"]
        query = case["query"]
        category = case["category"]
        expected_topics = case.get("expected_topics", [])
        
        print(f"\n[{query_id}] Running query ({category}): '{query}'...")
        
        start_time = time.perf_counter()
        loop = AutonomousResearchLoop()
        
        try:
            # Bypass rate limit middleware to test engine directly
            state, final_answer, metrics = await loop.execute_research(query)
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Map Pydantic models to serializable dicts
            citations_dicts = [c.model_dump() for c in final_answer.citations]
            evidence_dicts = [
                {
                    "id": getattr(ev, "id", f"ev_{i}"),
                    "sourceId": getattr(ev, "source_id", "src_1"),
                    "content": getattr(ev, "text", ""),
                    "relevanceScore": int(getattr(ev, "similarity_score", 0.8) * 100),
                    "url": getattr(ev, "url", ""),
                    "domain": getattr(ev, "domain", "")
                }
                for i, ev in enumerate(state.evidence)
            ]
            
            # Evaluate metrics
            cit_eval = evaluate_citations(final_answer.answer, citations_dicts, evidence_dicts)
            ret_eval = evaluate_retrieval(state.evidence)
            flow_eval = evaluate_research_flow(state, metrics)
            
            # Optional LLM-assisted evaluation for groundedness
            # Since LLM is on free-tier, we skip LLM provider here to save API limits,
            # using deterministic metrics inside test runners.
            ans_eval = await evaluate_answer(final_answer.answer, query, expected_topics, provider=None)
            
            results.append(TestCaseResult(
                query_id=query_id,
                query=query,
                category=category,
                success=True,
                latency_ms=latency_ms,
                citation_metrics={**cit_eval, "claim_risk": ans_eval["unsupported_claim_risk"]},
                retrieval_metrics=ret_eval,
                research_metrics=flow_eval,
                answer=final_answer.answer
            ))
            successful += 1
            print(f"✓ Query completed in {latency_ms / 1000:.2f}s (Coverage: {flow_eval['coverage_score'] * 100}%)")
            
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            failed += 1
            print(f"✗ Query failed: {e}")
            results.append(TestCaseResult(
                query_id=query_id,
                query=query,
                category=category,
                success=False,
                latency_ms=latency_ms,
                error_code=str(type(e).__name__),
                citation_metrics={"citation_validity": 0.0, "citation_coverage": 0.0, "citation_source_diversity": 0},
                retrieval_metrics={"top_k": 0, "avg_similarity": 0.0, "max_similarity": 0.0, "min_similarity": 0.0, "unique_domains": 0},
                research_metrics={"initial_topics": 0, "covered_topics": 0, "missing_topics": 0, "coverage_score": 0.0, "iterations": 0, "stop_reason": "failed"},
                answer=""
            ))
            
        # Pace benchmark query executions to respect rate limits
        await asyncio.sleep(2.0)
        
    total_duration = time.time() - total_start_time
    
    # 2. Compile metrics aggregates
    latencies = [r.latency_ms for r in results if r.success]
    citation_validities = [r.citation_metrics["citation_validity"] for r in results if r.success]
    citation_coverages = [r.citation_metrics["citation_coverage"] for r in results if r.success]
    evidence_coverages = [r.research_metrics["coverage_score"] for r in results if r.success]
    unique_sources = [r.research_metrics["sources_crawled"] for r in results if r.success]
    iterations_run = [r.research_metrics["iterations"] for r in results if r.success]
    
    stop_reasons = {}
    for r in results:
        if r.success:
            reason = r.research_metrics["stop_reason"]
            stop_reasons[reason] = stop_reasons.get(reason, 0) + 1
            
    report = BenchmarkReport(
        total_queries=len(cases),
        successful=successful,
        failed=failed,
        avg_latency_ms=int(sum(latencies) / len(latencies)) if latencies else 0,
        avg_citation_validity=round(sum(citation_validities) / len(citation_validities), 3) if citation_validities else 1.0,
        avg_citation_coverage=round(sum(citation_coverages) / len(citation_coverages), 3) if citation_coverages else 0.0,
        avg_evidence_coverage=round(sum(evidence_coverages) / len(evidence_coverages), 3) if evidence_coverages else 0.0,
        avg_unique_sources=round(sum(unique_sources) / len(unique_sources), 3) if unique_sources else 0.0,
        avg_iterations=round(sum(iterations_run) / len(iterations_run), 3) if iterations_run else 1.0,
        stop_reasons=stop_reasons,
        results=results
    )
    
    # 3. Write latest.json report output
    results_path = os.path.join(os.path.dirname(__file__), "results", "latest.json")
    with open(results_path, "w") as rf:
        json.dump(report.model_dump(), rf, indent=2)
        
    # Log report session outcomes to PostgreSQL
    try:
        from backend.database.postgres import AsyncSessionLocal
        from backend.database.models import EvaluationRunModel
        async with AsyncSessionLocal() as session:
            db_run = EvaluationRunModel(
                started_at=datetime.fromtimestamp(total_start_time),
                completed_at=datetime.utcnow(),
                total_cases=len(cases),
                passed=successful,
                failed=failed,
                average_latency_ms=report.avg_latency_ms
            )
            session.add(db_run)
            await session.commit()
    except Exception as db_err:
        print(f"Failed to log evaluation run details to DB: {db_err}")
        
    print("\n==================================================")
    print("AI Search Engine Evaluation: Benchmark Results")
    print("==================================================")
    print(f"Queries tested: {report.total_queries}")
    print(f"Successful:     {report.successful}")
    print(f"Failed:         {report.failed}")
    print(f"Avg Latency:    {report.avg_latency_ms / 1000:.2f}s")
    print(f"Citation validity: {report.avg_citation_validity * 100:.1f}%")
    print(f"Average evidence coverage: {report.avg_evidence_coverage * 100:.1f}%")
    print(f"Average unique sources: {report.avg_unique_sources:.1f}")
    print(f"Average research iterations: {report.avg_iterations:.1f}")
    print(f"Total time:     {total_duration:.2f}s")
    print("\nStop reasons distribution:")
    for reason, count in report.stop_reasons.items():
        print(f"- {reason}: {count}")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
