from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Literal
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
    
    job_titles: List[str] = Field(
        ...,
        description="Array of target job titles (10-30+ variations)",
        min_length=5
    )
    
    excluded_job_titles: List[str] = Field(
        ...,
        description="Array of job titles to avoid (3-10+ roles not relevant to this persona)",
        min_length=1
    )
    
    industry: str = Field(..., description="Industry vertical")
    company_size_range: str = Field(..., description="Employee range")
    company_type: str = Field(..., description="Detailed categorization")
    location: str = Field(..., description="US state/region")
    description: str = Field(..., description="3-4 sentences", min_length=100)
    
    @field_validator('job_titles')
    @classmethod
    def validate_job_titles_array(cls, v):
        if not isinstance(v, list):
            raise ValueError("job_titles must be an array")
        if len(v) == 0:
            raise ValueError("job_titles cannot be empty")
        for title in v:
            if not isinstance(title, str):
                raise ValueError(f"All job titles must be strings, got {type(title)}")
        if len(v) < 10:
            logger.warning(f"Only {len(v)} job titles. Recommend 10-30+ for better coverage")
        return v
    
    @field_validator('excluded_job_titles')
    @classmethod
    def validate_excluded_titles_array(cls, v):
        if not isinstance(v, list):
            raise ValueError("excluded_job_titles must be an array")
        for title in v:
            if not isinstance(title, str):
                raise ValueError(f"All excluded titles must be strings, got {type(title)}")
        if len(v) < 3:
            logger.warning(f"Only {len(v)} excluded titles. Recommend 3-10+ for better lead qualification")
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
                "job_titles": ["CRO", "VP of Sales", "VP Sales", "Chief Revenue Officer", "Sales Director"],
                "excluded_job_titles": ["HR Manager", "IT Director", "Customer Support Manager"],
                "industry": "SaaS & Cloud Software",
                "company_size_range": "200-800 employees",
                "company_type": "B2B SaaS companies",
                "location": "California",
                "description": "High-growth SaaS companies..."
            }
        }


class DataSources(BaseModel):
    """Data sources used in persona generation"""
    
    crm_data_used: bool = Field(..., description="Whether CRM data was used in generation")
    crm_data_influence: str = Field(
        ..., 
        description="Explanation of how CRM data influenced specific persona fields (e.g., location, industry, job_titles). If CRM data was not used, explain why."
    )
    source_url: Optional[str] = Field(
        default=None,
        description=(
            "Primary web content source URL used for generating personas "
            "(e.g., official website, case study, or news article)"
        )
    )


class PersonaGenerationResponse(BaseModel):
    """Response from persona generation"""
    
    personas: List[BuyerPersona] = Field(..., description="Generated personas")
    generation_reasoning: str = Field(
        ..., 
        description="Explanation of persona selections, including whether CRM data was used and how it influenced the generation"
    )
    data_sources: DataSources = Field(..., description="Data sources used and their influence on generation")
    
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
                    "job_titles": ["CRO", "VP Sales", "Chief Revenue Officer"],
                    "excluded_job_titles": ["HR Manager", "IT Director"],
                    "industry": "SaaS",
                    "company_size_range": "200-800 employees",
                    "company_type": "B2B SaaS",
                    "location": "California",
                    "description": "..."
                }],
                "generation_reasoning": "Selected personas based on web content analysis and CRM data insights. CRM data showed 70% of customers in California, which informed the location field.",
                "data_sources": {
                    "crm_data_used": True,
                    "crm_data_influence": "Location 'California' based on CRM data showing 70% of accounts in CA. Industry 'SaaS' matches top industry (45% of CRM accounts). Job titles include 'CRO' and 'VP Sales' which are top titles in CRM contact data.",
                    "source_url": "https://www.example.com/about"
                }
            }
        }


class PersonaGenerateRequest(BaseModel):
    """Request to generate buyer personas"""
    
    company_name: str = Field(..., description="Company name to analyze")
    generate_count: int = Field(default=5, ge=3, le=12)
    products: Optional[List[Dict]] = Field(
        default=None,
        description="Optional product catalog to inform persona generation. If not provided, personas will be generated from web content only."
    )
    # Optional search behavior controls (used to collect web content when needed)
    use_llm_search: Optional[bool] = Field(
        default=None,
        description="Use LLM-planned web search; if False, use selected provider. If omitted, system default is used."
    )
    provider: Optional[Literal["google", "perplexity"]] = Field(
        default=None,
        description="Search provider when not using LLM search (e.g., 'google' or 'perplexity')"
    )
    
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
    job_titles: List[str]
    excluded_job_titles: List[str]
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
    job_titles: List[str]
    excluded_job_titles: List[str]
    industry: str
    company_size_range: str
    company_type: str
    location: str
    description: str
    created_at: datetime
    
    @field_validator('job_titles', mode='before')
    @classmethod
    def parse_job_titles_from_db(cls, v):
        """Parse from JSON string if needed"""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [t.strip() for t in v.split(',')]
        return v
    
    @field_validator('excluded_job_titles', mode='before')
    @classmethod
    def parse_excluded_titles_from_db(cls, v):
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