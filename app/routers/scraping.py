# routers/scraping.py
"""
API routes for data scraping
"""
from fastapi import APIRouter, HTTPException, status
from ..schemas import ScrapeRequest, ScrapeResponse
from ..controllers.scraping_controller import get_scraping_controller
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/scrape/company",
    response_model=ScrapeResponse,
    summary="Scrape Company Data",
    description="Search for company information and scrape all found URLs"
)
async def scrape_company_data(request: ScrapeRequest):
    """Scrape company data from search results"""
    try:
        controller = get_scraping_controller()
        result = await controller.scrape_company(
            company_name=request.company_name,
            include_news=request.include_news,
            include_case_studies=request.include_case_studies,
            max_urls=request.max_urls,
            save_to_file=request.save_to_file,
            provider=request.provider
        )
        return ScrapeResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scraping failed: {str(e)}"
        )


@router.get(
    "/scrape/saved",
    summary="List Saved Data",
    description="List all saved scraped data files"
)
async def list_saved_data():
    """List all saved scraped data"""
    try:
        controller = get_scraping_controller()
        return await controller.list_saved_data()
    except Exception as e:
        logger.error(f"Failed to list saved data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list saved data: {str(e)}"
        )
