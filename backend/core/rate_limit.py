import time
from fastapi import Request, HTTPException, status
import redis.asyncio as aioredis
from backend.core.config import settings

async def check_rate_limit(request: Request):
    """
    Dependency checking rate limits for expensive endpoints (e.g., searches, answers).
    Default limits to 5 requests per minute, bypasses on connection errors.
    """
    # Bypass limits in testing environment
    if settings.APP_ENV == "testing":
        return
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    path = request.url.path
    key = f"rate_limit:{client_ip}:{path}"
    
    limit = 5
    period = 60
    
    client = None
    try:
        client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0, decode_responses=True)
        current = await client.get(key)
        if current is not None:
            count = int(current)
            if count >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too Many Requests. Rate limit exceeded (Max 5 requests per minute)."
                )
            await client.incr(key)
        else:
            await client.setex(key, period, 1)
    except HTTPException as he:
        raise he
    except Exception as e:
        # Gracefully degrade and allow requests if Redis is offline
        print(f"Rate limiter Redis connection offline, bypassing limits: {e}")
    finally:
        if client:
            await client.close()
