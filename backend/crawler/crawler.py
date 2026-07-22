import asyncio
from typing import List, Optional
import httpx
from backend.core.config import settings
from backend.crawler.models import CrawledDocument
from backend.crawler.validator import is_safe_url
from backend.crawler.robots import check_crawling_permission
from backend.crawler.extractor import extract_clean_content

USER_AGENT = "IntelliSearchBot/1.0 (+http://localhost:3000/bot)"

async def crawl_url(url: str, search_id: Optional[int] = None) -> CrawledDocument:
    """
    Crawls a single URL asynchronously with safety checks:
    - SSRF URL validation
    - robots.txt permissions validation
    - Redirect limits, size guards (max 2MB), and Content-Type validation
    - HTML main text content parsing and clean formatting
    """
    # 1. SSRF Safety Verification
    if not is_safe_url(url):
        return CrawledDocument(
            url=url,
            crawl_status="BLOCKED",
            error_message="Blocked: SSRF safety check failed (invalid or private target IP address)"
        )
        
    # 2. robots.txt Check
    is_allowed = await check_crawling_permission(url, USER_AGENT)
    if not is_allowed:
        return CrawledDocument(
            url=url,
            crawl_status="BLOCKED",
            error_message="Blocked: Crawler restricted by website robots.txt rules"
        )
        
    # 3. Fetch URL Content
    try:
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        async with httpx.AsyncClient(limits=limits, follow_redirects=True, max_redirects=3, timeout=settings.TIMEOUT_CRAWLER) as client:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            # Start streaming request to check size and content-type before full download
            async with client.stream("GET", url, headers=headers) as response:
                status_code = response.status_code
                
                # Check HTTP error status
                if response.status_code >= 400:
                    return CrawledDocument(
                        url=url,
                        status_code=status_code,
                        crawl_status="HTTP_ERROR",
                        error_message=f"HTTP request failed with status: {status_code}"
                    )
                    
                # Validate Content-Type
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    return CrawledDocument(
                        url=url,
                        status_code=status_code,
                        crawl_status="UNSUPPORTED_CONTENT",
                        error_message=f"Unsupported content type: {content_type}"
                    )
                    
                # Enforce Size Guard (Max 2MB)
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > 2 * 1024 * 1024:
                    return CrawledDocument(
                        url=url,
                        status_code=status_code,
                        crawl_status="BLOCKED",
                        error_message="Blocked: Content body size exceeds 2MB limit"
                    )
                    
                # Read chunks to enforce size limit dynamically during streaming
                chunks = []
                bytes_downloaded = 0
                async for chunk in response.aiter_text():
                    bytes_downloaded += len(chunk.encode('utf-8'))
                    if bytes_downloaded > 2 * 1024 * 1024:
                        return CrawledDocument(
                            url=url,
                            status_code=status_code,
                            crawl_status="BLOCKED",
                            error_message="Blocked: Content body size exceeded 2MB limit during stream"
                        )
                    chunks.append(chunk)
                    
                html_content = "".join(chunks)
                
        # 4. Extract Text Content
        extracted = extract_clean_content(html_content)
        if not extracted["success"]:
            return CrawledDocument(
                url=url,
                status_code=status_code,
                crawl_status="EXTRACTION_FAILED",
                error_message=f"HTML parsing failed: {extracted['error']}"
            )
            
        text = extracted["text"]
        word_count = extracted["word_count"]
        
        # 5. Quality Checks
        if word_count == 0:
            crawl_status = "EMPTY"
        elif word_count < 30:
            crawl_status = "TOO_SHORT"
        else:
            crawl_status = "SUCCESS"
            
        return CrawledDocument(
            url=url,
            title=extracted["title"],
            description=extracted["description"],
            text=text,
            word_count=word_count,
            status_code=status_code,
            crawl_status=crawl_status
        )
        
    except httpx.ConnectTimeout:
        return CrawledDocument(url=url, crawl_status="TIMEOUT", error_message="Request failed: connection timed out")
    except httpx.ReadTimeout:
        return CrawledDocument(url=url, crawl_status="TIMEOUT", error_message="Request failed: read timed out")
    except httpx.ConnectError as e:
        return CrawledDocument(url=url, crawl_status="HTTP_ERROR", error_message=f"Failed to connect to host: {e}")
    except httpx.HTTPStatusError as e:
        return CrawledDocument(url=url, crawl_status="HTTP_ERROR", error_message=f"HTTP status error: {e}")
    except Exception as e:
        return CrawledDocument(url=url, crawl_status="EXTRACTION_FAILED", error_message=f"An unexpected error occurred during crawl: {e}")

async def crawl_urls_concurrently(urls: List[str], search_id: Optional[int] = None) -> List[CrawledDocument]:
    """
    Crawls multiple URLs concurrently using asyncio.gather.
    """
    tasks = [crawl_url(url, search_id) for url in urls]
    return await asyncio.gather(*tasks)
