# schemas/evaluation_schemas.py
"""
Schemas for persona evaluation responses
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class PersonaEvaluationRequest(BaseModel):
    """Request for persona evaluation"""
    personas: List[Dict] = Field(..., description="List of persona dictionaries to evaluate")
    company_name: Optional[str] = Field(None, description="Company name (for context)")


class DiversityMetrics(BaseModel):
    """Semantic diversity metrics"""
    average_cosine_similarity: Optional[float] = None
    average_cosine_distance: Optional[float] = None
    min_cosine_distance: Optional[float] = None
    max_cosine_similarity: Optional[float] = None
    std_cosine_distance: Optional[float] = None
    diversity_score: Optional[float] = Field(None, description="0-1 score, higher = more diverse")
    interpretation: Optional[str] = None


class IndustryDiversity(BaseModel):
    """Industry diversity metrics"""
    unique_industries: int
    total_personas: int
    industry_diversity_score: float
    industry_distribution: Dict[str, int]
    recommendation: str


class GeographicDiversity(BaseModel):
    """Geographic diversity metrics"""
    unique_locations: int
    total_personas: int
    geographic_diversity_score: float
    location_distribution: Dict[str, int]


class SizeDiversity(BaseModel):
    """Company size diversity metrics"""
    unique_size_ranges: int
    total_personas: int
    size_diversity_score: float
    size_distribution: Dict[str, int]


class TierDistribution(BaseModel):
    """Tier distribution metrics"""
    tier_distribution: Dict[str, int]
    tier_percentages: Dict[str, float]
    is_balanced: bool
    recommendation: str


class Completeness(BaseModel):
    """Field completeness metrics"""
    average_completeness: float
    completeness_scores: List[float]
    all_complete: bool


class PersonaEvaluationResponse(BaseModel):
    """Response from persona evaluation"""
    persona_count: int
    overall_score: float = Field(..., description="Overall quality score (0-1)")
    semantic_diversity: DiversityMetrics
    industry_diversity: IndustryDiversity
    geographic_diversity: GeographicDiversity
    size_diversity: SizeDiversity
    tier_distribution: TierDistribution
    completeness: Completeness
    recommendations: List[str]
    
    class Config:
        # Allow None values in nested models
        extra = "allow"

