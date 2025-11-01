# schemas/search.py
"""
Pydantic schemas for search operations
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime


class SearchRequest(BaseModel):
    company_name: str = Field(
        ...,
        description="Company name to search for",
        json_schema_extra={"example": "Salesforce"}
    )
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
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class LLMCompanyWebSearchRequest(BaseModel):
    company_name: str = Field(
        ..., description="Target B2B seller company name", json_schema_extra={"example": "Salesforce"}
    )


class LLMCompanyWebItem(BaseModel):
    url: str
    title: Optional[str] = None


class LLMCompanyWebNewsItem(BaseModel):
    url: str
    title: Optional[str] = None
    published_at: Optional[str] = None


class LLMCompanyWebSearchResponse(BaseModel):
    company: str
    queries_planned: List[str] = []
    official_website: List[LLMCompanyWebItem] = []
    news: List[LLMCompanyWebNewsItem] = []
    case_studies: List[LLMCompanyWebItem] = []
    collected_at: Optional[str] = None


class LLMWebSearchResponse(BaseModel):
    result: str = Field(description="Freeform LLM output with planned queries and URLs")


