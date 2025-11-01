# schemas/crm_schemas.py

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional


class ColumnDistribution(BaseModel):
    """Distribution of values for a categorical column"""
    values: Dict[str, int] = Field(
        ...,
        description="Value counts for top 10 values",
        example={"Technology": 5, "Finance": 3, "Healthcare": 2}
    )


class NumericStats(BaseModel):
    """Statistics for numeric columns"""
    mean: float = Field(..., description="Average value")
    median: float = Field(..., description="Median value")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")
    count: int = Field(..., description="Number of non-null values")


class CRMSummary(BaseModel):
    """Summary statistics from parsed CRM data"""
    total_rows: int = Field(..., description="Total number of rows", example=300)
    total_columns: int = Field(..., description="Total number of columns", example=28)
    columns: List[str] = Field(
        ...,
        description="List of column names",
        example=["company_name", "company_industry", "deal_amount"]
    )
    preview: List[Dict[str, Any]] = Field(
        ...,
        description="First 5 rows of data",
        max_items=5
    )
    
    # Optional analysis fields
    industry_distribution: Optional[Dict[str, int]] = Field(
        None,
        description="Distribution of industries"
    )
    location_distribution: Optional[Dict[str, int]] = Field(
        None,
        description="Distribution of locations/countries"
    )
    department_distribution: Optional[Dict[str, int]] = Field(
        None,
        description="Distribution of departments"
    )
    job_title_distribution: Optional[Dict[str, int]] = Field(
        None,
        description="Distribution of job titles/functions"
    )
    deal_stage_distribution: Optional[Dict[str, int]] = Field(
        None,
        description="Distribution of deal stages"
    )
    deal_amount_stats: Optional[NumericStats] = Field(
        None,
        description="Statistics for deal amounts"
    )
    company_size_stats: Optional[NumericStats] = Field(
        None,
        description="Statistics for company sizes"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "total_rows": 300,
                "total_columns": 28,
                "columns": [
                    "company_name",
                    "company_industry",
                    "company_country",
                    "deal_amount",
                    "deal_stage"
                ],
                "preview": [
                    {
                        "company_name": "Acme Corp",
                        "company_industry": "Technology",
                        "company_country": "United States",
                        "deal_amount": 50000,
                        "deal_stage": "Qualified To Buy"
                    }
                ],
                "industry_distribution": {
                    "Technology": 120,
                    "Finance": 90,
                    "Healthcare": 60,
                    "Real Estate": 30
                },
                "location_distribution": {
                    "United States": 150,
                    "Canada": 80,
                    "United Kingdom": 70
                },
                "deal_amount_stats": {
                    "mean": 65432.10,
                    "median": 58000.00,
                    "min": 25000.00,
                    "max": 150000.00,
                    "count": 300
                }
            }
        }


class CRMParseResult(BaseModel):
    """Result from parsing a CRM CSV file"""
    full_content: str = Field(
        ...,
        description="Full CSV content as formatted text"
    )
    summary: CRMSummary = Field(
        ...,
        description="Summary statistics and analysis"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "full_content": "company_name  company_industry  deal_amount\nAcme Corp     Technology       50000\nXYZ Inc       Finance          75000",
                "summary": {
                    "total_rows": 300,
                    "total_columns": 28,
                    "columns": ["company_name", "company_industry"],
                    "preview": [{"company_name": "Acme Corp", "company_industry": "Technology"}],
                    "industry_distribution": {"Technology": 120, "Finance": 90}
                }
            }
        }


class CRMParseResponse(BaseModel):
    """API response for CRM file parsing"""
    success: bool = Field(..., description="Whether parsing was successful")
    data: Optional[CRMParseResult] = Field(None, description="Parsed data if successful")
    warning: Optional[str] = Field(None, description="Warning message if any")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "full_content": "...",
                    "summary": {
                        "total_rows": 300,
                        "total_columns": 28,
                        "industry_distribution": {"Technology": 120}
                    }
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response schema"""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Detailed error message")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": "Invalid file format",
                "detail": "Only CSV files are supported. Please upload a .csv file."
            }
        }