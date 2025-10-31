"""
Test script for the new structured LLM web search functionality.
This demonstrates how to use both the freeform and structured versions.
"""
import asyncio
import json
from app.services.llm_web_search_service import (
    llm_company_web_search_freeform,
    llm_company_web_search_structured
)


async def test_freeform_search():
    """Test the freeform search that returns JSON string"""
    print("=" * 80)
    print("Testing Freeform Search (returns JSON string)")
    print("=" * 80)
    
    company_name = "Salesforce"
    print(f"\nSearching for: {company_name}\n")
    
    try:
        result = await llm_company_web_search_freeform(company_name)
        print("Raw JSON Response:")
        print("-" * 80)
        
        # Pretty print the JSON
        parsed = json.loads(result)
        print(json.dumps(parsed, indent=2))
        
        print("\n" + "=" * 80)
        print("✓ Freeform search completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Error in freeform search: {e}")


async def test_structured_search():
    """Test the structured search that returns Pydantic object"""
    print("\n\n")
    print("=" * 80)
    print("Testing Structured Search (returns validated Pydantic object)")
    print("=" * 80)
    
    company_name = "DocuSign"
    print(f"\nSearching for: {company_name}\n")
    
    try:
        result = await llm_company_web_search_structured(company_name)
        
        print("Structured Response:")
        print("-" * 80)
        print(f"Company: {result.company}")
        print(f"Collected at: {result.collected_at}")
        
        print(f"\nQueries Planned ({len(result.queries_planned)}):")
        for i, query in enumerate(result.queries_planned, 1):
            print(f"  {i}. {query}")
        
        print(f"\nOfficial Website ({len(result.official_website)} items):")
        for item in result.official_website:
            print(f"  • {item.title or 'No title'}")
            print(f"    URL: {item.url}")
        
        print(f"\nProducts ({len(result.products)} items):")
        for item in result.products[:3]:  # Show first 3
            print(f"  • {item.title or 'No title'}")
            print(f"    URL: {item.url}")
        
        print(f"\nNews ({len(result.news)} items):")
        for item in result.news[:3]:  # Show first 3
            print(f"  • {item.title or 'No title'}")
            print(f"    URL: {item.url}")
            if item.published_at:
                print(f"    Published: {item.published_at}")
        
        print(f"\nCase Studies ({len(result.case_studies)} items):")
        for item in result.case_studies[:3]:  # Show first 3
            print(f"  • {item.title or 'No title'}")
            print(f"    URL: {item.url}")
        
        print("\n" + "=" * 80)
        print("✓ Structured search completed successfully!")
        print("✓ Official website validation passed!")
        print("=" * 80)
        
        # Convert to dict to show full JSON representation
        print("\nFull JSON representation:")
        print("-" * 80)
        print(json.dumps(result.model_dump(), indent=2))
        
    except ValueError as e:
        print(f"\n✗ Validation Error: {e}")
    except Exception as e:
        print(f"\n✗ Error in structured search: {e}")


async def main():
    """Run all tests"""
    print("\n")
    print("*" * 80)
    print("LLM Web Search Service - Test Suite")
    print("*" * 80)
    
    # Test freeform version
    await test_freeform_search()
    
    # Test structured version
    await test_structured_search()
    
    print("\n\n")
    print("*" * 80)
    print("All tests completed!")
    print("*" * 80)


if __name__ == "__main__":
    asyncio.run(main())

