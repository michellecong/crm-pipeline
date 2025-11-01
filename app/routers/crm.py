# routes/crm_routes.py (updated with schemas)

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.crm_service import CRMService
from app.schemas.crm_schemas import CRMParseResponse, ErrorResponse

router = APIRouter(
    prefix="/api/v1/crm",
    tags=["CRM"]
)

@router.post(
    "/parse",
    response_model=CRMParseResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file or parsing error"},
        413: {"model": ErrorResponse, "description": "File too large"}
    },
    summary="Parse CRM CSV File",
    description="Upload and parse a CRM CSV file to extract customer data and generate insights"
)
async def parse_crm_file(
    file: UploadFile = File(..., description="CSV file to parse (max 20MB)")
) -> CRMParseResponse:
    """
    Parse uploaded CSV file and return structured data with analysis
    
    - **file**: CSV file containing CRM data
    
    Returns parsed content, summary statistics, and data analysis including:
    - Industry distribution
    - Geographic distribution
    - Deal stage breakdown
    - Numeric statistics (deal amounts, company sizes)
    """
    
    # Validate file extension
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported"
        )
    
    # Read and validate file size
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    WARNING_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed size (20MB)"
        )
    
    # Parse CSV
    try:
        result = CRMService.parse_csv(content)
        
        response = CRMParseResponse(
            success=True,
            data=result
        )
        
        # Add warning for large files
        if len(content) > WARNING_FILE_SIZE:
            response.warning = f"Large file detected ({file_size_mb:.1f}MB). Processing completed successfully."
        
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
