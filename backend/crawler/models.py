from pydantic import BaseModel, Field
from typing import Optional

class CrawlRequest(BaseModel):
    url: str = Field(..., description="The URL of the webpage to crawl")

class CrawledDocument(BaseModel):
    url: str = Field(..., description="The original URL of the webpage")
    title: Optional[str] = Field(None, description="The extracted page title")
    description: Optional[str] = Field(None, description="The extracted meta description of the page")
    text: Optional[str] = Field(None, description="The extracted clean plain text of the page")
    word_count: int = Field(default=0, description="Total word count of the extracted text")
    status_code: Optional[int] = Field(None, description="The HTTP response status code")
    crawl_status: str = Field(..., description="Crawl job status: SUCCESS, EMPTY, TOO_SHORT, BLOCKED, UNSUPPORTED_CONTENT, TIMEOUT, HTTP_ERROR, EXTRACTION_FAILED")
    error_message: Optional[str] = Field(None, description="Error details if the crawl failed")
