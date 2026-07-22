import time
import asyncio
from typing import List, Dict, Any, Tuple
from datetime import datetime
from backend.search.models import SearchResult, SearchResponse
from backend.crawler.models import CrawledDocument
from backend.services.searxng import search_searxng
from backend.search.normalizer import normalize_url
from backend.search.deduplicator import deduplicate_results
from backend.search.ranker import rank_search_results, get_source_type
from backend.search.query_decomposer import extract_product_constraints, generate_targeted_product_queries
from backend.crawler.crawler import crawl_urls_concurrently, crawl_url
from backend.database.redis import get_cached_search, set_cached_search, get_cached_page, set_cached_page
from backend.database.postgres import AsyncSessionLocal
from backend.database.models import SearchQuery, CrawlResult

async def run_search_crawl_pipeline(
    query: str, 
    limit: int = 10, 
    max_crawl_sources: int = 6,
    intent: str = "web_search"
) -> Tuple[SearchResponse, List[CrawledDocument], int, List[Dict[str, Any]]]:
    """
    Executes Intent-Aware Search -> Rerank -> Scrape -> Diagnostics pipeline:
    1. Extracts query constraints (e.g. category, budget) & generates multi-search subqueries for product queries.
    2. Executes SearXNG searches, deduplicates URLs, and performs Intent-Aware Pre-Crawl Reranking.
    3. Selects top N candidate URLs with domain diversity capping (max 2 per domain) to crawl.
    4. Scrapes selected candidates, filters out failed scrapes, and computes retrieval diagnostic metadata.
    """
    start_time = time.time()
    normalized_query = query.lower().strip()
    
    # --- STEP 1: Search Discovery & Subquery Generation ---
    cached_results = await get_cached_search(normalized_query)
    
    if cached_results:
        print(f"Search cache hit for query: '{query}'")
        search_results = [SearchResult(**item) for item in cached_results]
    else:
        print(f"Search cache miss. Running intent-aware discovery for: '{query}' (intent: {intent})")
        constraints = extract_product_constraints(query)
        
        # Override intent to 'product' if product constraints detected
        if constraints.get("is_product_query"):
            intent = "product"
            
        subqueries = generate_targeted_product_queries(query, constraints) if constraints.get("is_product_query") else [query]
        
        raw_results = []
        for sq in subqueries:
            sq_results = await search_searxng(sq, limit=20)
            raw_results.extend(sq_results)
            
        # Normalize and Deduplicate
        unique_results = deduplicate_results(raw_results)
        
        # Intent-Aware Pre-Crawl Reranking with Domain Diversity Capping
        search_results = rank_search_results(unique_results, query, intent=intent)
        
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

    # --- STEP 3: Source Selection & Pre-Crawl Diagnostic Metadata ---
    top_candidate_sources = search_results[:max_crawl_sources]
    crawled_documents = []
    urls_to_crawl = []
    
    # 3a. Check page cache first
    for source in top_candidate_sources:
        cached_doc = await get_cached_page(source.url)
        if cached_doc:
            print(f"Page cache hit for URL: {source.url}")
            crawled_documents.append(CrawledDocument(**cached_doc))
        else:
            urls_to_crawl.append(source.url)

    # 3b. Crawl cache misses concurrently
    if urls_to_crawl:
        print(f"Crawling {len(urls_to_crawl)} top candidate URLs concurrently...")
        fresh_docs = await crawl_urls_concurrently(urls_to_crawl, search_id=search_query_id)
        
        # 3c. Cache and save fresh docs to DB
        async with AsyncSessionLocal() as session:
            for doc in fresh_docs:
                crawled_documents.append(doc)
                await set_cached_page(doc.url, doc.model_dump())
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

    # --- STEP 4: Retrieval Diagnostic Metadata Generation ---
    diagnostics = []
    crawled_by_url = {doc.url: doc for doc in crawled_documents}

    for rank, item in enumerate(search_results[:12], start=1):
        domain = item.url.split("//")[-1].split("/")[0].lower().replace("www.", "")
        doc = crawled_by_url.get(item.url)
        
        is_selected = item in top_candidate_sources
        quality_score = 0.0
        if doc and doc.crawl_status == "SUCCESS":
            # Quality score based on text length and structure
            if doc.word_count >= 200:
                quality_score = 0.90
            elif doc.word_count >= 80:
                quality_score = 0.70
            elif doc.word_count >= 30:
                quality_score = 0.50
            else:
                quality_score = 0.20
        elif doc and doc.crawl_status != "SUCCESS":
            quality_score = 0.0

        final_score = round((0.60 * item.score) + (0.40 * quality_score), 4)

        diagnostics.append({
            "source_url": item.url,
            "domain": domain,
            "source_type": get_source_type(domain),
            "search_query": query,
            "search_rank": rank,
            "pre_crawl_score": item.score,
            "post_crawl_score": final_score,
            "semantic_score": item.score,
            "quality_score": quality_score,
            "retrieved_at": datetime.utcnow().isoformat(),
            "citation_ids": [rank] if (is_selected and quality_score > 0) else [],
            "selected": is_selected and (quality_score > 0)
        })

    response = SearchResponse(
        query=query,
        total=len(search_results),
        results=search_results[:limit]
    )

    return response, crawled_documents, search_query_id, diagnostics
