import time
from typing import List, Dict, Any, Tuple
from datetime import datetime
from backend.search.models import SearchResult, SearchResponse
from backend.crawler.models import CrawledDocument
from backend.services.searxng import search_searxng
from backend.search.normalizer import normalize_url
from backend.search.deduplicator import deduplicate_results
from backend.search.ranker import rank_search_results
from backend.crawler.crawler import crawl_urls_concurrently, crawl_url
from backend.database.redis import get_cached_search, set_cached_search, get_cached_page, set_cached_page
from backend.database.postgres import AsyncSessionLocal
from backend.database.models import SearchQuery, CrawlResult

async def run_search_crawl_pipeline(query: str, limit: int = 10, max_crawl_sources: int = 6) -> Tuple[SearchResponse, List[CrawledDocument]]:
    """
    Executes the consolidated Search -> Scrape -> Extract pipeline:
    1. Checks Redis cache for query discovery results
    2. Fallback to SearXNG search + normalizes, deduplicates, and ranks candidate URLs
    3. Persists SearchQuery info to Postgres DB
    4. Triggers concurrent crawling for top N source domains
    5. Checks page level caches, fetches fresh HTML, extracts text, and stores details in DB and Redis
    """
    start_time = time.time()
    
    # --- STEP 1: Search Discovery ---
    normalized_query = query.lower().strip()
    cached_results = await get_cached_search(normalized_query)
    
    if cached_results:
        print(f"Search cache hit for query: '{query}'")
        search_results = [SearchResult(**item) for item in cached_results]
    else:
        print(f"Search cache miss. Querying SearXNG for: '{query}'")
        raw_results = await search_searxng(query, limit=30)
        # Normalize and Deduplicate
        unique_results = deduplicate_results(raw_results)
        # Score and Rank
        search_results = rank_search_results(unique_results, query)
        # Save to Redis search cache
        serializable_results = [item.model_dump() for item in search_results]
        await set_cached_search(normalized_query, serializable_results)
        
    # --- STEP 2: Save Query Metadata to Postgres ---
    duration_ms = int((time.time() - start_time) * 1000)
    search_query_id = None
    
    async with AsyncSessionLocal() as session:
        try:
            db_query = SearchQuery(
                query=query,
                result_count=len(search_results),
                duration_ms=duration_ms,
                created_at=datetime.utcnow()
            )
            session.add(db_query)
            await session.commit()
            await session.refresh(db_query)
            search_query_id = db_query.id
        except Exception as e:
            print(f"Failed to save search query to database: {e}")
            
    # --- STEP 3: Source Crawling & Scraping ---
    top_sources = search_results[:max_crawl_sources]
    crawled_documents = []
    urls_to_crawl = []
    
    # 3a. Check page cache first
    for source in top_sources:
        cached_doc = await get_cached_page(source.url)
        if cached_doc:
            print(f"Page cache hit for URL: {source.url}")
            crawled_documents.append(CrawledDocument(**cached_doc))
        else:
            urls_to_crawl.append(source.url)
            
    # 3b. Crawl cache misses concurrently
    if urls_to_crawl:
        print(f"Crawling {len(urls_to_crawl)} cache misses concurrently...")
        fresh_docs = await crawl_urls_concurrently(urls_to_crawl, search_id=search_query_id)
        
        # 3c. Cache and save fresh docs to DB
        async with AsyncSessionLocal() as session:
            for doc in fresh_docs:
                crawled_documents.append(doc)
                
                # Cache page result for 24 hours
                await set_cached_page(doc.url, doc.model_dump())
                
                # Save crawl info to Postgres
                try:
                    db_crawl = CrawlResult(
                        search_id=search_query_id,
                        url=doc.url,
                        title=doc.title,
                        status_code=doc.status_code,
                        crawl_status=doc.crawl_status,
                        word_count=doc.word_count,
                        extracted_text=doc.text,
                        crawled_at=datetime.utcnow()
                    )
                    session.add(db_crawl)
                except Exception as e:
                    print(f"Failed to queue database save for {doc.url}: {e}")
            try:
                await session.commit()
            except Exception as e:
                print(f"Failed to save crawl results to database: {e}")
                
    # Format and construct return response
    response = SearchResponse(
        query=query,
        total=len(search_results),
        results=search_results[:limit]
    )
    
    return response, crawled_documents, search_query_id
