# schemas/three_stage_schemas.py
"""
Pydantic schemas for three-stage pipeline generation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from .product_schemas import Product
from .persona_schemas import BuyerPersona
from .mapping_schemas import PersonaWithMappings
from .outreach_schemas import OutreachSequence
from .pipeline_schemas import PipelineArtifacts


class ThreeStageGenerateRequest(BaseModel):
    """Request for three-stage pipeline generation"""
    
    company_name: str = Field(
        ..., 
        description="Company name to analyze",
        min_length=2
    )
    generate_count: int = Field(
        default=5, 
        ge=3, 
        le=12, 
        description="Number of personas to generate"
    )
    use_llm_search: Optional[bool] = Field(
        default=None,
        description="Use LLM-planned web search"
    )
    provider: Optional[Literal["google", "perplexity"]] = Field(
        default=None,
        description="Search provider"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Salesforce",
                "generate_count": 5,
                "use_llm_search": True,
                "provider": "google"
            }
        }


class ThreeStageStatistics(BaseModel):
    """Statistics for three-stage execution"""
    total_runtime_seconds: float = Field(..., description="Total three-stage execution time in seconds")
    stage1_runtime_seconds: float = Field(..., description="Stage 1 (products) execution time")
    stage2_runtime_seconds: float = Field(..., description="Stage 2 (personas) execution time")
    stage3_runtime_seconds: float = Field(..., description="Stage 3 (mappings+sequences) execution time")
    total_tokens: int = Field(..., description="Total tokens used across all stages")
    stage1_tokens: int = Field(..., description="Tokens used in Stage 1")
    stage2_tokens: int = Field(..., description="Tokens used in Stage 2")
    stage3_tokens: int = Field(..., description="Tokens used in Stage 3")
    token_breakdown: Dict[str, Any] = Field(..., description="Detailed token breakdown per stage")


class ThreeStageGenerateResponse(BaseModel):
    """Response from three-stage pipeline generation"""
    
    products: List[Product]
    personas: List[BuyerPersona]
    personas_with_mappings: List[PersonaWithMappings]
    sequences: List[OutreachSequence]
    artifacts: Optional[PipelineArtifacts] = None
    statistics: Optional[ThreeStageStatistics] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "products": [
                    {
                        "product_name": "Sales Cloud",
                        "description": "Complete CRM platform...",
                        "source_url": "https://www.salesforce.com/sales-cloud"
                    }
                ],
                "personas": [
                    {
                        "persona_name": "US Enterprise SaaS - Revenue Leaders",
                        "tier": "tier_1",
                        "job_titles": ["CRO", "VP Sales", "Chief Revenue Officer"],
                        "excluded_job_titles": ["HR Manager", "IT Director"],
                        "industry": "B2B SaaS Platforms",
                        "company_size_range": "2000-10000 employees",
                        "company_type": "Large enterprise SaaS",
                        "location": "United States",
                        "description": "Enterprise SaaS with 200-500 sales reps."
                    }
                ],
                "personas_with_mappings": [
                    {
                        "persona_name": "US Enterprise SaaS - Revenue Leaders",
                        "mappings": [
                            {
                                "pain_point": "Sales reps waste 30% of time on manual data entry.",
                                "value_proposition": "Sales Cloud automates 80% of CRM updates with Einstein AI."
                            }
                        ]
                    }
                ],
                "sequences": [
                    {
                        "name": "US Enterprise SaaS - Revenue Leaders Outreach Sequence",
                        "persona_name": "US Enterprise SaaS - Revenue Leaders",
                        "objective": "Introduce pipeline visibility solution",
                        "total_touches": 5,
                        "duration_days": 14,
                        "touches": []
                    }
                ],
                "artifacts": {
                    "products_file": "data/generated/salesforce_products_2025-01-02T12-00-00.json",
                    "personas_file": "data/generated/salesforce_personas_2025-01-02T12-02-00.json",
                    "mappings_file": None,
                    "sequences_file": "data/generated/salesforce_three_stage_2025-01-02T12-05-00.json"
                }
            }
        }

