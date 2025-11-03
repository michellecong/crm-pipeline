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
from ..schemas.pipeline_schemas import (
    PipelineGenerateRequest,
    PipelineGenerateResponse,
    PipelineArtifacts
)
from ..schemas.outreach_schemas import (
    OutreachGenerateRequest,
    OutreachGenerationResponse,
    OutreachSequence
)
from ..schemas.baseline_schemas import (
    BaselineGenerateRequest,
    BaselineGenerateResponse
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
        # Optional search controls
        extra_search_kwargs = {
            "use_llm_search": getattr(request, "use_llm_search", None),
            "provider": getattr(request, "provider", None)
        }
        generator_kwargs.update({k: v for k, v in extra_search_kwargs.items() if v is not None})
        
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
        extra_search_kwargs = {
            "use_llm_search": getattr(request, "use_llm_search", None),
            "provider": getattr(request, "provider", None)
        }
        generator_kwargs = {k: v for k, v in extra_search_kwargs.items() if v is not None}
        result = await generator_service.generate(
            generator_type="products",
            company_name=request.company_name,
            **generator_kwargs
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
        extra_search_kwargs = {
            "use_llm_search": getattr(request, "use_llm_search", None),
            "provider": getattr(request, "provider", None)
        }
        generator_kwargs = {k: v for k, v in extra_search_kwargs.items() if v is not None}
        result = await generator_service.generate(
            generator_type="mappings",
            company_name=request.company_name,
            **generator_kwargs
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

@router.post(
    "/llm/pipeline/generate",
    response_model=PipelineGenerateResponse,
    summary="Run full pipeline: products → personas → mappings → sequences",
    description="Generate product catalog from scraped content, then personas using products + content, pain-point mappings using personas, and finally outreach sequences."
)
async def generate_full_pipeline(request: PipelineGenerateRequest):
    """
    Pipeline:
    1) Generate products from scraped content.
    2) Generate personas using products + scraped content.
    3) Generate pain-point mappings using personas (+ products).
    4) Generate outreach sequences using personas_with_mappings (optional).
    """
    try:
        logger.info(f"[Pipeline] Starting for company: {request.company_name}")
        generator_service = get_generator_service()

        # Common search kwargs passed through to DataAggregator
        extra_search_kwargs = {
            "use_llm_search": getattr(request, "use_llm_search", None),
            "provider": getattr(request, "provider", None)
        }
        extra_search_kwargs = {k: v for k, v in extra_search_kwargs.items() if v is not None}

        # Step 1: Products
        products_result = await generator_service.generate(
            generator_type="products",
            company_name=request.company_name,
            **extra_search_kwargs
        )
        if not products_result.get("success"):
            raise ValueError("Product generation failed")
        products_data = products_result["result"].get("products", [])
        logger.info(f"[Pipeline] Products generated: {len(products_data)}")

        # Step 2: Personas (explicitly pass products from step 1)
        personas_result = await generator_service.generate(
            generator_type="personas",
            company_name=request.company_name,
            products=products_data,
            generate_count=request.generate_count,
            **extra_search_kwargs
        )
        if not personas_result.get("success"):
            raise ValueError("Persona generation failed")
        personas_data = personas_result["result"].get("personas", [])
        logger.info(f"[Pipeline] Personas generated: {len(personas_data)}")

        # Step 3: Mappings (explicitly pass personas + products from earlier steps)
        mappings_result = await generator_service.generate(
            generator_type="mappings",
            company_name=request.company_name,
            products=products_data,
            personas=personas_data,
            **extra_search_kwargs
        )
        if not mappings_result.get("success"):
            raise ValueError("Mapping generation failed")
        mappings_data = mappings_result["result"].get("personas_with_mappings", [])
        logger.info(
            f"[Pipeline] Mappings generated for {len(mappings_data)} personas "
            f"with {sum(len(p.get('mappings', [])) for p in mappings_data)} total mappings"
        )

        # Step 4: Outreach Sequences (optional, can be generated separately)
        sequences_data = []
        sequences_file = None
        
        # Try to generate sequences if mappings are available
        try:
            logger.info("[Pipeline] Generating outreach sequences...")
            sequences_result = await generator_service.generate(
                generator_type="outreach",
                company_name=request.company_name,
                personas_with_mappings=mappings_data
            )
            if sequences_result.get("success"):
                sequences_data = sequences_result["result"].get("sequences", [])
                sequences_file = sequences_result.get("saved_filepath")
                logger.info(f"[Pipeline] Generated {len(sequences_data)} outreach sequences")
            else:
                logger.warning("[Pipeline] Outreach sequence generation skipped (optional)")
        except Exception as e:
            logger.warning(f"[Pipeline] Outreach generation failed (optional): {str(e)}")
        
        # Build typed response
        from ..schemas.pipeline_schemas import PipelineArtifacts
        response = PipelineGenerateResponse(
            products=[Product(**p) for p in products_data],
            personas=[BuyerPersona(**p) for p in personas_data],
            personas_with_mappings=[PersonaWithMappings(**pm) for pm in mappings_data],
            sequences=[OutreachSequence(**s) for s in sequences_data] if sequences_data else None,
            artifacts=PipelineArtifacts(
                products_file=products_result.get("saved_filepath"),
                personas_file=personas_result.get("saved_filepath"),
                mappings_file=mappings_result.get("saved_filepath"),
                sequences_file=sequences_file,
            ),
        )
        return response

    except ValueError as e:
        logger.error(f"[Pipeline] Validation error: {str(e)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"[Pipeline] Failed: {str(e)}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/llm/baseline/generate",
    response_model=BaselineGenerateResponse,
    summary="Baseline: Single-shot generation of all outputs",
    description="Generate products, personas, mappings, and sequences in ONE LLM call (baseline comparison)"
)
async def generate_baseline(request: BaselineGenerateRequest):
    """
    Baseline single-shot generation for comparison with multi-stage pipeline.
    Generates all 4 outputs in one LLM call without inter-stage information flow.
    """
    try:
        logger.info(f"[Baseline] Starting for company: {request.company_name}")
        generator_service = get_generator_service()
        
        # Common search kwargs passed through to DataAggregator
        extra_search_kwargs = {
            "use_llm_search": getattr(request, "use_llm_search", None),
            "provider": getattr(request, "provider", None)
        }
        extra_search_kwargs = {k: v for k, v in extra_search_kwargs.items() if v is not None}
        
        # Prepare kwargs (aligned with pipeline)
        generator_kwargs = {
            "generate_count": request.generate_count
        }
        generator_kwargs.update(extra_search_kwargs)
        
        # Single generation call
        result = await generator_service.generate(
            generator_type="baseline",
            company_name=request.company_name,
            **generator_kwargs
        )
        
        if not result.get("success"):
            raise ValueError("Baseline generation failed")
        
        data = result["result"]
        
        # Build typed response
        response = BaselineGenerateResponse(
            products=[Product(**p) for p in data.get("products", [])],
            personas=[BuyerPersona(**p) for p in data.get("personas", [])],
            personas_with_mappings=[PersonaWithMappings(**pm) for pm in data.get("personas_with_mappings", [])],
            sequences=[OutreachSequence(**s) for s in data.get("sequences", [])] if data.get("sequences") else None,
            artifacts=PipelineArtifacts(sequences_file=result.get("saved_filepath"))
        )
        
        logger.info(f"[Baseline] Generated: {len(response.products)} products, {len(response.personas)} personas")
        return response
        
    except ValueError as e:
        logger.error(f"[Baseline] Validation error: {str(e)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"[Baseline] Failed: {str(e)}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/outreach/generate",
    response_model=OutreachGenerationResponse,
    summary="Generate outreach sequences",
    description="Generate multi-touch sales outreach sequences for personas with pain point-value proposition mappings"
)
async def generate_outreach_sequences(request: OutreachGenerateRequest):
    """
    Generate outreach sequences for all personas.
    
    Creates a 4-6 touch sales cadence for each persona, incorporating their specific
    pain points and value propositions from the mapping stage.
    """
    try:
        logger.info(f"Generating outreach sequences for {request.company_name}")
        logger.info(f"Number of personas: {len(request.personas_with_mappings)}")
        
        # Get generator service
        generator_service = get_generator_service()
        
        # Generate sequences using OutreachGenerator
        result = await generator_service.generate(
            generator_type="outreach",
            company_name=request.company_name,
            personas_with_mappings=request.personas_with_mappings
        )
        
        if not result.get("success"):
            raise ValueError("Outreach sequence generation failed")
        
        sequences_data = result["result"].get("sequences", [])
        logger.info(f"Generated {len(sequences_data)} outreach sequences")
        
        # Validate and build response
        sequences = [OutreachSequence(**seq) for seq in sequences_data]
        
        response = OutreachGenerationResponse(sequences=sequences)
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Outreach generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Outreach generation failed: {str(e)}"
        )


@router.post(
    "/personas/evaluate",
    response_model=PersonaEvaluationResponse,
    summary="Evaluate persona diversity and quality",
    description="Evaluate a set of personas using semantic diversity (embedding cosine distance), industry diversity, geographic diversity, and other quality metrics"
)
async def evaluate_personas(request: PersonaEvaluationRequest):
    """
    Evaluate personas for diversity and quality.
    
    Key Metrics:
    - **Semantic Diversity (Metric 3)**: Uses embedding cosine distance to measure
      semantic similarity between personas. Higher diversity = lower similarity.
    - Industry Diversity: Count of unique industries
    - Geographic Diversity: Count of unique locations
    - Size Diversity: Coverage of company size ranges
    - Tier Distribution: Balance across tier_1, tier_2, tier_3
    - Completeness: Field completeness check
    
    Returns comprehensive evaluation with scores and recommendations.
    """
    try:
        logger.info(f"Evaluating {len(request.personas)} personas")
        
        evaluator = get_persona_evaluator()
        evaluation_result = evaluator.evaluate_personas(request.personas)
        
        # Check for errors
        if "error" in evaluation_result:
            raise ValueError(evaluation_result["error"])
        
        # Build response - convert nested dicts to Pydantic models
        from ..schemas.evaluation_schemas import (
            DiversityMetrics, IndustryDiversity, GeographicDiversity,
            SizeDiversity, TierDistribution, Completeness
        )
        
        response = PersonaEvaluationResponse(
            persona_count=evaluation_result["persona_count"],
            overall_score=evaluation_result["overall_score"],
            semantic_diversity=DiversityMetrics(**evaluation_result["semantic_diversity"]),
            industry_diversity=IndustryDiversity(**evaluation_result["industry_diversity"]),
            geographic_diversity=GeographicDiversity(**evaluation_result["geographic_diversity"]),
            size_diversity=SizeDiversity(**evaluation_result["size_diversity"]),
            tier_distribution=TierDistribution(**evaluation_result["tier_distribution"]),
            completeness=Completeness(**evaluation_result["completeness"]),
            recommendations=evaluation_result["recommendations"]
        )
        
        logger.info(
            f"Evaluation complete: overall_score={response.overall_score:.3f}, "
            f"semantic_diversity={response.semantic_diversity.diversity_score:.3f}"
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Persona evaluation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )
