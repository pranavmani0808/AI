from fastapi import APIRouter, HTTPException, status
from backend.crawler.models import CrawlRequest, CrawledDocument
from backend.crawler.crawler import crawl_url

router = APIRouter(prefix="/crawl", tags=["Crawl"])

@router.get("/status")
async def get_crawl_status():
    """Placeholder crawl module status check for Phase 1/2."""
    return {
        "module": "crawler",
        "status": "ready",
        "phase": "placeholder"
    }

@router.post("", response_model=CrawledDocument)
async def perform_crawl(request: CrawlRequest):
    """
    Direct scraping API endpoint:
    Accepts URL, performs SSRF and robots validation, crawls webpage body text,
    removes html noise elements, and returns clean plain text.
    """
    try:
        doc = await crawl_url(request.url)
        
        # If blocked by safety or robots rules, raise error
        if doc.crawl_status == "BLOCKED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=doc.error_message or "URL crawling blocked due to safety or robot restrictions"
            )
            
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Crawling request failed: {str(e)}"
        )
