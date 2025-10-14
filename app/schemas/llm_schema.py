"""
Pydantic schemas for LLM operations
"""
from pydantic import BaseModel, Field
from typing import Optional


class LLMGenerateRequest(BaseModel):
    """Request to generate text from LLM"""
    prompt: str = Field(
        ..., 
        description="The main prompt/question to send to the LLM",
        example="Explain the benefits of CRM systems in 3 sentences"
    )
    system_message: Optional[str] = Field(
        default=None,
        description="System message to set LLM behavior/context",
        example="You are a helpful assistant specializing in B2B sales."
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Controls randomness (0=deterministic, 2=very random)"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=4000,
        description="Maximum tokens in response"
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
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float


class LLMConfigUpdateRequest(BaseModel):
    """Update LLM configuration"""
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4000)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)

