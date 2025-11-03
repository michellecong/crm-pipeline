from fastapi import APIRouter, HTTPException, status
from ..schemas.pipeline_schemas import PipelineEvaluateRequest, PipelineEvaluateResponse
from ..services.pipeline_completeness import evaluate_pipeline_completeness


router = APIRouter()


@router.post(
    "/pipeline/evaluation/completeness",
    response_model=PipelineEvaluateResponse,
    summary="Pipeline completeness report",
    description="Validate products, personas, mappings, and sequences; compute per-item completeness scores and overall completeness."
)
async def get_pipeline_completeness(request: PipelineEvaluateRequest):
    try:
        report = evaluate_pipeline_completeness(request.payload)
        return PipelineEvaluateResponse(report=report)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Evaluation failed: {str(e)}"
        )


