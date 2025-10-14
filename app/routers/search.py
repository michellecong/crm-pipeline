# api/search.py
from fastapi import APIRouter, HTTPException, status
from ..schemas.schema import SearchRequest, SearchResponse, SearchResultItem, HealthResponse
from ..services.search_service import search_company_async
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/search/company",
    response_model=SearchResponse,
    summary="Search Company Information",
    description="Search for a company's official website, news articles, and case studies"
)
async def search_company(request: SearchRequest):
    """
    Search for comprehensive company information including:
    - Official website
    - News articles  
    - Case studies and customer success stories
    """
    try:
        logger.info(f"Searching for company: {request.company_name}")
        
        if not request.company_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company name cannot be empty"
            )
        
        raw_results = await search_company_async(
            company_name=request.company_name.strip(),
            include_news=request.include_news,
            include_case_studies=request.include_case_studies
        )
        
        response = SearchResponse(
            company_name=raw_results["company_name"],
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
        
        logger.info(f"Search completed for {request.company_name}: {response.total_results} results")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for {request.company_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

 

@router.get(
    "/search/test",
    response_model=HealthResponse,
    summary="Test Search Service"
)
async def test_search():
    """Test if search service is working"""
    try:
        test_results = await search_company_async(
            company_name="Google",
            include_news=False,
            include_case_studies=False
        )
        
        return HealthResponse(
            status="success",
            message=f"Search service working. Found: {test_results.get('official_website', 'None')}"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search test failed: {str(e)}"
        )