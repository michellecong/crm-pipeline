"""
Test suite for Baseline generation feature

Tests the baseline single-shot generation functionality including:
- Schema validation
- BaselineGenerator logic
- API endpoints
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from app.schemas.baseline_schemas import (
    BaselineGenerateRequest,
    BaselineGenerateResponse
)
from app.generators.baseline_generator import BaselineGenerator
from app.schemas.product_schemas import Product
from app.schemas.persona_schemas import BuyerPersona, PersonaTier


# Test fixtures
@pytest.fixture
def sample_baseline_response():
    """Sample baseline LLM response for testing"""
    return json.dumps({
        "products": [
            {
                "product_name": "Sales Cloud",
                "description": "Complete CRM platform for managing sales pipelines, forecasting revenue, and automating sales processes."
            },
            {
                "product_name": "Service Cloud",
                "description": "Customer service platform that unifies support channels, automates case routing, and provides agents with complete customer context."
            }
        ],
        "personas": [
            {
                "persona_name": "US Enterprise SaaS - Revenue Leaders",
                "tier": "tier_1",
                "target_decision_makers": ["CRO", "VP Sales", "VP Revenue Operations"],
                "industry": "B2B SaaS Platforms",
                "company_size_range": "2000-10000 employees",
                "company_type": "Large enterprise SaaS vendors",
                "location": "United States",
                "description": "Enterprise SaaS platforms with 200-500 sales reps. $500K-$2M annual contracts with 8-12 month sales cycles involving 6-9 stakeholders."
            }
        ],
        "personas_with_mappings": [
            {
                "persona_name": "US Enterprise SaaS - Revenue Leaders",
                "mappings": [
                    {
                        "pain_point": "Sales reps waste 30% of time on manual data entry.",
                        "value_proposition": "Sales Cloud automates 80% of CRM updates, freeing 10+ hours per rep per week."
                    }
                ]
            }
        ],
        "sequences": [
            {
                "name": "US Enterprise SaaS - Revenue Leaders Outreach",
                "persona_name": "US Enterprise SaaS - Revenue Leaders",
                "objective": "Secure discovery meeting with revenue leaders",
                "total_touches": 4,
                "duration_days": 14,
                "touches": [
                    {
                        "sort_order": 1,
                        "touch_type": "email",
                        "timing_days": 0,
                        "objective": "Introduce pipeline visibility challenge",
                        "subject_line": "30% better forecasts for enterprise teams",
                        "content_suggestion": "Hi {first_name}, many enterprise SaaS teams struggle with pipeline visibility.",
                        "hints": "Personalize with recent expansion news"
                    }
                ]
            }
        ]
    })


@pytest.fixture
def baseline_generator():
    """Fixture for BaselineGenerator"""
    return BaselineGenerator()


# Schema Tests
def test_baseline_generate_request_schema():
    """Test BaselineGenerateRequest schema validation"""
    request = BaselineGenerateRequest(
        company_name="Salesforce",
        generate_count=5
    )
    assert request.company_name == "Salesforce"
    assert request.generate_count == 5
    assert request.use_llm_search is None
    assert request.provider is None


def test_baseline_generate_request_with_options():
    """Test BaselineGenerateRequest with all options"""
    request = BaselineGenerateRequest(
        company_name="Salesforce",
        generate_count=8,
        use_llm_search=True,
        provider="google"
    )
    assert request.company_name == "Salesforce"
    assert request.generate_count == 8
    assert request.use_llm_search is True
    assert request.provider == "google"


def test_baseline_generate_request_validation():
    """Test BaselineGenerateRequest validation"""
    # Test min_length validation
    with pytest.raises(Exception):  # Pydantic validation error
        BaselineGenerateRequest(company_name="A")  # Too short
    
    # Test generate_count range validation
    with pytest.raises(Exception):
        BaselineGenerateRequest(company_name="Salesforce", generate_count=2)  # Too low
    
    with pytest.raises(Exception):
        BaselineGenerateRequest(company_name="Salesforce", generate_count=15)  # Too high


# BaselineGenerator Tests
def test_baseline_generator_initialization(baseline_generator):
    """Test BaselineGenerator initialization"""
    assert baseline_generator is not None
    assert baseline_generator.llm_service is not None


def test_get_system_message(baseline_generator):
    """Test system message generation"""
    system_message = baseline_generator.get_system_message()
    assert "B2B sales intelligence analyst" in system_message
    assert "Products" in system_message
    assert "Personas" in system_message
    assert "Mappings" in system_message
    assert "Sequences" in system_message


def test_build_prompt(baseline_generator):
    """Test prompt building"""
    company_name = "Salesforce"
    context = "Salesforce is a leading CRM platform..."
    
    prompt = baseline_generator.build_prompt(company_name, context)
    
    assert company_name in prompt
    assert context in prompt
    assert "PART 1: PRODUCTS GENERATION" in prompt
    assert "PART 2: PERSONAS GENERATION" in prompt
    assert "PART 3: MAPPINGS GENERATION" in prompt
    assert "PART 4: SEQUENCES GENERATION" in prompt


def test_parse_response_success(baseline_generator, sample_baseline_response):
    """Test successful response parsing"""
    result = baseline_generator.parse_response(sample_baseline_response)
    
    assert "products" in result
    assert "personas" in result
    assert "personas_with_mappings" in result
    assert "sequences" in result
    
    assert len(result["products"]) == 2
    assert len(result["personas"]) == 1
    assert len(result["personas_with_mappings"]) == 1
    assert len(result["sequences"]) == 1


def test_parse_response_with_markdown(baseline_generator, sample_baseline_response):
    """Test parsing response wrapped in markdown code blocks"""
    markdown_response = f"```json\n{sample_baseline_response}\n```"
    result = baseline_generator.parse_response(markdown_response)
    
    assert "products" in result
    assert len(result["products"]) == 2


def test_parse_response_missing_fields(baseline_generator):
    """Test parsing response with missing optional fields"""
    incomplete_response = json.dumps({
        "products": [{"product_name": "Test", "description": "Test product"}],
        "personas": [],
        "personas_with_mappings": [],
        "sequences": []
    })
    
    result = baseline_generator.parse_response(incomplete_response)
    
    assert len(result["products"]) == 1
    assert len(result["personas"]) == 0
    assert len(result["sequences"]) == 0


def test_parse_response_invalid_json(baseline_generator):
    """Test parsing invalid JSON"""
    invalid_json = "{ invalid json }"
    
    with pytest.raises(ValueError, match="Invalid JSON"):
        baseline_generator.parse_response(invalid_json)


# Integration Tests (mocked LLM calls)
@pytest.mark.asyncio
async def test_generate_baseline_mocked(baseline_generator):
    """Test baseline generation with mocked LLM"""
    with patch.object(baseline_generator.llm_service, 'generate_async') as mock_generate:
        # Setup mock response
        mock_response = Mock()
        mock_response.content = json.dumps({
            "products": [{"product_name": "Test", "description": "Test"}],
            "personas": [],
            "personas_with_mappings": [],
            "sequences": []
        })
        mock_response.model = "gpt-5-mini"
        
        mock_generate.return_value = mock_response
        
        # Run generation
        result = await baseline_generator.generate(
            company_name="Salesforce",
            context="Test context"
        )
        
        # Verify LLM was called
        mock_generate.assert_called_once()
        
        # Verify result structure
        assert "products" in result
        assert "model" in result


# API Endpoint Tests
def test_baseline_endpoint_existence(client):
    """Test that baseline endpoint exists and returns proper error without auth"""
    response = client.post(
        "/api/v1/llm/baseline/generate",
        json={
            "company_name": "Salesforce",
            "generate_count": 5
        }
    )
    
    # Should either succeed (200) or fail due to missing context (400/500)
    # but NOT return 404 (endpoint not found)
    assert response.status_code != 404


def test_baseline_endpoint_request_validation(client):
    """Test baseline endpoint request validation"""
    # Missing required field
    response = client.post(
        "/api/v1/llm/baseline/generate",
        json={"generate_count": 5}  # Missing company_name
    )
    assert response.status_code == 422  # Validation error
    
    # Invalid generate_count
    response = client.post(
        "/api/v1/llm/baseline/generate",
        json={"company_name": "Salesforce", "generate_count": 20}  # Too high
    )
    assert response.status_code == 422


def test_baseline_schema_alignment():
    """Test that baseline request schema aligns with pipeline"""
    from app.schemas.pipeline_schemas import PipelineGenerateRequest
    
    # Both should have same fields
    baseline_fields = set(BaselineGenerateRequest.model_fields.keys())
    pipeline_fields = set(PipelineGenerateRequest.model_fields.keys())
    
    # Fields should be identical
    assert baseline_fields == pipeline_fields
    
    # Field types should match
    assert BaselineGenerateRequest.model_fields["company_name"].annotation == \
           PipelineGenerateRequest.model_fields["company_name"].annotation
    
    assert BaselineGenerateRequest.model_fields["generate_count"].annotation == \
           PipelineGenerateRequest.model_fields["generate_count"].annotation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

