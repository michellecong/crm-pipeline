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
from ..schemas.persona_schemas import (
    PersonaGenerateRequest,
    PersonaResponse,
    Persona,
    TierClassification
)
from ..services.llm_service import get_llm_service
from ..services.generator_service import get_generator_service
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
            max_completion_tokens=request.max_completion_tokens
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
            max_completion_tokens=500
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


@router.post(
    "/llm/persona/generate",
    response_model=PersonaResponse,
    summary="Generate personas from company data",
    description="Use scraped web content to generate detailed buyer personas with tier classification and structured data."
)
async def generate_persona(request: PersonaGenerateRequest):
    """
    Enhanced persona generation endpoint that generates multiple structured personas
    with tier classification, pain points, goals, and communication preferences.
    """
    try:
        generator_service = get_generator_service()
        
        # Generate personas using the generator service
        result = await generator_service.generate(
            generator_type="personas",
            company_name=request.company_name,
            generate_count=request.generate_count,
            max_context_chars=request.max_context_chars,
            include_news=request.include_news,
            include_case_studies=request.include_case_studies,
            max_urls=request.max_urls
        )
        
        # Convert to response format
        personas_data = result["result"].get("personas", [])
        tier_data = result["result"].get("tier_classification", {})
        
        # Create Persona objects
        personas = []
        for persona_data in personas_data:
            persona = Persona(
                name=persona_data.get("name", "Unknown"),
                tier=persona_data.get("tier", "tier_3"),
                job_title=persona_data.get("job_title"),
                industry=persona_data.get("industry"),
                department=persona_data.get("department"),
                location=persona_data.get("location"),
                company_size=persona_data.get("company_size"),
                description=persona_data.get("description"),
                decision_power=persona_data.get("decision_power"),
                pain_points=persona_data.get("pain_points", []),
                goals=persona_data.get("goals", []),
                communication_preferences=persona_data.get("communication_preferences", [])
            )
            personas.append(persona)
        
        # Create tier classification
        tier_classification = TierClassification(
            tier_1=tier_data.get("tier_1", []),
            tier_2=tier_data.get("tier_2", []),
            tier_3=tier_data.get("tier_3", [])
        )
        
        return PersonaResponse(
            company_name=result["company_name"],
            personas=personas,
            tier_classification=tier_classification,
            context_length=result["context_length"],
            generated_at=result["generated_at"],
            total_personas=len(personas),
            model=result["result"].get("model")
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Persona generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Persona generation failed: {str(e)}"
        )
