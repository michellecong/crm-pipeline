"""
Test script for Product Generator with Perplexity web search
"""
import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.generator_service import get_generator_service
from app.services.llm_service import get_llm_service
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_perplexity_api_connection():
    """Test if Perplexity API is accessible"""
    logger.info("=" * 60)
    logger.info("Test 1: Perplexity API Connection")
    logger.info("=" * 60)
    
    try:
        llm_service = get_llm_service()
        
        response = await llm_service.generate_async(
            prompt="What is Python?",
            system_message="You are a helpful assistant.",
            provider="perplexity",
            max_completion_tokens=100
        )
        
        logger.info(f"✅ Perplexity API connection successful")
        logger.info(f"   Model: {response.model}")
        logger.info(f"   Content length: {len(response.content)} chars")
        logger.info(f"   Citations: {len(response.citations)}")
        logger.info(f"   Tokens used: {response.total_tokens}")
        
        if response.citations:
            logger.info(f"   Sample citation: {response.citations[0]}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Perplexity API connection failed: {e}")
        return False


async def test_product_generator_basic():
    """Test Product Generator with a simple company"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: Product Generator - Basic Test (Salesforce)")
    logger.info("=" * 60)
    
    try:
        generator_service = get_generator_service()
        
        result = await generator_service.generate(
            generator_type="products",
            company_name="Salesforce",
            generate_count=5
        )
        
        if not result.get("success"):
            logger.error(f"❌ Product generation failed")
            logger.error(f"   Result: {result}")
            return False
        
        products = result.get("result", {}).get("products", [])
        
        logger.info(f"✅ Product generation successful")
        logger.info(f"   Generated {len(products)} products")
        logger.info(f"   Model: {result.get('result', {}).get('model', 'unknown')}")
        
        # Check each product
        products_with_url = 0
        for i, product in enumerate(products):
            product_name = product.get("product_name", "Unknown")
            has_url = bool(product.get("source_url"))
            
            if has_url:
                products_with_url += 1
                logger.info(f"   Product {i+1}: {product_name}")
                logger.info(f"      URL: {product.get('source_url')}")
            else:
                logger.warning(f"   Product {i+1}: {product_name} - NO URL")
        
        logger.info(f"\n   Summary: {products_with_url}/{len(products)} products have source_url")
        
        # Save result for inspection
        output_file = "test_product_generator_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info(f"   Result saved to: {output_file}")
        
        return len(products) > 0
        
    except Exception as e:
        logger.error(f"❌ Product generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_product_generator_oracle():
    """Test Product Generator with Oracle (the example company)"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 3: Product Generator - Oracle Test")
    logger.info("=" * 60)
    
    try:
        generator_service = get_generator_service()
        
        result = await generator_service.generate(
            generator_type="products",
            company_name="Oracle",
            generate_count=10
        )
        
        if not result.get("success"):
            logger.error(f"❌ Product generation failed")
            logger.error(f"   Result: {result}")
            return False
        
        products = result.get("result", {}).get("products", [])
        
        logger.info(f"✅ Product generation successful")
        logger.info(f"   Generated {len(products)} products")
        
        # Detailed product analysis
        products_with_url = 0
        products_without_url = 0
        
        for i, product in enumerate(products[:5]):  # Show first 5
            product_name = product.get("product_name", "Unknown")
            description = product.get("description", "")
            source_url = product.get("source_url")
            
            logger.info(f"\n   Product {i+1}: {product_name}")
            logger.info(f"      Description: {description[:100]}...")
            
            if source_url:
                products_with_url += 1
                logger.info(f"      ✅ URL: {source_url}")
            else:
                products_without_url += 1
                logger.warning(f"      ❌ NO URL")
        
        logger.info(f"\n   Summary:")
        logger.info(f"      Products with URL: {products_with_url}/{len(products)}")
        logger.info(f"      Products without URL: {products_without_url}/{len(products)}")
        
        # Save result
        output_file = "test_product_generator_oracle_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info(f"   Result saved to: {output_file}")
        
        return len(products) > 0
        
    except Exception as e:
        logger.error(f"❌ Product generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_other_generators_still_use_openai():
    """Verify that other generators still use OpenAI"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 4: Verify Other Generators Use OpenAI")
    logger.info("=" * 60)
    
    try:
        llm_service = get_llm_service()
        
        # Test OpenAI (default)
        response_openai = await llm_service.generate_async(
            prompt="Say 'OpenAI test'",
            provider="openai",
            max_completion_tokens=10
        )
        
        logger.info(f"✅ OpenAI test successful")
        logger.info(f"   Model: {response_openai.model}")
        logger.info(f"   Content: {response_openai.content[:50]}")
        logger.info(f"   Citations: {len(response_openai.citations)} (should be 0 for OpenAI)")
        
        # Verify it's not Perplexity
        if "sonar" in response_openai.model.lower() or "perplexity" in response_openai.model.lower():
            logger.error(f"❌ OpenAI test returned Perplexity model: {response_openai.model}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ OpenAI test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("Starting Product Generator Perplexity Tests")
    logger.info("=" * 60 + "\n")
    
    results = []
    
    # Test 1: Perplexity API connection
    results.append(("Perplexity API Connection", await test_perplexity_api_connection()))
    
    # Test 2: Product Generator basic
    results.append(("Product Generator - Basic", await test_product_generator_basic()))
    
    # Test 3: Product Generator Oracle
    results.append(("Product Generator - Oracle", await test_product_generator_oracle()))
    
    # Test 4: Other generators use OpenAI
    results.append(("Other Generators Use OpenAI", await test_other_generators_still_use_openai()))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

