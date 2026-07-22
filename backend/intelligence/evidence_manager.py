from typing import List, Set, Dict
from urllib.parse import urlparse
from backend.core.config import settings
from backend.search.models import SearchResult

class EvidenceManager:
    """
    Coordinates global URL deduplication and domain diversity filters across subqueries.
    Enforces maximum sources per domain limits.
    """
    def __init__(self):
        pass

    def filter_and_deduplicate(
        self,
        candidates: List[SearchResult],
        crawled_urls: Set[str],
        domain_counts: Dict[str, int]
    ) -> List[SearchResult]:
        """
        Filters candidates by:
        1. Global URL deduplication: skips if url is already crawled.
        2. Domain diversity: skips if domain count exceeds MAX_SOURCES_PER_DOMAIN limit.
        
        Returns the list of allowed SearchResult sources.
        """
        filtered_sources = []
        
        for candidate in candidates:
            url = candidate.url
            # Clean URL to standard form for deduplication
            normalized_url = url.strip().lower()
            
            if normalized_url in crawled_urls:
                continue
                
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix for consistent domain tracking
            if domain.startswith("www."):
                domain = domain[4:]
                
            current_domain_count = domain_counts.get(domain, 0)
            
            if current_domain_count >= settings.MAX_SOURCES_PER_DOMAIN:
                # Domain diversity cap reached for this domain
                continue
                
            # Accept URL
            filtered_sources.append(candidate)
            crawled_urls.add(normalized_url)
            domain_counts[domain] = current_domain_count + 1
            
        return filtered_sources
