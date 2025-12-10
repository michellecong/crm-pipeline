# schemas/two_stage_schemas.py
"""
Pydantic schemas for two-stage pipeline generation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from .product_schemas import Product
from .persona_schemas import BuyerPersona
from .mapping_schemas import PersonaWithMappings
from .outreach_schemas import OutreachSequence
from .pipeline_schemas import PipelineArtifacts


class TwoStageGenerateRequest(BaseModel):
    """Request for two-stage pipeline generation"""
    
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
    provider: Optional[Literal["google", "perplexity"]] = Field(
        default=None,
        description="Search provider (google or perplexity)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Salesforce",
                "generate_count": 5,
                "provider": "google"
            }
        }


class TwoStageStatistics(BaseModel):
    """Statistics for two-stage execution"""
    total_runtime_seconds: float = Field(..., description="Total two-stage execution time in seconds")
    stage1_runtime_seconds: float = Field(..., description="Stage 1 (products) execution time")
    stage2_runtime_seconds: float = Field(..., description="Stage 2 (consolidated) execution time")
    total_tokens: int = Field(..., description="Total tokens used across both stages")
    stage1_tokens: int = Field(..., description="Tokens used in Stage 1")
    stage2_tokens: int = Field(..., description="Tokens used in Stage 2")
    token_breakdown: Dict[str, Any] = Field(..., description="Detailed token breakdown per stage")


class TwoStageGenerateResponse(BaseModel):
    """Response from two-stage pipeline generation"""
    
    products: List[Product]
    personas: List[BuyerPersona]
    personas_with_mappings: List[PersonaWithMappings]
    sequences: List[OutreachSequence]
    artifacts: Optional[PipelineArtifacts] = None
    statistics: Optional[TwoStageStatistics] = None
    
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
                        "description": "Enterprise SaaS with 200-500 sales reps. $500K-$2M annual contracts with 8-12 month sales cycles involving 6-9 stakeholders."
                    }
                ],
                "personas_with_mappings": [
                    {
                        "persona_name": "US Enterprise SaaS - Revenue Leaders",
                        "mappings": [
                            {
                                "pain_point": "Sales reps waste 30% of time on manual data entry, reducing selling time.",
                                "value_proposition": "Sales Cloud automates 80% of CRM updates with Einstein AI, freeing 10+ hours per rep per week."
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
                        "touches": [
                            {
                                "sort_order": 1,
                                "touch_type": "email",
                                "timing_days": 0,
                                "objective": "Introduce pipeline visibility challenge",
                                "subject_line": "30% better forecasts for enterprise teams",
                                "content_suggestion": "Hi {first_name}, many enterprise SaaS teams struggle with pipeline visibility...",
                                "hints": "Personalize with recent expansion news"
                            }
                        ]
                    }
                ],
                "artifacts": {
                    "products_file": "data/generated/salesforce_products_2025-01-02T12-00-00.json",
                    "personas_file": None,
                    "mappings_file": None,
                    "sequences_file": "data/generated/salesforce_two_stage_2025-01-02T12-05-00.json"
                }
            }
        }

