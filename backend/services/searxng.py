import httpx
from backend.core.config import settings

async def check_searxng_health() -> bool:
    """Verifies that SearXNG service is responding by hitting its base endpoint."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{settings.SEARXNG_URL}/")
            return res.status_code == 200
    except Exception as e:
        print(f"SearXNG health check connection error: {e}")
        return False

async def verify_searxng_json_query() -> bool:
    """Sends a mock query test request to verify json outputs from SearXNG search discovery."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(f"{settings.SEARXNG_URL}/search", params={"q": "test", "format": "json"})
            if res.status_code == 200:
                data = res.json()
                return "results" in data
            return False
    except Exception as e:
        print(f"SearXNG query validation error: {e}")
        return False

from typing import List
from backend.search.models import SearchResult

async def search_searxng(query: str, limit: int = 15, time_range: Optional[str] = None) -> List[SearchResult]:
    """
    Queries SearXNG search engine for web search discovery results.
    - Sends request to internal or external SEARXNG_URL
    - Requests JSON output format
    - Handles timeouts and returns normalized SearchResult list
    """
    from typing import Optional
    url = f"{settings.SEARXNG_URL}/search"
    params = {
        "q": query,
        "format": "json",
    }
    if time_range:
        params["time_range"] = time_range
    
    try:
        async with httpx.AsyncClient(timeout=settings.TIMEOUT_SEARXNG) as client:
            res = await client.get(url, params=params)
            if res.status_code != 200:
                print(f"SearXNG query returned non-200 status: {res.status_code}")
                return []
                
            data = res.json()
            raw_results = data.get("results", [])
            
            search_results = []
            for item in raw_results[:limit]:
                # Map keys cleanly
                title = item.get("title", "")
                item_url = item.get("url", "")
                snippet = item.get("content", "") or item.get("snippet", "") or ""
                engine = item.get("engine", "") or "searxng"
                score = item.get("score", 0.0)
                
                if title and item_url:
                    search_results.append(SearchResult(
                        title=title,
                        url=item_url,
                        snippet=snippet,
                        engine=engine,
                        score=float(score)
                    ))
            return search_results
    except Exception as e:
        print(f"SearXNG query request failed: {e}")
        return []

