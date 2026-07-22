import redis.asyncio as aioredis
from backend.core.config import settings

import json
from typing import List, Optional

async def check_redis_health() -> bool:
    """Verifies Redis health status by executing a client PING command."""
    try:
        # Create an async redis client linked to settings DB 0
        client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        pong = await client.ping()
        await client.close()
        return pong is True
    except Exception as e:
        print(f"Redis health check connection error: {e}")
        return False

async def get_cached_search(query: str) -> Optional[List[dict]]:
    """Retrieves cached search results from Redis for a given query."""
    client = None
    try:
        client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0, decode_responses=True)
        key = f"search_cache:{query.lower().strip()}"
        cached = await client.get(key)
        if cached:
            return json.loads(cached)
        return None
    except Exception as e:
        print(f"Failed to read search cache: {e}")
        return None
    finally:
        if client:
            await client.close()

async def set_cached_search(query: str, results: List[dict], ttl: int = 1800):
    """Caches search results in Redis with a time-to-live (default 30 mins)."""
    client = None
    try:
        client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        key = f"search_cache:{query.lower().strip()}"
        await client.setex(key, ttl, json.dumps(results))
    except Exception as e:
        print(f"Failed to write search cache: {e}")
    finally:
        if client:
            await client.close()

async def get_cached_page(url: str) -> Optional[dict]:
    """Retrieves cached crawled page content from Redis."""
    client = None
    try:
        client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0, decode_responses=True)
        key = f"page_cache:{url.strip()}"
        cached = await client.get(key)
        if cached:
            return json.loads(cached)
        return None
    except Exception as e:
        print(f"Failed to read page cache: {e}")
        return None
    finally:
        if client:
            await client.close()

async def set_cached_page(url: str, page_data: dict, ttl: int = 86400):
    """Caches crawled page content in Redis (default 24 hours)."""
    client = None
    try:
        client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        key = f"page_cache:{url.strip()}"
        await client.setex(key, ttl, json.dumps(page_data))
    except Exception as e:
        print(f"Failed to write page cache: {e}")
    finally:
        if client:
            await client.close()

