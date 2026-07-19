from fastapi import APIRouter

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("")
async def search(q: str):
    """Placeholder search endpoint for Phase 1."""
    return {
        "status": "placeholder",
        "query": q,
        "results": [
            {
                "title": "Example Search Result 1",
                "url": "https://example.com/1",
                "snippet": "This is a placeholder result for query: " + q
            },
            {
                "title": "Example Search Result 2",
                "url": "https://example.com/2",
                "snippet": "This is another placeholder result for query: " + q
            }
        ]
    }
