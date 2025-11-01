from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal


class PainPointMapping(BaseModel):
    """Single pain point to value proposition mapping"""
    
    pain_point: str = Field(
        ...,
        description="Pain point (1-2 sentences, <300 chars)",
        max_length=300
    )
    
    value_proposition: str = Field(
        ...,
        description="Value proposition with product name integrated (1-2 sentences, <300 chars)",
        max_length=300
    )
    
    @field_validator('pain_point', 'value_proposition')
    @classmethod
    def validate_length(cls, v):
        if len(v) > 300:
            raise ValueError("Must be under 300 characters")
        if len(v) < 20:
            raise ValueError("Too short, needs more detail")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "pain_point": "Sales teams struggle with too many prospecting tools, hindering productivity.",
                "value_proposition": "Agents consolidate multiple prospecting tools into one platform, saving costs and streamlining workflow."
            }
        }


class PersonaWithMappings(BaseModel):
    """Persona with associated pain-point mappings"""
    
    persona_name: str = Field(
        ..., 
        description="Persona name (must match generated persona)"
    )
    
    mappings: List[PainPointMapping] = Field(
        ...,
        description="Pain point to value prop mappings (3-10 per persona)",
        min_length=3,
        max_length=10
    )
    
    @field_validator('mappings')
    @classmethod
    def validate_mappings_count(cls, v):
        if len(v) < 3:
            raise ValueError("Each persona must have at least 3 mappings")
        if len(v) > 10:
            raise ValueError("Each persona should have at most 10 mappings")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "persona_name": "Operations Leader (ATL)",
                "mappings": [
                    {
                        "pain_point": "Sales teams struggle with too many prospecting tools, hindering productivity.",
                        "value_proposition": "Agents consolidate multiple prospecting tools into one platform, saving costs and streamlining workflow."
                    }
                ]
            }
        }


class MappingGenerationResponse(BaseModel):
    """Complete response with all personas and their mappings"""
    
    personas_with_mappings: List[PersonaWithMappings] = Field(
        ...,
        description="All personas with their pain-point mappings"
    )
    
    @field_validator('personas_with_mappings')
    @classmethod
    def validate_personas_exist(cls, v):
        if len(v) == 0:
            raise ValueError("Must have at least one persona with mappings")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "personas_with_mappings": [
                    {
                        "persona_name": "Operations Leader (ATL)",
                        "mappings": [
                            {
                                "pain_point": "Sales teams struggle with too many prospecting tools, hindering productivity.",
                                "value_proposition": "Agents consolidate multiple prospecting tools into one platform, saving costs and streamlining workflow."
                            },
                            {
                                "pain_point": "Active buyers go unworked because sales doesn't act on intent signals.",
                                "value_proposition": "Agents leverage intent data to engage active buyers, creating smarter paths to meetings."
                            }
                        ]
                    }
                ]
            }
        }


class MappingGenerateRequest(BaseModel):
    """Request to generate persona mappings"""
    
    company_name: str = Field(
        ...,
        description="Company name to generate mappings for",
        min_length=2
    )
    # Optional search behavior controls (used to collect web content when needed)
    use_llm_search: Optional[bool] = Field(
        default=None,
        description="Use LLM-planned web search; if False, use selected provider. If omitted, system default is used."
    )
    provider: Optional[Literal["google", "perplexity"]] = Field(
        default=None,
        description="Search provider when not using LLM search"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Salesforce"
            }
        }

