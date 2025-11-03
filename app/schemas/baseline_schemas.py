# schemas/baseline_schemas.py
"""
Pydantic schemas for baseline single-shot generation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from .pipeline_schemas import Product, BuyerPersona, PersonaWithMappings, OutreachSequence, PipelineArtifacts


class BaselineGenerateRequest(BaseModel):
    """Request for baseline single-shot generation"""
    
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


class BaselineGenerateResponse(BaseModel):
    """Response from baseline single-shot generation containing all 4 outputs"""
    
    products: List[Product]
    personas: List[BuyerPersona]
    personas_with_mappings: List[PersonaWithMappings]
    sequences: Optional[List[OutreachSequence]] = None
    artifacts: Optional[PipelineArtifacts] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "products": [
                    {
                        "product_name": "Sales Cloud",
                        "description": "Complete CRM platform..."
                    }
                ],
                "personas": [
                    {
                        "persona_name": "US Enterprise SaaS - Revenue Leaders",
                        "tier": "tier_1",
                        "target_decision_makers": ["CRO", "VP Sales"],
                        "industry": "B2B SaaS",
                        "company_size_range": "2000-10000",
                        "company_type": "Large enterprise SaaS",
                        "location": "United States",
                        "description": "Enterprise SaaS with 200-500 reps"
                    }
                ],
                "personas_with_mappings": [
                    {
                        "persona_name": "US Enterprise SaaS - Revenue Leaders",
                        "mappings": [
                            {
                                "pain_point": "Sales reps waste time on manual data entry",
                                "value_proposition": "Sales Cloud automates 80% of CRM updates"
                            }
                        ]
                    }
                ],
                "sequences": [],
                "artifacts": {
                    "products_file": None,
                    "personas_file": None,
                    "mappings_file": None,
                    "sequences_file": "data/generated/salesforce_baseline_2025-01-02T12-00-00.json"
                }
            }
        }

