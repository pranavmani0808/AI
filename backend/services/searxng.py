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
