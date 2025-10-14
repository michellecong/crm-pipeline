"""
LLM Router - API endpoints for language model operations
"""
from fastapi import APIRouter, HTTPException, status
from ..schemas.llm_schema import (
    LLMGenerateRequest,
    LLMGenerateResponse,
    LLMConfigResponse,
    LLMConfigUpdateRequest,
    TokenUsage
)
from ..services.llm_service import get_llm_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/llm/generate",
    response_model=LLMGenerateResponse,
    summary="Generate text from LLM",
    description="Send a prompt to the LLM and get a response"
)
async def generate_text(request: LLMGenerateRequest):
    """
    General-purpose LLM text generation endpoint.
    
    Use this for:
    - Testing LLM connectivity
    - Custom prompts
    - Debugging generation issues
    """
    try:
        logger.info(f"Generating text with prompt length: {len(request.prompt)}")
        
        llm_service = get_llm_service()
        
        # Call LLM service (async wrapper)
        response = await llm_service.generate_async(
            prompt=request.prompt,
            system_message=request.system_message,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return LLMGenerateResponse(
            content=response.content,
            model=response.model,
            finish_reason=response.finish_reason,
            usage=TokenUsage(
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                total_tokens=response.total_tokens
            )
        )
        
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM generation failed: {str(e)}"
        )


@router.get(
    "/llm/config",
    response_model=LLMConfigResponse,
    summary="Get current LLM configuration"
)
async def get_llm_config():
    """Get current LLM service configuration settings."""
    try:
        llm_service = get_llm_service()
        config = llm_service.get_config()
        return LLMConfigResponse(**config)
        
    except Exception as e:
        logger.error(f"Failed to get config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get config: {str(e)}"
        )


@router.patch(
    "/llm/config",
    response_model=LLMConfigResponse,
    summary="Update LLM configuration"
)
async def update_llm_config(request: LLMConfigUpdateRequest):
    """
    Update LLM service configuration.
    Only provided fields will be updated.
    """
    try:
        llm_service = get_llm_service()
        
        # Update only provided fields
        update_data = request.dict(exclude_none=True)
        if update_data:
            llm_service.update_config(**update_data)
            logger.info(f"Updated LLM config: {update_data}")
        
        # Return updated config
        config = llm_service.get_config()
        return LLMConfigResponse(**config)
        
    except Exception as e:
        logger.error(f"Failed to update config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update config: {str(e)}"
        )


@router.get(
    "/llm/test",
    summary="Test LLM service connectivity"
)
async def test_llm():
    """
    Test if LLM service is configured and can connect to OpenAI API.
    This endpoint will fail gracefully if API key is not set.
    """
    try:
        llm_service = get_llm_service()
        
        # Try a simple generation
        response = await llm_service.generate_async(
            prompt="Say 'Connection successful!' if you can read this.",
            max_tokens=20
        )
        
        return {
            "status": "success",
            "message": "LLM service is working",
            "response": response.content,
            "model": response.model,
            "tokens_used": response.total_tokens
        }
        
    except ValueError as e:
        # API key not configured
        return {
            "status": "not_configured",
            "message": str(e),
            "note": "Set OPENAI_API_KEY in .env file to enable LLM features"
        }
    except Exception as e:
        logger.error(f"LLM test failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM test failed: {str(e)}"
        )

