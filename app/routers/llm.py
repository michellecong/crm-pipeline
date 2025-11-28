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
    PipelineGenerateEnvelope,
    PipelinePayload,
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
from ..schemas.two_stage_schemas import (
    TwoStageGenerateRequest,
    TwoStageGenerateResponse
)
from ..schemas.evaluation_schemas import (
    PersonaEvaluationRequest,
    PersonaEvaluationResponse
)
from ..services.llm_service import get_llm_service
from ..services.generator_service import get_generator_service
from ..services.persona_evaluator import get_persona_evaluator
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
                f"({persona.tier.value}, {len(persona.job_titles)} titles)"
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
    response_model=PipelineGenerateEnvelope,
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
    import time
    
    try:
        pipeline_start_time = time.time()
        logger.info(f"[Pipeline] Starting for company: {request.company_name}")
        generator_service = get_generator_service()

        # Track statistics
        step_runtimes = {}
        step_tokens = {}
        token_breakdown = {}
        content_processing_tokens = {}

        # Common search kwargs passed through to DataAggregator
        extra_search_kwargs = {
            "use_llm_search": getattr(request, "use_llm_search", None),
            "provider": getattr(request, "provider", None)
        }
        extra_search_kwargs = {k: v for k, v in extra_search_kwargs.items() if v is not None}

        # Step 1: Products
        step_start = time.time()
        products_result = await generator_service.generate(
            generator_type="products",
            company_name=request.company_name,
            **extra_search_kwargs
        )
        if not products_result.get("success"):
            raise ValueError("Product generation failed")
        products_data = products_result["result"].get("products", [])
        
        # Track step statistics
        step_runtimes["products"] = time.time() - step_start
        if "usage" in products_result["result"]:
            usage = products_result["result"]["usage"]
            step_tokens["products"] = usage["total_tokens"]
            token_breakdown["products"] = usage
        
        # Track content processing tokens if available (products uses Perplexity, no content processing)
        
        logger.info(f"[Pipeline] Products generated: {len(products_data)} (Time: {step_runtimes['products']:.2f}s, Tokens: {step_tokens.get('products', 0)})")

        # Step 2: Personas (explicitly pass products from step 1)
        step_start = time.time()
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
        
        # Track step statistics
        step_runtimes["personas"] = time.time() - step_start
        if "usage" in personas_result["result"]:
            usage = personas_result["result"]["usage"]
            step_tokens["personas"] = usage["total_tokens"]
            token_breakdown["personas"] = usage
        
        # Track content processing tokens if available
        if "content_processing_tokens" in personas_result and not content_processing_tokens:
            content_processing_tokens = personas_result["content_processing_tokens"]
        
        logger.info(f"[Pipeline] Personas generated: {len(personas_data)} (Time: {step_runtimes['personas']:.2f}s, Tokens: {step_tokens.get('personas', 0)})")

        # Step 3: Mappings (explicitly pass personas + products from earlier steps)
        step_start = time.time()
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
        
        # Track step statistics
        step_runtimes["mappings"] = time.time() - step_start
        if "usage" in mappings_result["result"]:
            usage = mappings_result["result"]["usage"]
            step_tokens["mappings"] = usage["total_tokens"]
            token_breakdown["mappings"] = usage
        
        # Track content processing tokens if available (usually collected in personas step)
        if "content_processing_tokens" in mappings_result and not content_processing_tokens:
            content_processing_tokens = mappings_result["content_processing_tokens"]
        
        logger.info(
            f"[Pipeline] Mappings generated for {len(mappings_data)} personas "
            f"with {sum(len(p.get('mappings', [])) for p in mappings_data)} total mappings "
            f"(Time: {step_runtimes['mappings']:.2f}s, Tokens: {step_tokens.get('mappings', 0)})"
        )

        # Step 4: Outreach Sequences (optional, can be generated separately)
        sequences_data = []
        sequences_file = None
        
        # Try to generate sequences if mappings are available
        try:
            logger.info("[Pipeline] Generating outreach sequences...")
            step_start = time.time()
            sequences_result = await generator_service.generate(
                generator_type="outreach",
                company_name=request.company_name,
                personas_with_mappings=mappings_data
            )
            if sequences_result.get("success"):
                sequences_data = sequences_result["result"].get("sequences", [])
                sequences_file = sequences_result.get("saved_filepath")
                
                # Track step statistics
                step_runtimes["sequences"] = time.time() - step_start
                if "usage" in sequences_result["result"]:
                    usage = sequences_result["result"]["usage"]
                    step_tokens["sequences"] = usage["total_tokens"]
                    token_breakdown["sequences"] = usage
                
                logger.info(f"[Pipeline] Generated {len(sequences_data)} outreach sequences (Time: {step_runtimes.get('sequences', 0):.2f}s, Tokens: {step_tokens.get('sequences', 0)})")
            else:
                logger.warning("[Pipeline] Outreach sequence generation skipped (optional)")
        except Exception as e:
            logger.warning(f"[Pipeline] Outreach generation failed (optional): {str(e)}")
        
        # Calculate total statistics
        total_runtime = time.time() - pipeline_start_time
        total_tokens = sum(step_tokens.values())
        
        # Add content processing tokens to total if available
        if content_processing_tokens:
            total_tokens += content_processing_tokens.get('total_tokens', 0)
            token_breakdown['content_processing'] = content_processing_tokens
        
        # Build typed lists
        products_t = [Product(**p) for p in products_data]
        personas_t = [BuyerPersona(**p) for p in personas_data]
        mappings_t = [PersonaWithMappings(**pm) for pm in mappings_data]
        sequences_t = [OutreachSequence(**s) for s in sequences_data] if sequences_data else []

        # Build statistics
        from ..schemas.pipeline_schemas import PipelineStatistics
        statistics = PipelineStatistics(
            total_runtime_seconds=total_runtime,
            step_runtimes=step_runtimes,
            total_tokens=total_tokens,
            step_tokens=step_tokens,
            token_breakdown=token_breakdown
        )

        log_msg = f"[Pipeline] Completed in {total_runtime:.2f}s using {total_tokens} tokens"
        if content_processing_tokens:
            log_msg += f" (includes {content_processing_tokens.get('total_tokens', 0)} content processing tokens)"
        logger.info(log_msg)

        # Return payload envelope with statistics
        response = PipelineGenerateEnvelope(
            payload=PipelinePayload(
                products=products_t,
                personas=personas_t,
                personas_with_mappings=mappings_t,
                sequences=sequences_t,
            ),
            artifacts=PipelineArtifacts(
                products_file=products_result.get("saved_filepath"),
                personas_file=personas_result.get("saved_filepath"),
                mappings_file=mappings_result.get("saved_filepath"),
                sequences_file=sequences_file,
            ),
            statistics=statistics
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
    import time
    
    try:
        baseline_start_time = time.time()
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
        
        # Calculate statistics
        total_runtime = time.time() - baseline_start_time
        token_usage = data.get("usage", {})
        
        # Get content processing tokens from generator service result
        content_processing_tokens = result.get("content_processing_tokens", {})
        
        # Calculate total tokens (baseline generation + content processing)
        baseline_tokens = token_usage.get("total_tokens", 0)
        content_proc_tokens = content_processing_tokens.get("total_tokens", 0)
        total_tokens = baseline_tokens + content_proc_tokens
        
        # Build token breakdown
        token_breakdown_dict = {
            "prompt_tokens": token_usage.get("prompt_tokens", 0),
            "completion_tokens": token_usage.get("completion_tokens", 0),
            "total_tokens": token_usage.get("total_tokens", 0)
        }
        
        # Add content processing tokens to breakdown if available
        if content_processing_tokens:
            token_breakdown_dict["content_processing"] = content_processing_tokens
        
        # Build statistics
        from ..schemas.baseline_schemas import BaselineStatistics
        statistics = BaselineStatistics(
            total_runtime_seconds=total_runtime,
            total_tokens=total_tokens,
            token_breakdown=token_breakdown_dict
        )
        
        log_msg = f"[Baseline] Completed in {total_runtime:.2f}s using {total_tokens} tokens "
        log_msg += f"(baseline: {baseline_tokens}"
        if content_proc_tokens > 0:
            log_msg += f" + content processing: {content_proc_tokens}"
        log_msg += f") - Generated: {len(data.get('products', []))} products, {len(data.get('personas', []))} personas"
        logger.info(log_msg)
        
        # Build typed response
        response = BaselineGenerateResponse(
            products=[Product(**p) for p in data.get("products", [])],
            personas=[BuyerPersona(**p) for p in data.get("personas", [])],
            personas_with_mappings=[PersonaWithMappings(**pm) for pm in data.get("personas_with_mappings", [])],
            sequences=[OutreachSequence(**s) for s in data.get("sequences", [])] if data.get("sequences") else None,
            artifacts=PipelineArtifacts(sequences_file=result.get("saved_filepath")),
            statistics=statistics
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"[Baseline] Validation error: {str(e)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"[Baseline] Failed: {str(e)}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/llm/two-stage/generate",
    response_model=TwoStageGenerateResponse,
    summary="Two-stage baseline: Products (Stage 1) + Consolidated Personas/Mappings/Sequences (Stage 2)",
    description="Generate products in Stage 1, then personas, mappings, and sequences in one consolidated Stage 2 call"
)
async def generate_two_stage(request: TwoStageGenerateRequest):
    """
    Two-stage baseline generation for ablation study.
    
    Stage 1: Products generation (reuses ProductGenerator)
    Stage 2: Personas + Mappings + Sequences (consolidated in one call)
    
    This validates optimal number of stages by testing intermediate configurations.
    """
    import time
    
    try:
        two_stage_start_time = time.time()
        logger.info(f"[Two-Stage] Starting for company: {request.company_name}")
        generator_service = get_generator_service()
        
        # Common search kwargs passed through to DataAggregator
        extra_search_kwargs = {
            "use_llm_search": getattr(request, "use_llm_search", None),
            "provider": getattr(request, "provider", None)
        }
        extra_search_kwargs = {k: v for k, v in extra_search_kwargs.items() if v is not None}
        
        # Stage 1: Products (reuse existing ProductGenerator)
        stage1_start = time.time()
        logger.info("[Two-Stage] Stage 1: Generating products...")
        products_result = await generator_service.generate(
            generator_type="products",
            company_name=request.company_name,
            **extra_search_kwargs
        )
        if not products_result.get("success"):
            raise ValueError("Product generation failed in Stage 1")
        products_data = products_result["result"].get("products", [])
        stage1_runtime = time.time() - stage1_start
        stage1_tokens = products_result["result"].get("usage", {}).get("total_tokens", 0)
        
        logger.info(f"[Two-Stage] Stage 1 complete: {len(products_data)} products (Time: {stage1_runtime:.2f}s, Tokens: {stage1_tokens})")
        
        # Stage 2: Personas + Mappings + Sequences (consolidated)
        stage2_start = time.time()
        logger.info("[Two-Stage] Stage 2: Generating personas, mappings, and sequences...")
        consolidated_result = await generator_service.generate(
            generator_type="two_stage",
            company_name=request.company_name,
            products=products_data,  # Pass Stage 1 output
            generate_count=request.generate_count,
            **extra_search_kwargs
        )
        if not consolidated_result.get("success"):
            raise ValueError("Consolidated generation failed in Stage 2")
        
        consolidated_data = consolidated_result["result"]
        personas_data = consolidated_data.get("personas", [])
        mappings_data = consolidated_data.get("personas_with_mappings", [])
        sequences_data = consolidated_data.get("sequences", [])
        stage2_runtime = time.time() - stage2_start
        stage2_tokens = consolidated_result["result"].get("usage", {}).get("total_tokens", 0)
        
        logger.info(
            f"[Two-Stage] Stage 2 complete: {len(personas_data)} personas, "
            f"{len(mappings_data)} personas_with_mappings, {len(sequences_data)} sequences "
            f"(Time: {stage2_runtime:.2f}s, Tokens: {stage2_tokens})"
        )
        
        # Calculate total statistics
        total_runtime = time.time() - two_stage_start_time
        total_tokens = stage1_tokens + stage2_tokens
        
        # Get content processing tokens if available
        content_processing_tokens = consolidated_result.get("content_processing_tokens", {})
        if content_processing_tokens:
            content_proc_tokens = content_processing_tokens.get("total_tokens", 0)
            total_tokens += content_proc_tokens
            stage2_tokens += content_proc_tokens
        
        # Build token breakdown
        token_breakdown = {
            "stage1": products_result["result"].get("usage", {}),
            "stage2": consolidated_result["result"].get("usage", {})
        }
        if content_processing_tokens:
            token_breakdown["content_processing"] = content_processing_tokens
        
        # Build statistics
        from ..schemas.two_stage_schemas import TwoStageStatistics
        statistics = TwoStageStatistics(
            total_runtime_seconds=total_runtime,
            stage1_runtime_seconds=stage1_runtime,
            stage2_runtime_seconds=stage2_runtime,
            total_tokens=total_tokens,
            stage1_tokens=stage1_tokens,
            stage2_tokens=stage2_tokens,
            token_breakdown=token_breakdown
        )
        
        log_msg = f"[Two-Stage] Completed in {total_runtime:.2f}s using {total_tokens} tokens "
        log_msg += f"(Stage 1: {stage1_tokens}, Stage 2: {stage2_tokens})"
        logger.info(log_msg)
        
        # Build artifacts using PipelineArtifacts (aligned with pipeline design)
        # Note: personas, mappings, and sequences are all in the two_stage_file
        artifacts = PipelineArtifacts(
            products_file=products_result.get("saved_filepath"),
            personas_file=None,  # Contained in two_stage_file
            mappings_file=None,  # Contained in two_stage_file
            sequences_file=consolidated_result.get("saved_filepath")  # Contains personas, mappings, sequences
        )
        
        # Build typed response
        response = TwoStageGenerateResponse(
            products=[Product(**p) for p in products_data],
            personas=[BuyerPersona(**p) for p in personas_data],
            personas_with_mappings=[PersonaWithMappings(**pm) for pm in mappings_data],
            sequences=[OutreachSequence(**s) for s in sequences_data],
            artifacts=artifacts,
            statistics=statistics
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"[Two-Stage] Validation error: {str(e)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"[Two-Stage] Failed: {str(e)}", exc_info=True)
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
