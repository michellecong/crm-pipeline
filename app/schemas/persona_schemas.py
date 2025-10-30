from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PersonaTier(str, Enum):
    """Persona tier classification based on strategic priority"""
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


class BuyerPersona(BaseModel):
    """
    Buyer company persona (market segment archetype).
    
    Represents a TYPE of buyer company, not a specific individual.
    """
    
    persona_name: str = Field(
        ..., 
        description="Format: [Geography] [Size] [Industry] - [Function]",
        min_length=10
    )
    
    tier: PersonaTier = Field(
        ..., 
        description="Strategic priority tier"
    )
    
    target_decision_makers: List[str] = Field(
        ...,
        description="Array of job titles (10-30+ variations)",
        min_length=5
    )
    
    industry: str = Field(..., description="Industry vertical")
    company_size_range: str = Field(..., description="Employee range")
    company_type: str = Field(..., description="Detailed categorization")
    location: str = Field(..., description="US state/region")
    description: str = Field(..., description="3-4 sentences", min_length=100)
    
    @field_validator('target_decision_makers')
    @classmethod
    def validate_titles_array(cls, v):
        if not isinstance(v, list):
            raise ValueError("target_decision_makers must be an array")
        if len(v) == 0:
            raise ValueError("target_decision_makers cannot be empty")
        for title in v:
            if not isinstance(title, str):
                raise ValueError(f"All titles must be strings, got {type(title)}")
        if len(v) < 5:
            logger.warning(f"Only {len(v)} titles. Recommend 10-30+")
        return v
    
    @field_validator('persona_name')
    @classmethod
    def validate_persona_name(cls, v):
        if not v or len(v) < 10:
            raise ValueError("persona_name must be at least 10 characters")
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if not v or len(v) < 100:
            raise ValueError("description must be at least 100 characters")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "persona_name": "California Mid-Market SaaS - Sales Leaders",
                "tier": "tier_1",
                "target_decision_makers": ["CRO", "VP of Sales", "VP Sales"],
                "industry": "SaaS & Cloud Software",
                "company_size_range": "200-800 employees",
                "company_type": "B2B SaaS companies",
                "location": "California",
                "description": "High-growth SaaS companies..."
            }
        }


class PersonaGenerationResponse(BaseModel):
    """Response from persona generation"""
    
    personas: List[BuyerPersona] = Field(..., description="Generated personas")
    generation_reasoning: str = Field(..., description="Explanation of selections")
    
    @field_validator('personas')
    @classmethod
    def validate_personas_list(cls, v):
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("personas must be a non-empty array")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "personas": [{
                    "persona_name": "California Mid-Market SaaS - Sales Leaders",
                    "tier": "tier_1",
                    "target_decision_makers": ["CRO", "VP Sales"],
                    "industry": "SaaS",
                    "company_size_range": "200-800 employees",
                    "company_type": "B2B SaaS",
                    "location": "California",
                    "description": "..."
                }],
                "generation_reasoning": "..."
            }
        }


class PersonaGenerateRequest(BaseModel):
    """Request to generate buyer personas"""
    
    company_name: str = Field(..., description="Company name to analyze")
    generate_count: int = Field(default=5, ge=3, le=12)
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Salesforce",
                "generate_count": 5
            }
        }


class PersonaCreate(BaseModel):
    """Schema for creating persona in database"""
    
    pack_id: int
    persona_name: str
    tier: PersonaTier
    target_decision_makers: List[str]
    industry: str
    company_size_range: str
    company_type: str
    location: str
    description: str


class PersonaDB(BaseModel):
    """Schema for persona from database"""
    
    id: int
    pack_id: int
    persona_name: str
    tier: PersonaTier
    target_decision_makers: List[str]
    industry: str
    company_size_range: str
    company_type: str
    location: str
    description: str
    created_at: datetime
    
    @field_validator('target_decision_makers', mode='before')
    @classmethod
    def parse_titles_from_db(cls, v):
        """Parse from JSON string if needed"""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [t.strip() for t in v.split(',')]
        return v
    
    class Config:
        from_attributes = True