from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import httpx
import redis.asyncio as aioredis
from backend.core.config import settings

# Shared Redis client for caching
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def check_crawling_permission(url: str, user_agent: str = "IntelliSearchBot") -> bool:
    """
    Checks if crawling is permitted for a URL by checking its robots.txt file.
    - Fetches from host, parses rules, and caches the raw robots.txt content in Redis for 1 hour.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        scheme = parsed.scheme.lower()
        
        if not domain or scheme not in ("http", "https"):
            return False
            
        robots_url = f"{scheme}://{domain}/robots.txt"
        cache_key = f"robots_cache:{domain}"
        
        # 1. Attempt to pull from Redis cache
        robots_content = None
        try:
            robots_content = await redis_client.get(cache_key)
        except Exception as e:
            print(f"Redis robots.txt cache read failed: {e}")
            
        # 2. Fetch fresh if cache miss
        if robots_content is None:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    # Impersonate standard bot header
                    headers = {"User-Agent": user_agent}
                    res = await client.get(robots_url, headers=headers, follow_redirects=True)
                    if res.status_code == 200:
                        robots_content = res.text
                    else:
                        robots_content = "" # Empty content means no restriction rules
            except Exception as e:
                # If robots.txt cannot be fetched or times out, default to allowed
                print(f"Failed to fetch robots.txt for {domain}: {e}")
                robots_content = ""
                
            # Store in Redis cache for 1 hour (3600 seconds)
            try:
                await redis_client.setex(cache_key, 3600, robots_content)
            except Exception as e:
                print(f"Redis robots.txt cache write failed: {e}")
                
        # 3. Parse and match rules using standard RobotFileParser
        parser = RobotFileParser()
        # Parse requires a list of lines or direct string
        parser.parse(robots_content.splitlines())
        
        # Verify if our agent can crawl the path
        return parser.can_fetch(user_agent, url)
    except Exception as e:
        print(f"robots.txt check failed for {url}: {e}")
        # Default to safe true (allow) in case of system parser crash
        return True
