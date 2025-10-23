"""
Pydantic schemas for LLM operations
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


class PersonaTier(str, Enum):
    """Persona tier classification"""
    TIER_1 = "tier_1"  # C-level executives with direct budget control
    TIER_2 = "tier_2"  # VPs and directors who influence decisions
    TIER_3 = "tier_3"  # Managers and individual contributors


class LLMGenerateRequest(BaseModel):
    """Request to generate text from LLM"""
    prompt: str = Field(
        ..., 
        description="The main prompt/question to send to the LLM",
        json_schema_extra={"example": "Explain the benefits of CRM systems in 3 sentences"}
    )
    system_message: Optional[str] = Field(
        default=None,
        description="System message to set LLM behavior/context",
        json_schema_extra={"example": "You are a helpful assistant specializing in B2B sales."}
    )
    temperature: Optional[float] = Field(
        default=1.0,
        description="Temperature for GPT-5 models is fixed at 1.0 (cannot be modified)"
    )
    max_completion_tokens: Optional[int] = Field(
        default=8000,
        ge=1,
        le=8000,
        description="Maximum tokens in response (increased for comprehensive persona generation)"
    )


class TokenUsage(BaseModel):
    """Token usage information"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMGenerateResponse(BaseModel):
    """Response from LLM generation"""
    content: str = Field(..., description="Generated text content")
    model: str = Field(..., description="Model that generated the response")
    finish_reason: str = Field(..., description="Why generation stopped")
    usage: TokenUsage


class LLMConfigResponse(BaseModel):
    """Current LLM service configuration"""
    model: str
    temperature: float
    max_completion_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float


class LLMConfigUpdateRequest(BaseModel):
    """Update LLM configuration"""
    model: Optional[str] = None
    temperature: Optional[float] = Field(
        None, 
        description="Temperature for GPT-5 models is fixed at 1.0 (cannot be modified)"
    )
    max_completion_tokens: Optional[int] = Field(None, ge=1, le=8000)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)


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
    tier_3: List[str] = Field(default_factory=list)  # Managers and individual contributors


class PersonaGenerateRequest(BaseModel):
    """Request to generate persona from company data"""
    company_name: str = Field(..., description="Target company name to search and scrape")
    generate_count: int = Field(default=3, description="Number of personas to generate (3-7)")


class PersonaResponse(BaseModel):
    """Persona generation response"""
    company_name: str
    personas: List[Persona]
    tier_classification: TierClassification
    context_length: int
    generated_at: str
    total_personas: int
    model: Optional[str] = None

