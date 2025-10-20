# schemas/search.py
"""
Pydantic schemas for search operations
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class SearchRequest(BaseModel):
    company_name: str = Field(..., description="Company name to search for", example="Salesforce")
    include_news: bool = Field(default=True, description="Include news articles in search")
    include_case_studies: bool = Field(default=True, description="Include case studies in search")
    provider: Literal["google", "perplexity"] = Field(default="google", description="Search provider to use")


class SearchResultItem(BaseModel):
    title: str
    url: str  
    snippet: str


class SearchResponse(BaseModel):
    company_name: str
    official_website: Optional[str] = None
    news_articles: List[SearchResultItem] = []
    case_studies: List[SearchResultItem] = []
    total_results: int
    search_timestamp: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


    

