import redis.asyncio as aioredis
from backend.core.config import settings

async def check_redis_health() -> bool:
    """Verifies Redis connection health by sending a PING command."""
    try:
        # Create an async redis client from connection string
        client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        pong = await client.ping()
        await client.close()
        return pong is True
    except Exception as e:
        print(f"Redis health check failed: {e}")
        return False
