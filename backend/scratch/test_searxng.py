import asyncio
import os
import sys

# Add current workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.searxng import search_searxng

async def main():
    try:
        results = await search_searxng("React Next.js", limit=5)
        print(f"SearXNG returned {len(results)} results:")
        for r in results:
            print(f"- {r.title} ({r.url})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
