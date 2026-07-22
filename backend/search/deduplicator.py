from typing import List
from backend.search.models import SearchResult
from backend.search.normalizer import normalize_url

def deduplicate_results(results: List[SearchResult]) -> List[SearchResult]:
    """
    Remove duplicate search results based on their normalized URL representation.
    Preserves the order of appearance (typically keeping the highest ranked).
    """
    seen_urls = set()
    deduplicated = []
    
    for item in results:
        norm = normalize_url(item.url)
        if norm not in seen_urls:
            seen_urls.add(norm)
            deduplicated.append(item)
            
    return deduplicated
