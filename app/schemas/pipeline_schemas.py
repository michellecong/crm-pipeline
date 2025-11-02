from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from .product_schemas import Product
from .persona_schemas import BuyerPersona
from .mapping_schemas import PersonaWithMappings
from .outreach_schemas import OutreachSequence


class PipelineGenerateRequest(BaseModel):
    company_name: str = Field(..., description="Company name to analyze", min_length=2)
    generate_count: int = Field(default=5, ge=3, le=12, description="Number of personas to generate")
    use_llm_search: Optional[bool] = Field(default=None, description="Use LLM-planned web search")
    provider: Optional[Literal["google", "perplexity"]] = Field(default=None, description="Search provider")


class PipelineArtifacts(BaseModel):
    products_file: Optional[str] = None
    personas_file: Optional[str] = None
    mappings_file: Optional[str] = None
    sequences_file: Optional[str] = None


class PipelineGenerateResponse(BaseModel):
    products: List[Product]
    personas: List[BuyerPersona]
    personas_with_mappings: List[PersonaWithMappings]
    sequences: Optional[List[OutreachSequence]] = None
    artifacts: Optional[PipelineArtifacts] = None


