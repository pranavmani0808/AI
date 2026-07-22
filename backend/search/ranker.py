from typing import List
import re
from backend.search.models import SearchResult

def rank_search_results(results: List[SearchResult], query: str) -> List[SearchResult]:
    """
    Ranks unique search results based on relevance:
    - Base score is set from SearXNG's relative relevance score
    - Boosts score if search terms appear in the title or snippet
    - Down-scores obvious spam keywords or directory indices if present
    Returns sorted list, descending by score.
    """
    ranked = []
    # Tokenize query words for match counts
    query_tokens = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]
    
    for item in results:
        # Base score starts with SearXNG score or fallback
        score = item.score if item.score > 0 else 0.5
        
        # Boost for title matches
        title_lower = item.title.lower()
        title_matches = sum(1 for token in query_tokens if token in title_lower)
        if len(query_tokens) > 0:
            score += 0.3 * (title_matches / len(query_tokens))
            
        # Boost for snippet matches
        snippet_lower = item.snippet.lower()
        snippet_matches = sum(1 for token in query_tokens if token in snippet_lower)
        if len(query_tokens) > 0:
            score += 0.1 * (snippet_matches / len(query_tokens))
            
        # Domain safety adjustments (e.g. down-score PDF files or raw directories for search indices)
        if item.url.endswith('.pdf') or '/cgi-bin/' in item.url:
            score -= 0.2
            
        # Ensure score is normalized within 0.0 to 1.0 boundary for UI consistency
        item.score = max(0.0, min(1.0, round(score, 4)))
        ranked.append(item)
        
    # Sort descending by calculated score
    ranked.sort(key=lambda x: x.score, reverse=True)
    return ranked
