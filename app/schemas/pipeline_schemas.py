from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
try:
    from pydantic import ConfigDict
except Exception:
    ConfigDict = dict  # Fallback for environments pinning older pydantic
from .product_schemas import Product
from .persona_schemas import BuyerPersona
from .mapping_schemas import PersonaWithMappings
from .outreach_schemas import OutreachSequence


class PipelineGenerateRequest(BaseModel):
    company_name: str = Field(..., description="Company name to analyze", min_length=2)
    generate_count: int = Field(default=5, ge=3, le=12, description="Number of personas to generate")
    provider: Optional[Literal["google", "perplexity"]] = Field(default=None, description="Search provider (google or perplexity)")


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



class PipelinePayload(BaseModel):
    products: List[Product]
    personas: List[BuyerPersona]
    personas_with_mappings: List[PersonaWithMappings]
    sequences: List[OutreachSequence] = Field(default_factory=list)


class PipelineStatistics(BaseModel):
    """Statistics for pipeline execution"""
    total_runtime_seconds: float = Field(..., description="Total pipeline execution time in seconds")
    step_runtimes: Dict[str, float] = Field(..., description="Runtime for each step (products, personas, mappings, sequences)")
    total_tokens: int = Field(..., description="Total tokens used across all steps")
    step_tokens: Dict[str, int] = Field(..., description="Token usage for each step")
    token_breakdown: Dict[str, Dict[str, int]] = Field(..., description="Detailed token breakdown (prompt/completion) per step")


class PipelineGenerateEnvelope(BaseModel):
    payload: PipelinePayload
    artifacts: Optional[PipelineArtifacts] = None
    statistics: Optional[PipelineStatistics] = None



# --- Completeness evaluation schemas ---

class PipelineCompletenessIssue(BaseModel):
    path: str
    message: str
    type: Optional[str] = None


class PipelineSectionReport(BaseModel):
    model_config = ConfigDict(ser_json_exclude_none=True)
    name: str
    required: bool = True
    present: bool
    total_items: int = 0
    valid_items: int = 0
    missing_required_errors: int = 0
    completeness_ratio: float = 0.0
    errors: List[PipelineCompletenessIssue] = []
    required_fields: List[str] = []
    field_missing_counts: Dict[str, int] = {}
    blank_required_errors: int = 0
    field_blank_counts: Dict[str, int] = {}
    # Per-item field completeness scores and aggregates
    item_field_scores: Optional[Dict[str, float]] = None
    avg_field_score: Optional[float] = None
    field_completion_rates: Optional[Dict[str, float]] = None


class CrossComponentCheck(BaseModel):
    passed: bool
    issues: List[PipelineCompletenessIssue] = []


class PipelineCompletenessReport(BaseModel):
    is_complete: bool
    required_sections_present: Dict[str, bool]
    sections: Dict[str, PipelineSectionReport]
    cross_component: CrossComponentCheck
    score_required_only: float
    score_including_optional: float


class PipelineEvaluateRequest(BaseModel):
    payload: Dict


class PipelineEvaluateResponse(BaseModel):
    report: PipelineCompletenessReport

