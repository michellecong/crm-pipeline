"""
LLM Router - API endpoints for language model operations
"""
from fastapi import APIRouter, HTTPException, status
from ..schemas.llm_schema import (
    LLMGenerateRequest,
    LLMGenerateResponse,
    LLMConfigResponse,
    LLMConfigUpdateRequest,
    TokenUsage,
    PersonaGenerateRequest,
    PersonaResponse
)
from ..services.llm_service import get_llm_service
from ..controllers.scraping_controller import get_scraping_controller
from ..services.data_store import get_data_store
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
            max_completion_tokens=20
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
    summary="Generate persona from company data",
    description="Search and scrape web content for the company by name, then generate a buyer persona."
)
async def generate_persona(request: PersonaGenerateRequest):
    try:
        # 1) Prefer local cached scraped data if available
        data_store = get_data_store()
        scraping_result = data_store.load_latest_scraped_data(request.company_name)

        # Fallback to scraping if no local cache
        if not scraping_result:
            controller = get_scraping_controller()
            scraping_result = await controller.scrape_company(
                company_name=request.company_name,
                include_news=request.include_news,
                include_case_studies=request.include_case_studies,
                max_urls=request.max_urls,
                save_to_file=True
            )

        items = [
            it for it in scraping_result.get("scraped_content", [])
            if it.get("success") and it.get("markdown")
        ]
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No usable content scraped for this company"
            )

        # 2) Concatenate markdown with a conservative character budget
        char_budget = 4000
        combined, total = [], 0
        for it in items:
            text = it["markdown"].strip()
            if not text:
                continue
            remaining = char_budget - total
            if remaining <= 0:
                break
            snippet = text[:remaining]
            combined.append(f"URL: {it.get('url','')}\n\n{snippet}")
            total += len(snippet)

        context = "\n\n---\n\n".join(combined)
        logger.info(f"Persona context prepared: items={len(items)}, context_chars={len(context)}")

        # 3) Call LLM
        system_message = (
            "You are a B2B marketing analyst. Create a concise buyer persona "
            "(name, role, company size, goals, pain points, key objections, purchase triggers). "
            "Only output plain text; do not return JSON or tool calls. Base it only on the provided content."
        )
        prompt = (
            "Use the following content to infer a single buyer persona for this company.\n\n"
            f"Content:\n{context}\n\n"
            "Return only the persona."
        )

        llm_service = get_llm_service()
        resp = await llm_service.generate_async(
            prompt=prompt,
            system_message=system_message,
            max_completion_tokens=2000,
        )

        return PersonaResponse(persona=resp.content, model=resp.model)


    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Persona generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Persona generation failed: {str(e)}"
        )
