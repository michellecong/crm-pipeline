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
    PersonaGenerationResponse,
    BuyerPersona
)
from ..services.llm_service import get_llm_service
from ..services.generator_service import get_generator_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/llm/generate",
    response_model=LLMGenerateResponse,
    summary="Generate text from LLM"
)
async def generate_text(request: LLMGenerateRequest):
    """General-purpose LLM text generation endpoint."""
    try:
        logger.info(f"Generating text with prompt length: {len(request.prompt)}")
        
        llm_service = get_llm_service()
        
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
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/llm/config", response_model=LLMConfigResponse)
async def get_llm_config():
    """Get current LLM configuration"""
    try:
        llm_service = get_llm_service()
        config = llm_service.get_config()
        return LLMConfigResponse(**config)
    except Exception as e:
        logger.error(f"Failed to get config: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/llm/config", response_model=LLMConfigResponse)
async def update_llm_config(request: LLMConfigUpdateRequest):
    """Update LLM configuration"""
    try:
        llm_service = get_llm_service()
        update_data = request.dict(exclude_none=True)
        if update_data:
            llm_service.update_config(**update_data)
            logger.info(f"Updated LLM config: {update_data}")
        config = llm_service.get_config()
        return LLMConfigResponse(**config)
    except Exception as e:
        logger.error(f"Failed to update config: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/llm/test")
async def test_llm():
    """Test LLM connectivity"""
    try:
        llm_service = get_llm_service()
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
        return {
            "status": "not_configured",
            "message": str(e),
            "note": "Set OPENAI_API_KEY in .env"
        }
    except Exception as e:
        logger.error(f"LLM test failed: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/llm/persona/generate",
    response_model=PersonaGenerationResponse,
    summary="Generate buyer personas",
    description="Generate buyer company archetypes (market segments) based on company analysis"
)
async def generate_buyer_personas(request: PersonaGenerateRequest):
    """
    Generate buyer company personas for a seller company.
    
    Input: Company name (seller company to analyze)
    Process: Scrape company data → Analyze business → Generate buyer personas
    Output: Buyer company archetypes (e.g., "California Mid-Market SaaS - Sales Leaders")
    
    Note: Products and CRM data are optional for MVP. Personas will be generated
    based on available web content. Full integration coming in later stages.
    """
    try:
        logger.info(f"Generating buyer personas for: {request.company_name}")
        
        generator_service = get_generator_service()
        
        result = await generator_service.generate(
            generator_type="personas",
            company_name=request.company_name,
            generate_count=request.generate_count
        )
        
        if not result.get("success"):
            raise ValueError("Persona generation failed")
        
        response_data = result["result"]
        response = PersonaGenerationResponse(**response_data)
        
        logger.info(
            f"Generated {len(response.personas)} buyer personas for {request.company_name}"
        )
        
        for i, persona in enumerate(response.personas):
            logger.info(
                f"  Persona {i+1}: '{persona.persona_name}' "
                f"({persona.tier.value}, {len(persona.target_decision_makers)} titles)"
            )
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Persona generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))