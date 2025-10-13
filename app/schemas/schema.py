# models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SearchRequest(BaseModel):
    company_name: str = Field(..., description="Company name to search for", example="Salesforce")
    include_news: bool = Field(default=True, description="Include news articles in search")
    include_case_studies: bool = Field(default=True, description="Include case studies in search")

class SearchResultItem(BaseModel):
    title: str
    url: str  
    snippet: str
    display_link: Optional[str] = None
    type: str  # 'news', 'case_study', 'official', 'other'

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

class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())