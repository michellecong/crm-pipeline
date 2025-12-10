# schemas/scraping.py
"""
Pydantic schemas for scraping operations
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal


class ScrapeRequest(BaseModel):
    """Request to scrape company data"""
    company_name: str = Field(..., description="Target company name")
    include_news: bool = Field(default=True, description="Include news articles")
    include_case_studies: bool = Field(default=True, description="Include case studies")
    max_urls: int = Field(default=10, description="Maximum URLs to scrape")
    save_to_file: bool = Field(default=False, description="If True, save to file only (skip database)")
    provider: Literal["google", "perplexity"] = Field(default="google", description="Search provider (google or perplexity)")


class ScrapedContent(BaseModel):
    """Scraped content from a single URL"""
    url: str
    title: Optional[str] = None
    markdown: str = Field(..., description="Content in markdown format")
    html: Optional[str] = None
    metadata: Dict = Field(default={})
    content_type: str = Field(..., description="website, product, news, or case_study")
    success: bool
    error: Optional[str] = None
    scraped_at: str


class ScrapeResponse(BaseModel):
    """Response with all scraped data"""
    company_name: str
    official_website: Optional[str] = None
    total_urls_found: int
    total_urls_scraped: int
    successful_scrapes: int
    scraped_content: List[ScrapedContent]
    search_results_summary: Dict
    scraping_timestamp: str
    saved_filepath: Optional[str] = None

