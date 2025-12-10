#!/usr/bin/env python3
"""
Test complete CRM Pipeline flow: from data scraping to content generation
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent))

from app.controllers.scraping_controller import get_scraping_controller
from app.services.data_aggregator import get_data_aggregator
from app.services.generator_service import get_generator_service
from app.services.data_store import get_data_store
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_full_pipeline():
    """Test complete CRM Pipeline flow"""
    
    print("🚀 Starting complete CRM Pipeline flow test")
    print("=" * 60)
    
    # Test company
    company_name = "Tesla"
    
    try:
        # Step 1: Scrape data
        print(f"\n📡 Step 1: Scraping data for {company_name}...")
        controller = get_scraping_controller()
        
        scrape_result = await controller.scrape_company(
            company_name=company_name,
            include_news=True,
            include_case_studies=True,
            max_urls=5,  # Limit URLs to speed up test
            save_to_file=True  # Save to file
        )
        
        print(f"✅ Scraping completed!")
        print(f"   - URLs found: {scrape_result['total_urls_found']}")
        print(f"   - Successfully scraped: {scrape_result['successful_scrapes']}")
        print(f"   - Saved file: {scrape_result.get('saved_filepath', 'N/A')}")
        
        # Show content processing statistics
        content_processing = scrape_result.get('content_processing', {})
        print(f"   - Processed items: {content_processing.get('processed_items', 0)}/{content_processing.get('total_items', 0)}")
        
        # Step 2: Verify saved data
        print(f"\n💾 Step 2: Verifying saved data...")
        data_store = get_data_store()
        saved_data = data_store.load_latest_scraped_data(company_name)
        
        if saved_data:
            print(f"✅ Successfully loaded saved data")
            print(f"   - Company name: {saved_data['company_name']}")
            print(f"   - Official website: {saved_data.get('official_website', 'N/A')}")
            print(f"   - Content items: {len(saved_data.get('scraped_content', []))}")
            
            # Check if there's processed data
            processed_items = [item for item in saved_data.get('scraped_content', []) 
                             if 'processed_markdown' in item]
            print(f"   - Processed items: {len(processed_items)}")
            
            # Show statistics for first content item
            if processed_items:
                first_item = processed_items[0]
                print(f"   - First content item:")
                print(f"     URL: {first_item.get('url', 'N/A')}")
                print(f"     Type: {first_item.get('content_type', 'N/A')}")
                print(f"     Original length: {first_item.get('original_markdown_length', 0)}")
                print(f"     Processed length: {first_item.get('processed_markdown_length', 0)}")
                print(f"     Compression ratio: {first_item.get('compression_ratio', 0):.2f}")
        else:
            print("❌ Unable to load saved data")
            return
        
        # Step 3: Prepare context
        print(f"\n🔧 Step 3: Preparing generation context...")
        data_aggregator = get_data_aggregator()
        
        context = await data_aggregator.prepare_context(
            company_name=company_name,
            max_chars=8000,  # Limit context length
            include_news=True,
            include_case_studies=True,
            max_urls=5
        )
        
        print(f"✅ Context preparation completed!")
        print(f"   - Context length: {len(context)} characters")
        print(f"   - Context preview: {context[:200]}...")
        
        # Step 4: Generate content
        print(f"\n🎯 Step 4: Generating Persona content...")
        generator_service = get_generator_service()
        
        generation_result = await generator_service.generate(
            generator_type="personas",
            company_name=company_name,
            generate_count=2,  # Generate 2 personas
            max_context_chars=8000,
            include_news=True,
            include_case_studies=True,
            max_urls=5
        )
        
        print(f"✅ Content generation completed!")
        print(f"   - Generation result: {generation_result.get('success', False)}")
        
        if generation_result.get('success'):
            result_data = generation_result.get('result', {})
            personas = result_data.get('personas', [])
            print(f"   - Generated personas: {len(personas)}")
            print(f"   - Saved file: {generation_result.get('saved_filepath', 'N/A')}")
            
            # Show summary of first persona
            if personas:
                first_persona = personas[0]
                print(f"   - First Persona:")
                print(f"     Name: {first_persona.get('name', 'N/A')}")
                print(f"     Title: {first_persona.get('title', 'N/A')}")
                print(f"     Tier: {first_persona.get('tier', 'N/A')}")
                print(f"     Pain points: {first_persona.get('pain_points', [])[:2]}...")  # Show first 2 only
        
        # Step 5: Show complete flow summary
        print(f"\n📊 Step 5: Flow Summary")
        print("=" * 60)
        print(f"✅ Complete flow test successful!")
        print(f"   - Company: {company_name}")
        print(f"   - URLs scraped: {scrape_result['total_urls_found']}")
        print(f"   - Successfully scraped: {scrape_result['successful_scrapes']}")
        print(f"   - Content processing: {content_processing.get('processed_items', 0)} items")
        print(f"   - Context length: {len(context)} characters")
        print(f"   - Generated personas: {len(personas) if generation_result.get('success') else 0}")
        print(f"   - Saved file: {scrape_result.get('saved_filepath', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        logger.exception("Full pipeline test failed")
        return False


async def test_data_flow():
    """Test data flow"""
    print(f"\n🔍 Testing data flow...")
    
    company_name = "Tesla"
    data_store = get_data_store()
    
    # Check if saved data exists
    saved_data = data_store.load_latest_scraped_data(company_name)
    if not saved_data:
        print("❌ No saved data found, please run scraping test first")
        return False
    
    print(f"✅ Found saved data")
    
    # Check data structure
    scraped_content = saved_data.get('scraped_content', [])
    processed_items = [item for item in scraped_content if 'processed_markdown' in item]
    
    print(f"   - Total content items: {len(scraped_content)}")
    print(f"   - Processed items: {len(processed_items)}")
    
    # Show processing statistics
    if processed_items:
        total_original = sum(item.get('original_markdown_length', 0) for item in processed_items)
        total_processed = sum(item.get('processed_markdown_length', 0) for item in processed_items)
        avg_compression = total_processed / total_original if total_original > 0 else 0
        
        print(f"   - Total original length: {total_original}")
        print(f"   - Total processed length: {total_processed}")
        print(f"   - Average compression ratio: {avg_compression:.2f}")
    
    return True


if __name__ == "__main__":
    print("🧪 CRM Pipeline Complete Flow Test")
    print("=" * 60)
    
    async def main():
        # Test complete flow
        success = await test_full_pipeline()
        
        if success:
            # Test data flow
            await test_data_flow()
        
        print(f"\n🎉 Test completed!")
    
    # Run tests
    asyncio.run(main())


