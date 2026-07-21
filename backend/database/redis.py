import redis.asyncio as aioredis
from backend.core.config import settings

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
