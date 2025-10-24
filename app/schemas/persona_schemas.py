# schemas/persona_schemas.py
"""
Pydantic schemas for persona generation
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class PersonaTier(str, Enum):
    """Persona tier classification matching database enum"""
    TIER_1 = "tier_1"  # C-level executives with direct budget control
    TIER_2 = "tier_2"  # VPs and directors who influence decisions
    TIER_3 = "tier_3"  # Managers and individual contributors


class CommunicationChannel(BaseModel):
    """Communication channel preference"""
    type: str = Field(..., description="Channel type (e.g., email, phone, linkedin)")
    frequency: str = Field(..., description="Frequency of contact (e.g., weekly, monthly)")
    note: str = Field(default="", description="Additional notes about this channel")

class CommunicationPreferences(BaseModel):
    """Structured communication preferences"""
    channels: List[CommunicationChannel] = Field(default_factory=list)
    content_format: List[str] = Field(default_factory=list, description="Preferred content formats")
    meeting_style: List[str] = Field(default_factory=list, description="Preferred meeting styles")
    response_time: str = Field(default="2-3 business days", description="Expected response time")

class Persona(BaseModel):
    """Individual persona structure matching database schema"""
    # Required fields (Group 1: Company-derived)
    name: str = Field(..., description="Role title or person name")
    tier: PersonaTier = Field(..., description="Decision-making tier")
    job_title: str = Field(..., description="Full job title")
    industry: str = Field(..., description="Company industry")
    department: str = Field(..., description="Department/function")
    location: str = Field(..., description="Geographic location")
    size: Optional[int] = Field(
        default=None, 
        description="Company size (employee count)", 
        alias="company_size"
    )
    
    # Required fields (Group 2: Role-based)
    description: str = Field(..., description="Role description and responsibilities")
    decision_power: str = Field(..., description="Decision-making authority level")
    communication_preferences: CommunicationPreferences = Field(
        ..., 
        description="Structured communication preferences"
    )
    
    # Optional fields (Group 3: Evidence-based)
    pain_points: Optional[List[str]] = Field(
        default=None, 
        description="Evidence-based pain points (null if no evidence in data)"
    )
    
    # Optional fields (Group 4: Contact information)
    email: Optional[str] = Field(default=None, description="Email address if available")
    phone: Optional[str] = Field(default=None, description="Phone number if available")
    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn profile URL if available")
    
    class Config:
        populate_by_name = True  # Allow both 'size' and 'company_size'
        json_schema_extra = {
            "example": {
                "name": "Chief Financial Officer",
                "tier": "tier_1",
                "job_title": "Chief Financial Officer (CFO)",
                "industry": "Technology",
                "department": "Finance",
                "location": "San Francisco, CA",
                "size": 70000,
                "description": "Senior executive responsible for financial strategy...",
                "decision_power": "budget_owner",
                "communication_preferences": {
                    "channels": [
                        {"type": "email", "frequency": "bi-weekly", "note": "Prefers executive summaries"}
                    ],
                    "content_format": ["Executive summary", "ROI analysis"],
                    "meeting_style": ["30-min video calls"],
                    "response_time": "3-5 business days"
                },
                "pain_points": ["Vendor sprawl management", "ROI measurement"],
                "email": None,
                "phone": None,
                "linkedin_url": None
            }
        }
    
    @field_validator('size', mode='before')
    @classmethod
    def validate_size(cls, v):
        """Handle None or invalid size values"""
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None
    
    
    @field_validator('communication_preferences', mode='before')
    @classmethod
    def validate_communication_preferences(cls, v):
        """Convert list to proper object structure if needed"""
        logger.debug(f"communication_preferences validator input: {v}")
        
        if isinstance(v, list):
            # If it's a list (old format), convert to new structure
            result = {
                "channels": [],
                "content_format": v if v else [],
                "meeting_style": [],
                "response_time": "2-3 business days"
            }
            logger.debug(f"communication_preferences validator output (list): {result}")
            return result
        elif isinstance(v, dict):
            # If it's already a dict, preserve existing values and only add missing defaults
            defaults = {
                "channels": [],
                "content_format": [],
                "meeting_style": [],
                "response_time": "2-3 business days"
            }
            # Only add defaults for missing keys, preserve existing values
            result = {**defaults, **v}
            logger.debug(f"communication_preferences validator output (dict): {result}")
            return result
        elif v is None or v == "":
            # Handle null/empty
            result = {
                "channels": [],
                "content_format": [],
                "meeting_style": [],
                "response_time": "2-3 business days"
            }
            logger.debug(f"communication_preferences validator output (null): {result}")
            return result
        
        logger.debug(f"communication_preferences validator output (unchanged): {v}")
        return v
    
    @field_validator('pain_points', mode='before')
    @classmethod
    def validate_pain_points(cls, v):
        """Convert empty list to None"""
        if v == [] or v == "":
            return None
        return v

class CompanyInfo(BaseModel):
    """Company information structure"""
    name: str
    size: int
    industry: str
    location: str
    domain: str

class TierClassification(BaseModel):
    """Tier classification structure with auto-conversion"""
    tier_1: List[str] = Field(default_factory=list, description="C-level persona indices")
    tier_2: List[str] = Field(default_factory=list, description="VP/Director persona indices")
    tier_3: List[str] = Field(default_factory=list, description="Manager/IC persona indices")
    
    @field_validator('tier_1', 'tier_2', 'tier_3', mode='before')
    @classmethod
    def convert_to_strings(cls, v):
        """Convert integer indices to string indices"""
        if isinstance(v, list):
            return [str(item) for item in v]
        return v if v is not None else []
    
    class Config:
        json_schema_extra = {
            "example": {
                "tier_1": ["0"],
                "tier_2": ["1"],
                "tier_3": ["2"]
            }
        }

class PersonaGenerateRequest(BaseModel):
    """Request to generate personas from company data"""
    company_name: str = Field(..., description="Target company name to search and scrape")
    generate_count: int = Field(default=3, description="Number of personas to generate", ge=1, le=7)
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Salesforce",
                "generate_count": 3
            }
        }

class PersonaResponse(BaseModel):
    """Enhanced persona generation response"""
    company_name: str
    company: CompanyInfo
    personas: List[Persona]
    tier_classification: TierClassification
    context_length: int
    generated_at: str
    total_personas: int
    model: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Salesforce",
                "company": {
                    "name": "Salesforce",
                    "size": 70000,
                    "industry": "Technology",
                    "location": "San Francisco, CA",
                    "domain": "SaaS"
                },
                "personas": [
                    {
                        "name": "Chief Financial Officer",
                        "tier": "tier_1",
                        "job_title": "CFO",
                        "industry": "Technology",
                        "department": "Finance",
                        "location": "San Francisco, CA",
                        "size": 70000,
                        "description": "Responsible for financial strategy...",
                        "decision_power": "budget_owner",
                        "communication_preferences": {
                            "channels": [{"type": "email", "frequency": "weekly", "note": ""}],
                            "content_format": ["Executive summary"],
                            "meeting_style": ["Video calls"],
                            "response_time": "3-5 days"
                        },
                        "pain_points": None,
                        "email": None,
                        "phone": None,
                        "linkedin_url": None
                    }
                ],
                "tier_classification": {
                    "tier_1": ["0"],
                    "tier_2": [],
                    "tier_3": []
                },
                "context_length": 1500,
                "generated_at": "2025-10-23T12:00:00",
                "total_personas": 1,
                "model": "gpt-4"
            }
        }


class PersonaCreate(BaseModel):
    """Schema for creating persona in database"""
    pack_id: int
    name: str
    tier: PersonaTier
    job_title: str
    industry: str
    department: str
    location: str
    size: int
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: str
    decision_power: str
    pain_points: Optional[List[str]] = None
    communication_preferences: Dict[str, Any]  # JSONB in database

class PersonaDB(PersonaCreate):
    """Schema for persona from database (includes auto-generated fields)"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True  # Pydantic V2 (was orm_mode in V1)