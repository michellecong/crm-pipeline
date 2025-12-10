# schemas/product_schemas.py
"""
Pydantic schemas for product catalog generation
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal

class Product(BaseModel):
    """Individual product/service offering"""
    
    product_name: str = Field(
        ..., 
        description="Official product name",
        min_length=2
    )
    
    description: str = Field(
        ...,
        description="2-4 sentence product description focused on value and use cases",
        min_length=50
    )
    
    source_url: Optional[str] = Field(
        default=None,
        description="Official product page URL (from web search)"
    )
    
    @field_validator('product_name')
    @classmethod
    def validate_product_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("product_name must be at least 2 characters")
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if not v or len(v.strip()) < 50:
            raise ValueError("description must be at least 50 characters")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_name": "Sales Cloud",
                "description": "Complete CRM platform for managing sales pipelines, forecasting revenue, and automating sales processes. Helps sales teams close deals faster with AI-powered insights, workflow automation, and mobile access. Scales from small teams to global enterprises with customizable features and deep integration capabilities.",
                "source_url": "https://www.salesforce.com/products/sales-cloud"
            }
        }


class ProductCatalogResponse(BaseModel):
    """Complete product catalog for a seller company"""
    
    products: List[Product] = Field(
        ..., 
        description="List of products/services",
        min_length=1
    )
    
    @field_validator('products')
    @classmethod
    def validate_products_list(cls, v):
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("products must be a non-empty array")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "products": [
                {
                    "product_name": "Sales Cloud",
                    "description": "Complete CRM platform for managing sales pipelines...",
                    "source_url": "https://www.salesforce.com/products/sales-cloud"
                },
                {
                    "product_name": "Service Cloud",
                    "description": "Customer service platform for support teams...",
                    "source_url": "https://www.salesforce.com/products/service-cloud"
                }
                ]
            }
        }


class ProductGenerateRequest(BaseModel):
    """Request to generate product catalog"""
    
    company_name: str = Field(
        ...,
        description="Seller company name to analyze",
        min_length=2
    )
    
    # Optional search behavior controls (used to collect web content when needed)
    provider: Optional[Literal["google", "perplexity"]] = Field(
        default=None,
        description="Search provider (e.g., 'google' or 'perplexity')"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Salesforce"
            }
        }

