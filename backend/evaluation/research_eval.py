from typing import List, Dict, Any

def evaluate_research_flow(state: Any, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates autonomous multi-step research iterations quality and checklist progress:
    - initial_topics: total checklist items planned
    - covered_topics: total topics successfully matched
    - missing_topics: topics left unresolved
    - coverage_score: final evidence coverage ratio
    - iterations: total iteration steps run
    - follow_up_queries: count of target follow-up searches
    - sources_discovered: count of total candidate links found
    - sources_crawled: count of urls successfully parsed
    - sources_failed: count of url scrape connection failures
    - unique_domains: number of unique domains crawled
    - contradictions_detected: count of factual conflicts found
    - stop_reason: stop reason tag (e.g. COVERAGE_REACHED)
    """
    # Safe defaults
    coverage_score = 0.0
    covered = []
    missing = []
    
    if hasattr(state, "coverage") and state.coverage:
        coverage_score = state.coverage.coverage_score
        covered = state.coverage.covered_topics
        missing = state.coverage.missing_topics
        
    initial_topics = len(covered) + len(missing)
    
    # Calculate unique domains
    unique_domains = set()
    for src in getattr(state, "sources", []):
        unique_domains.add(src.domain)
        
    return {
        "initial_topics": initial_topics,
        "covered_topics": len(covered),
        "missing_topics": len(missing),
        "coverage_score": round(coverage_score, 3),
        "iterations": getattr(state, "iteration", 1),
        "follow_up_queries": len(getattr(state, "subqueries", [])) - len(getattr(state, "initial_queries", []) or []),
        "sources_discovered": metrics.get("skipped_duplicate_queries", 0) + metrics.get("pages_crawled", 0),
        "sources_crawled": metrics.get("pages_crawled", 0),
        "sources_failed": metrics.get("failed_crawls", 0),
        "unique_domains": len(unique_domains),
        "contradictions_detected": len(getattr(state, "contradictions", [])),
        "stop_reason": metrics.get("stop_reason", "unknown")
    }
