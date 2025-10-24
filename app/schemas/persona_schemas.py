# schemas/persona_schemas.py
"""
Pydantic schemas for persona generation
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class PersonaTier(str, Enum):
    """Persona tier classification matching database enum"""
    TIER_1 = "tier_1"  # C-level executives with direct budget control
    TIER_2 = "tier_2"  # VPs and directors who influence decisions
    TIER_3 = "tier_3"  # Managers and individual contributors

class PersonaGenerateRequest(BaseModel):
    """Request to generate personas from company data"""
    company_name: str = Field(..., description="Target company name to search and scrape")
    generate_count: int = Field(default=3, description="Number of personas to generate (3-7)")

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
    pain_points: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    communication_preferences: List[str] = Field(default_factory=list)

class TierClassification(BaseModel):
    """Tier classification structure"""
    tier_1: List[str] = Field(default_factory=list)  # C-level executives
    tier_2: List[str] = Field(default_factory=list)  # VPs and directors
    tier_3: List[str] = Field(default_factory=list)  # Managers and contributors

class PersonaResponse(BaseModel):
    """Persona generation response"""
    company_name: str
    personas: List[Persona]
    tier_classification: TierClassification
    context_length: int
    generated_at: str
    total_personas: int
    model: Optional[str] = None
