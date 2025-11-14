# schemas/outreach_schemas.py
"""
Pydantic schemas for outreach sequence generation
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
import logging

logger = logging.getLogger(__name__)


class SequenceTouch(BaseModel):
    """Individual touch in a sales outreach sequence"""
    
    sort_order: int = Field(
        ...,
        description="Position in sequence: 1, 2, 3, ...",
        ge=1
    )
    
    touch_type: Literal["email", "linkedin", "phone", "video"] = Field(
        ...,
        description="Communication channel for this touch"
    )
    
    timing_days: int = Field(
        ...,
        description="Days after previous touch (0 for first touch)",
        ge=0
    )
    
    objective: str = Field(
        ...,
        description="Goal of this specific touch",
        min_length=10
    )
    
    subject_line: Optional[str] = Field(
        default=None,
        description="For email/linkedin (max 500 chars), null for phone/video",
        max_length=500
    )
    
    content_suggestion: str = Field(
        ...,
        description="Template/talking points for this touch",
        min_length=20
    )
    
    hints: Optional[str] = Field(
        default=None,
        description="Optional execution hints",
        max_length=500
    )
    
    @field_validator('subject_line')
    @classmethod
    def validate_subject_line(cls, v):
        """Validate subject_line format"""
        # Just validate the subject_line format if provided
        if v is not None and v.strip():
            if len(v) > 60:
                logger.warning(f"subject_line is {len(v)} chars, recommend <60")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "sort_order": 1,
                "touch_type": "email",
                "timing_days": 0,
                "objective": "Introduce pain point around pipeline visibility",
                "subject_line": "Quick insight on your pipeline operations",
                "content_suggestion": "Hi {first_name}, noticed your team is scaling pipeline operations. Our AI tools help revenue leaders like you...",
                "hints": "Reference their LinkedIn post about Q4 results"
            }
        }


class OutreachSequence(BaseModel):
    """Complete outreach sequence for a persona"""
    
    name: str = Field(
        ...,
        description="e.g., 'VP Engineering Outreach Sequence'",
        min_length=10
    )
    
    persona_name: str = Field(
        ...,
        description="Links to which persona this targets",
        min_length=5
    )
    
    objective: str = Field(
        ...,
        description="Overall goal of the sequence",
        min_length=10
    )
    
    total_touches: int = Field(
        ...,
        description="Number of touches (4-6)",
        ge=4,
        le=6
    )
    
    duration_days: int = Field(
        ...,
        description="Total days from first to last touch",
        ge=7
    )
    
    touches: List[SequenceTouch] = Field(
        ...,
        description="Ordered list of touches",
        min_length=4
    )
    
    @field_validator('touches')
    @classmethod
    def validate_touches(cls, v):
        """Validate touches array"""
        if not isinstance(v, list):
            raise ValueError("touches must be an array")
        if len(v) < 4 or len(v) > 6:
            raise ValueError("touches must have 4-6 items")
        
        # Check sort_order is sequential starting from 1
        sort_orders = sorted([touch.get('sort_order') if isinstance(touch, dict) else touch.sort_order for touch in v])
        expected = list(range(1, len(v) + 1))
        if sort_orders != expected:
            raise ValueError(f"sort_order must be sequential: {expected}, got {sort_orders}")
        
        # First touch should have timing_days = 0
        first_touch = v[0]
        first_timing = first_touch.get('timing_days') if isinstance(first_touch, dict) else first_touch.timing_days
        if first_timing != 0:
            raise ValueError("First touch must have timing_days = 0")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "VP Engineering Outreach Sequence",
                "persona_name": "California Mid-Market SaaS - Sales Leaders",
                "objective": "Secure discovery meeting with revenue leaders",
                "total_touches": 5,
                "duration_days": 14,
                "touches": [
                    {
                        "sort_order": 1,
                        "touch_type": "email",
                        "timing_days": 0,
                        "objective": "Introduce pain point around pipeline visibility",
                        "subject_line": "Quick insight on your pipeline operations",
                        "content_suggestion": "Hi {first_name}, noticed your team is scaling...",
                        "hints": None
                    }
                ]
            }
        }


class OutreachGenerateRequest(BaseModel):
    """Request to generate outreach sequences"""
    
    company_name: str = Field(..., description="Company name")
    
    personas_with_mappings: List[dict] = Field(
        ...,
        description="List of personas with their pain point-value proposition mappings",
        min_length=1
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Salesforce",
                "personas_with_mappings": [
                    {
                        "persona_name": "VP Engineering",
                        "job_titles": ["VP Engineering", "Engineering Director", "Director of Engineering"],
                        "excluded_job_titles": ["HR Manager", "IT Support"],
                        "industry": "SaaS",
                        "company_size_range": "200-800 employees",
                        "tier": "tier_1",
                        "mappings": [
                            {
                                "pain_point": "Vendor sprawl management",
                                "value_proposition": "Unified platform consolidates vendors"
                            }
                        ]
                    }
                ]
            }
        }


class OutreachGenerationResponse(BaseModel):
    """Response from outreach sequence generation"""
    
    sequences: List[OutreachSequence] = Field(
        ...,
        description="Generated outreach sequences (1 per persona)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "sequences": [
                    {
                        "name": "VP Engineering Outreach Sequence",
                        "persona_name": "VP Engineering",
                        "objective": "Secure discovery meeting",
                        "total_touches": 5,
                        "duration_days": 14,
                        "touches": []
                    }
                ]
            }
        }

