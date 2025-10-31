#!/usr/bin/env python3
"""
Test script for product catalog generator

Run this to verify the product generator is working correctly.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from app.services.generator_service import get_generator_service
from app.services.data_aggregator import get_data_aggregator
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_product_generation():
    """Test product catalog generation"""
    
    print("="*60)
    print("Testing Product Catalog Generator")
    print("="*60)
    
    company_name = "Salesforce"
    
    try:
        # Step 1: Check if scraped data exists
        print(f"\n📊 Step 1: Checking scraped data for {company_name}...")
        data_aggregator = get_data_aggregator()
        summary = data_aggregator.get_data_summary(company_name)
        
        if not summary.get("available"):
            print(f"❌ No scraped data found for {company_name}")
            print("   Please run scraping first:")
            print(f"   curl -X POST http://localhost:8000/api/v1/scrape/company \\")
            print(f"     -H 'Content-Type: application/json' \\")
            print(f"     -d '{{\"company_name\": \"{company_name}\", \"save_to_file\": true}}'")
            return False
        
        print(f"✅ Found scraped data:")
        print(f"   - Official website: {summary['official_website']}")
        print(f"   - Content items: {summary['total_content_items']}")
        print(f"   - Successful scrapes: {summary['successful_scrapes']}")
        
        # Step 2: Generate products
        print(f"\n🔧 Step 2: Generating product catalog...")
        generator_service = get_generator_service()
        
        result = await generator_service.generate(
            generator_type="products",
            company_name=company_name,
            max_products=10
        )
        
        if not result.get("success"):
            print("❌ Product generation failed")
            return False
        
        products_data = result["result"]
        products = products_data.get("products", [])
        
        print(f"✅ Generated {len(products)} products")
        print(f"   Context length: {result['context_length']} characters")
        print(f"   Generated at: {result['generated_at']}")
        
        # Step 3: Display products
        print(f"\n📦 Step 3: Product Catalog:")
        print("="*60)
        
        for i, product in enumerate(products, 1):
            print(f"\n{i}. {product['product_name']}")
            print(f"   Description ({len(product['description'])} chars):")
            print(f"   {product['description']}")
        
        print("\n" + "="*60)
        print(f"Generation Reasoning:")
        print(f"{products_data.get('generation_reasoning', 'N/A')}")
        
        # Step 4: Validation summary
        print("\n" + "="*60)
        print("✅ Validation Summary:")
        print("="*60)
        
        # Check product count
        if 3 <= len(products) <= 10:
            print(f"✅ Product count: {len(products)} (optimal range: 3-10)")
        elif len(products) < 3:
            print(f"⚠️  Product count: {len(products)} (recommend 3-10)")
        else:
            print(f"⚠️  Product count: {len(products)} (recommend focusing on core products)")
        
        # Check description lengths
        desc_lengths = [len(p['description']) for p in products]
        avg_length = sum(desc_lengths) / len(desc_lengths)
        
        if 150 <= avg_length <= 300:
            print(f"✅ Average description length: {avg_length:.0f} chars (optimal: 150-300)")
        else:
            print(f"⚠️  Average description length: {avg_length:.0f} chars (recommend: 150-300)")
        
        # Check for short descriptions
        short_descs = [p for p in products if len(p['description']) < 100]
        if short_descs:
            print(f"⚠️  {len(short_descs)} product(s) with short descriptions (< 100 chars)")
        else:
            print(f"✅ All descriptions are adequate length")
        
        # Check for long descriptions
        long_descs = [p for p in products if len(p['description']) > 500]
        if long_descs:
            print(f"⚠️  {len(long_descs)} product(s) with long descriptions (> 500 chars)")
        else:
            print(f"✅ All descriptions are concise")
        
        print("\n" + "="*60)
        print("🎉 Product Generation Test Complete!")
        print("="*60)
        
        if result.get('saved_filepath'):
            print(f"\n💾 Saved to: {result['saved_filepath']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        logger.exception("Product generation test failed")
        return False


async def main():
    """Main test function"""
    success = await test_product_generation()
    
    if success:
        print("\n✅ All tests passed!")
        print("\nNext steps:")
        print("1. Review the generated products")
        print("2. Test with other companies (HubSpot, Stripe, Shopify)")
        print("3. Use products in persona generation")
    else:
        print("\n❌ Tests failed. Please check the errors above.")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

