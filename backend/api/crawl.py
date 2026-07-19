from fastapi import APIRouter

router = APIRouter(prefix="/crawl", tags=["Crawl"])

@router.post("")
async def start_crawl(url: str):
    """Placeholder endpoint to trigger a website crawl."""
    return {
        "status": "pending",
        "job_id": "placeholder-crawl-job-id",
        "url": url,
        "message": "Crawl job queued (placeholder)"
    }

@router.get("/{job_id}")
async def get_crawl_status(job_id: str):
    """Placeholder endpoint to check crawl job status."""
    return {
        "job_id": job_id,
        "status": "completed",
        "url": "https://example.com",
        "extracted_text": "This is mock extracted text content from Phase 1 crawler placeholder."
    }
