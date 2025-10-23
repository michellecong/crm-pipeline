# schemas/__init__.py
"""
Pydantic schemas for API requests and responses
"""
from .search import SearchRequest, SearchResultItem, SearchResponse
from .scraping import ScrapeRequest, ScrapedContent, ScrapeResponse
from .common import ErrorResponse, HealthResponse
from .persona_schemas import PersonaGenerateRequest, PersonaResponse, Persona, TierClassification

__all__ = [
    # Search
    "SearchRequest",
    "SearchResultItem", 
    "SearchResponse",
    # Scraping
    "ScrapeRequest",
    "ScrapedContent",
    "ScrapeResponse",
    # Common
    "ErrorResponse",
    "HealthResponse",
    # Persona
    "PersonaGenerateRequest",
    "PersonaResponse",
    "Persona",
    "TierClassification",
]
