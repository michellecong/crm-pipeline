from fastapi import APIRouter, HTTPException, status
from ..schemas import SearchRequest, SearchResponse, SearchResultItem, HealthResponse
from ..services.perplexity_search_service import search_company_perplexity_async
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/search/perplexity/company",
    response_model=SearchResponse,
    summary="Search Company Information via Perplexity",
    description="Use Perplexity online search to find official website, news, and case studies"
)
async def search_company_perplexity(request: SearchRequest):
    try:
        logger.info(f"Perplexity search for company: {request.company_name}")

        if not request.company_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company name cannot be empty"
            )

        raw_results = await search_company_perplexity_async(
            company_name=request.company_name.strip(),
            include_news=request.include_news,
            include_case_studies=request.include_case_studies
        )

        response = SearchResponse(
            company_name=raw_results.get("company_name", request.company_name),
            official_website=raw_results.get("official_website"),
            news_articles=[
                SearchResultItem(**item) for item in raw_results.get("news_articles", [])
            ],
            case_studies=[
                SearchResultItem(**item) for item in raw_results.get("case_studies", [])
            ],
            total_results=len(raw_results.get("news_articles", [])) + len(raw_results.get("case_studies", [])),
            search_timestamp=raw_results.get("search_timestamp", datetime.now().isoformat())
        )

        logger.info(
            f"Perplexity search completed for {request.company_name}: {response.total_results} results"
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Perplexity search failed for {request.company_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get(
    "/search/perplexity/test",
    response_model=HealthResponse,
    summary="Test Perplexity Search Service"
)
async def test_perplexity_search():
    try:
        test_results = await search_company_perplexity_async(
            company_name="Google",
            include_news=False,
            include_case_studies=False
        )

        return HealthResponse(
            status="success",
            message=f"Perplexity search working. Found: {test_results.get('official_website', 'None')}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Perplexity search test failed: {str(e)}"
        )


