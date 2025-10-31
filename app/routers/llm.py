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
from ..schemas.product_schemas import (
    ProductGenerateRequest,
    ProductCatalogResponse,
    Product
)
from ..schemas.mapping_schemas import (
    MappingGenerateRequest,
    MappingGenerationResponse,
    PersonaWithMappings
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
        
        # Prepare kwargs for generator
        generator_kwargs = {
            "generate_count": request.generate_count
        }
        
        # Add products if provided
        if request.products:
            generator_kwargs["products"] = request.products
            logger.info(f"Using {len(request.products)} products for persona generation")
        
        result = await generator_service.generate(
            generator_type="personas",
            company_name=request.company_name,
            **generator_kwargs
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


@router.post(
    "/llm/products/generate",
    response_model=ProductCatalogResponse,
    summary="Generate product catalog from company data",
    description="Analyze seller company's web content to extract product catalog with names and descriptions"
)
async def generate_products(request: ProductGenerateRequest):
    """
    Generate seller company's product catalog.
    
    This analyzes the seller's web content to extract:
    - Core products/services (3-10 offerings)
    - Clear, buyer-focused descriptions
    - Value propositions and use cases
    
    The generated product catalog can be used to:
    - Feed into persona generation for better targeting
    - Create pain-point to product mappings
    - Understand seller's go-to-market strategy
    """
    try:
        logger.info(f"Generating product catalog for: {request.company_name}")
        
        generator_service = get_generator_service()
        
        # Generate products using the generator service
        result = await generator_service.generate(
            generator_type="products",
            company_name=request.company_name,
            max_products=request.max_products
        )
        
        if not result.get("success"):
            raise ValueError("Product generation failed")
        
        response_data = result["result"]
        
        response = ProductCatalogResponse(**response_data)
        
        logger.info(
            f"Generated {len(response.products)} products for {request.company_name}"
        )
        
        for i, product in enumerate(response.products):
            logger.info(
                f"  Product {i+1}: '{product.product_name}' "
                f"({len(product.description)} chars)"
            )
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Product generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/llm/mappings/generate",
    response_model=MappingGenerationResponse,
    summary="Generate pain-point to value-prop mappings",
    description="Generate persona-specific pain-point to value-proposition mappings (Regie.ai style)"
)
async def generate_mappings(request: MappingGenerateRequest):
    """
    Generate pain-point to value-proposition mappings for buyer personas.
    
    This creates 3-10 mappings per persona, where each mapping includes:
    - Pain Point: Specific challenge the persona faces (1-2 sentences, <300 chars)
    - Value Proposition: How product solves it (1-2 sentences, <300 chars, product integrated)
    
    The system automatically loads:
    - Products (from previous product generation)
    - Personas (from previous persona generation)
    
    Requirements:
    - Must have generated personas first (required)
    - Products are recommended but optional
    
    Style: Regie.ai format - concise, tactical, product-integrated
    """
    try:
        logger.info(f"Generating pain-point mappings for: {request.company_name}")
        
        generator_service = get_generator_service()
        
        # Generate mappings (auto-loads products + personas)
        result = await generator_service.generate(
            generator_type="mappings",
            company_name=request.company_name
        )
        
        if not result.get("success"):
            raise ValueError("Mapping generation failed")
        
        response_data = result["result"]
        response = MappingGenerationResponse(**response_data)
        
        total_mappings = sum(len(p.mappings) for p in response.personas_with_mappings)
        
        logger.info(
            f"Generated mappings for {len(response.personas_with_mappings)} personas "
            f"({total_mappings} total mappings)"
        )
        
        for i, persona_data in enumerate(response.personas_with_mappings):
            logger.info(
                f"  Persona {i+1}: '{persona_data.persona_name}' "
                f"({len(persona_data.mappings)} mappings)"
            )
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Mapping generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))