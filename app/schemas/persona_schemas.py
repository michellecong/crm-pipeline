# schemas/persona_schemas.py
"""
Pydantic schemas for persona generation
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class PersonaTier(str, Enum):
    """Persona tier classification matching database enum"""
    TIER_1 = "tier_1"  # C-level executives with direct budget control
    TIER_2 = "tier_2"  # VPs and directors who influence decisions
    TIER_3 = "tier_3"  # Managers and individual contributors


class PersonaGenerateRequest(BaseModel):
    """Request to generate personas from company data"""
    company_name: str = Field(
        ..., description="Target company name to search and scrape"
    )
    include_news: bool = Field(
        default=True, description="Include news articles"
    )
    include_case_studies: bool = Field(
        default=True, description="Include case studies"
    )
    max_urls: int = Field(
        default=8, description="Maximum URLs to scrape for context"
    )
    max_context_chars: int = Field(
        default=15000, description="Maximum characters for context"
    )
    generate_count: int = Field(
        default=3, description="Number of personas to generate (3-7)"
    )
    pack_id: int = Field(
        default=1, description="Content pack ID to associate personas with"
    )


class Persona(BaseModel):
    """Individual persona structure"""
    name: str
    tier: PersonaTier
    job_title: Optional[str] = None
    industry: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    company_size: Optional[int] = None
    description: Optional[str] = None
    decision_power: Optional[str] = None
    pain_points: List[str] = Field(default=[])
    goals: List[str] = Field(default=[])
    communication_preferences: List[str] = Field(default=[])


class TierClassification(BaseModel):
    """Tier classification structure"""
    tier_1: List[str] = Field(default=[])  # C-level executives
    tier_2: List[str] = Field(default=[])  # VPs and directors
    tier_3: List[str] = Field(default=[])  # Managers and contributors


class PersonaResponse(BaseModel):
    """Enhanced persona generation response"""
    company_name: str
    personas: List[Persona]
    tier_classification: TierClassification
    context_length: int
    generated_at: str
    model: Optional[str] = None
    total_personas: int
