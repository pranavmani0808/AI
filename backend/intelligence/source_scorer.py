import re
from urllib.parse import urlparse
from typing import Optional
from backend.core.config import settings
from backend.intelligence.models import ResearchSource

class SourceScorer:
    """
    Ranks web source URLs using authority, relevance, and freshness heuristics.
    Prioritizes official first-party documentation and avoids domain suffix biases like generic .org.
    """
    def __init__(self):
        pass

    def score_source(self, url: str, title: str, excerpt: str, query: str, rank: int, source_preference: Optional[str] = "balanced") -> ResearchSource:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        title_lower = title.lower() if title else ""
        excerpt_lower = excerpt.lower() if excerpt else ""
        query_lower = query.lower()
        
        # --- 1. AUTHORITY SCORE ---
        authority_score = 0.2 # Baseline
        
        # Check for official/first-party doc patterns:
        # e.g., if query has "react" and domain is "react.dev", or query has "next.js" and domain is "nextjs.org"
        query_keywords = set(re.findall(r'\b[a-z]{3,}\b', query_lower))
        domain_keywords = set(re.findall(r'\b[a-z]{3,}\b', domain.replace('.', ' ')))
        
        has_overlap = False
        for qw in query_keywords:
            if qw in ["docs", "guide", "tutorial", "reference", "developer", "how", "what", "the"]:
                continue
            for dw in domain_keywords:
                if dw in ["org", "com", "net", "dev", "www", "blog"]:
                    continue
                if qw in dw or dw in qw:
                    has_overlap = True
                    break
            if has_overlap:
                break
        
        is_docs_path = any(term in path for term in ["/docs", "/doc/", "/guide", "/tutorial", "/reference", "/developer"])
        is_docs_subdomain = any(term in domain for term in ["docs.", "developer.", "doc."])
        
        if has_overlap and (is_docs_path or is_docs_subdomain):
            # Highly likely first-party official documentation site
            authority_score += 0.6
        elif is_docs_path or is_docs_subdomain:
            # Secondary documentation site
            authority_score += 0.3
            
        # Trusted institutional/academic suffixes (excluding generic .org)
        if domain.endswith(".edu") or domain.endswith(".gov"):
            authority_score += 0.3
            
        # Common high-authority dev communities & reference sites
        known_dev_sites = ["github.com", "stackoverflow.com", "developer.mozilla.org", "w3schools.com"]
        if any(site in domain for site in known_dev_sites):
            authority_score += 0.25
            
        # SearXNG search rank corroboration (earlier rank represents higher search engine corroboration)
        rank_bonus = max(0.0, 0.15 - (rank * 0.02))
        authority_score += rank_bonus
        
        # Cap authority at 1.0
        authority_score = min(1.0, max(0.0, authority_score))
        
        # --- 2. RELEVANCE SCORE ---
        # Match count of query keywords in title and excerpt
        relevance_score = 0.1
        if query_keywords:
            text_to_search = f"{title_lower} {excerpt_lower}"
            matched_in_text = sum(1 for kw in query_keywords if kw in text_to_search)
            match_ratio = matched_in_text / len(query_keywords)
            relevance_score += match_ratio * 0.9
            
        relevance_score = min(1.0, max(0.0, relevance_score))
        
        # --- 3. FRESHNESS SCORE ---
        freshness_score = 0.5 # Default baseline
        
        # Extract years from text (focus on recent years up to 2026)
        text_to_search = f"{title_lower} {excerpt_lower} {path}"
        years = re.findall(r'\b(202[0-6])\b', text_to_search)
        if years:
            latest_year = max(int(y) for y in years)
            if latest_year == 2026:
                freshness_score = 1.0
            elif latest_year == 2025:
                freshness_score = 0.85
            elif latest_year == 2024:
                freshness_score = 0.7
            else:
                freshness_score = 0.5
        else:
            # No year found, search rank decay fallback
            freshness_score = max(0.2, 0.6 - (rank * 0.05))
            
        # --- 4. OVERALL COMBINATION & PREFERENCES ---
        weight_authority = settings.WEIGHT_AUTHORITY
        weight_relevance = settings.WEIGHT_RELEVANCE
        weight_freshness = settings.WEIGHT_FRESHNESS
        
        if source_preference == "primary":
            weight_authority = 0.60
            weight_relevance = 0.30
            weight_freshness = 0.10
            # Boost authority for potential official sites
            if authority_score >= 0.4:
                authority_score = min(1.0, authority_score + 0.3)
        elif source_preference == "recent":
            weight_authority = 0.20
            weight_relevance = 0.30
            weight_freshness = 0.50
            # Boost freshness
            freshness_score = min(1.0, freshness_score + 0.3)
            
        overall_score = (
            authority_score * weight_authority +
            relevance_score * weight_relevance +
            freshness_score * weight_freshness
        )
        
        # Classify source type label based on score levels
        if authority_score >= 0.75:
            source_type = "Primary / Official"
        elif authority_score >= 0.5:
            source_type = "High-quality secondary"
        elif authority_score >= 0.3:
            source_type = "Secondary"
        else:
            source_type = "Unknown"
            
        return ResearchSource(
            url=url,
            title=title,
            domain=domain,
            source_type=source_type,
            authority_score=round(authority_score, 3),
            relevance_score=round(relevance_score, 3),
            freshness_score=round(freshness_score, 3),
            overall_score=round(overall_score, 3)
        )
