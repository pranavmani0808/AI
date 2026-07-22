import asyncio
from backend.core.celery_app import celery_app
from backend.crawler.crawler import crawl_url
from backend.database.postgres import AsyncSessionLocal
from backend.database.models import CrawlResult
from datetime import datetime
from typing import Optional

@celery_app.task(name="backend.tasks.crawl_tasks.crawl_url_task")
def crawl_url_task(url: str, search_id: Optional[int] = None) -> dict:
    """
    Celery task that runs in the background to crawl a URL,
    extracts content, and persists metadata in PostgreSQL.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        doc = loop.run_until_complete(crawl_url(url, search_id))
        
        # Persist results in Database
        async def save_to_db():
            async with AsyncSessionLocal() as session:
                db_result = CrawlResult(
                    search_id=search_id,
                    url=doc.url,
                    title=doc.title,
                    status_code=doc.status_code,
                    crawl_status=doc.crawl_status,
                    word_count=doc.word_count,
                    extracted_text=doc.text,
                    crawled_at=datetime.utcnow()
                )
                session.add(db_result)
                await session.commit()
                
        loop.run_until_complete(save_to_db())
        
        return {
            "url": doc.url,
            "crawl_status": doc.crawl_status,
            "word_count": doc.word_count,
            "title": doc.title
        }
    finally:
        loop.close()
