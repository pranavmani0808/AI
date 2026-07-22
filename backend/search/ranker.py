import re
from typing import List, Dict, Any, Tuple
from backend.search.models import SearchResult
from backend.intelligence.query_router import QueryIntent

# Categorized Domain Registries
PRODUCT_TIER1_DOMAINS = {
    "amazon.in", "flipkart.com", "apple.com", "samsung.com", "oneplus.in", "oneplus.com",
    "mi.com", "realme.com", "vivo.com", "oppo.com", "motorola.in", "google.com"
}

PRODUCT_TIER2_DOMAINS = {
    "91mobiles.com", "gadgets360.com", "smartprix.com", "techradar.com", "digit.in",
    "gsmarena.com", "tomshardware.com", "rtings.com", "notebookcheck.net", "theverge.com",
    "cnet.com", "androidcentral.com", "xda-developers.com", "mysmartprice.com"
}

PRODUCT_PENALIZED_DOMAINS = {
    "geeksforgeeks.org", "w3schools.com", "tutorialspoint.com", "uxpin.com", "buttercups.tech",
    "javatpoint.com", "leetcode.com", "hackerrank.com", "npm.com", "pypi.org"
}

ACADEMIC_DOMAINS = {
    "arxiv.org", "scholar.google.com", "researchgate.net", "ieee.org", "acm.org",
    "nature.com", "sciencedirect.com", "semanticscholar.org", "springer.com"
}

NEWS_TECH_DOMAINS = {
    "techcrunch.com", "theverge.com", "arstechnica.com", "engadget.com", "wired.com",
    "reuters.com", "bloomberg.com", "news.ycombinator.com", "bbc.com", "apnews.com"
}

def get_source_type(domain: str) -> str:
    """Classifies domain into human-readable source types."""
    d = domain.lower().replace("www.", "")
    if any(m in d for m in ["apple.com", "samsung.com", "oneplus", "mi.com", "realme", "vivo", "oppo", "google.com"]):
        return "manufacturer"
    if any(r in d for r in ["amazon", "flipkart"]):
        return "retailer"
    if d in PRODUCT_TIER2_DOMAINS or "mobile" in d or "gadget" in d or "smartprix" in d:
        return "review"
    if d in ACADEMIC_DOMAINS or d.endswith(".edu"):
        return "academic"
    if d in NEWS_TECH_DOMAINS:
        return "news"
    return "other"

def calculate_domain_intent_score(domain: str, intent: str) -> float:
    """Computes intent-aware domain compatibility score [0.0 - 1.0]."""
    d = domain.lower().replace("www.", "")
    
    if intent == QueryIntent.PRODUCT.value or intent == "product":
        if d in PRODUCT_TIER1_DOMAINS:
            return 1.00
        if d in PRODUCT_TIER2_DOMAINS or "mobile" in d or "gadget" in d or "smartprix" in d:
            return 0.95
        if d in NEWS_TECH_DOMAINS:
            return 0.80
        if d in PRODUCT_PENALIZED_DOMAINS:
            return 0.15
        return 0.50

    if intent == QueryIntent.ACADEMIC.value or intent == "academic":
        if d in ACADEMIC_DOMAINS or d.endswith(".edu"):
            return 1.00
        if d in NEWS_TECH_DOMAINS:
            return 0.70
        return 0.40

    if intent in [QueryIntent.WEB_SEARCH.value, QueryIntent.RESEARCH.value, "web_search", "research"]:
        if d in NEWS_TECH_DOMAINS or d in PRODUCT_TIER2_DOMAINS:
            return 0.95
        if d in ACADEMIC_DOMAINS or d.endswith(".edu"):
            return 0.90
        return 0.65

    return 0.50

def rank_search_results(results: List[SearchResult], query: str, intent: str = "web_search") -> List[SearchResult]:
    """
    Multi-signal Intent-Aware Search Result Reranker:
    Scores candidate results before crawling based on:
    1. Title-query keyword relevance (0.35)
    2. Snippet-query keyword relevance (0.25)
    3. Domain-intent compatibility score (0.40)
    
    Applies domain diversity capping (max 2 per domain).
    """
    if not results:
        return []

    query_tokens = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]
    ranked = []

    for item in results:
        domain = item.url.split("//")[-1].split("/")[0].lower().replace("www.", "")
        
        # Signal 1: Title relevance
        title_lower = item.title.lower()
        title_matches = sum(1 for token in query_tokens if token in title_lower)
        title_rel = (title_matches / len(query_tokens)) if query_tokens else 0.5
        
        # Signal 2: Snippet relevance
        snippet_lower = item.snippet.lower()
        snippet_matches = sum(1 for token in query_tokens if token in snippet_lower)
        snippet_rel = (snippet_matches / len(query_tokens)) if query_tokens else 0.5
        
        # Signal 3: Intent-Domain compatibility score
        domain_score = calculate_domain_intent_score(domain, intent)
        
        # Pre-crawl composite score calculation
        pre_crawl_score = (0.35 * title_rel) + (0.25 * snippet_rel) + (0.40 * domain_score)
        
        # Penalty adjustments for raw pdfs or query-irrelevant directories
        if item.url.endswith('.pdf') or '/cgi-bin/' in item.url:
            pre_crawl_score -= 0.15
            
        item.score = max(0.0, min(1.0, round(pre_crawl_score, 4)))
        ranked.append(item)

    # Sort descending by calculated pre-crawl score
    ranked.sort(key=lambda x: x.score, reverse=True)
    
    # Domain Diversity Capping (Max 2 URLs per domain)
    domain_counts = {}
    diversified_results = []
    
    for item in ranked:
        domain = item.url.split("//")[-1].split("/")[0].lower().replace("www.", "")
        count = domain_counts.get(domain, 0)
        if count < 2:
            domain_counts[domain] = count + 1
            diversified_results.append(item)
            
    return diversified_results
