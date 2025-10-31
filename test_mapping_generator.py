#!/usr/bin/env python3
"""
Test the mapping generator (Regie.ai style)

This script tests the complete workflow:
1. Generate products
2. Generate personas
3. Generate pain-point to value-prop mappings
"""

import requests
import json
import sys

API_BASE = "http://localhost:8000/api/v1"
COMPANY_NAME = "Salesforce"


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_full_workflow():
    """Test the complete workflow: Products → Personas → Mappings"""
    
    print_section("TESTING MAPPING GENERATOR (Regie.ai Style)")
    
    # Step 1: Generate Products
    print_section("Step 1/3: Generate Products")
    print(f"📤 POST {API_BASE}/llm/products/generate")
    
    try:
        products_response = requests.post(
            f"{API_BASE}/llm/products/generate",
            json={"company_name": COMPANY_NAME, "max_products": 5},
            timeout=120
        )
        products_response.raise_for_status()
        products_data = products_response.json()
        products = products_data["products"]
        
        print(f"✅ Generated {len(products)} products:\n")
        for i, product in enumerate(products, 1):
            print(f"   {i}. {product['product_name']}")
            print(f"      {product['description'][:80]}...")
        
    except Exception as e:
        print(f"❌ Product generation failed: {e}")
        sys.exit(1)
    
    # Step 2: Generate Personas
    print_section("Step 2/3: Generate Personas")
    print(f"📤 POST {API_BASE}/llm/persona/generate")
    
    try:
        personas_response = requests.post(
            f"{API_BASE}/llm/persona/generate",
            json={"company_name": COMPANY_NAME, "generate_count": 3},
            timeout=180
        )
        personas_response.raise_for_status()
        personas_data = personas_response.json()
        personas = personas_data["personas"]
        
        print(f"✅ Generated {len(personas)} personas:\n")
        for i, persona in enumerate(personas, 1):
            print(f"   {i}. {persona['persona_name']}")
            print(f"      Tier: {persona['tier']}, Industry: {persona['industry']}")
        
    except Exception as e:
        print(f"❌ Persona generation failed: {e}")
        sys.exit(1)
    
    # Step 3: Generate Mappings
    print_section("Step 3/3: Generate Pain-Point to Value-Prop Mappings")
    print(f"📤 POST {API_BASE}/llm/mappings/generate")
    print("⚡ Auto-loading products and personas...\n")
    
    try:
        mappings_response = requests.post(
            f"{API_BASE}/llm/mappings/generate",
            json={"company_name": COMPANY_NAME},
            timeout=240
        )
        mappings_response.raise_for_status()
        mappings_data = mappings_response.json()
        personas_with_mappings = mappings_data["personas_with_mappings"]
        
        total_mappings = sum(len(p["mappings"]) for p in personas_with_mappings)
        
        print(f"✅ Generated mappings for {len(personas_with_mappings)} personas")
        print(f"   Total mappings: {total_mappings}\n")
        
        # Display mappings
        for i, persona_data in enumerate(personas_with_mappings, 1):
            print(f"\n{'─' * 80}")
            print(f"Persona {i}: {persona_data['persona_name']}")
            print(f"{'─' * 80}\n")
            
            for j, mapping in enumerate(persona_data['mappings'], 1):
                print(f"  Mapping {j}:")
                print(f"  Pain Point:")
                print(f"    {mapping['pain_point']}")
                print(f"  Value Proposition:")
                print(f"    {mapping['value_proposition']}")
                print()
        
        # Validation
        print_section("VALIDATION")
        
        all_valid = True
        
        for persona_data in personas_with_mappings:
            persona_name = persona_data['persona_name']
            mappings = persona_data['mappings']
            
            if len(mappings) < 3 or len(mappings) > 10:
                print(f"⚠️  {persona_name}: Has {len(mappings)} mappings (expected 3-10)")
                all_valid = False
            
            for j, mapping in enumerate(mappings):
                pain_len = len(mapping['pain_point'])
                value_len = len(mapping['value_proposition'])
                
                if pain_len > 300:
                    print(f"⚠️  {persona_name} Mapping {j+1}: Pain point too long ({pain_len} chars)")
                    all_valid = False
                
                if value_len > 300:
                    print(f"⚠️  {persona_name} Mapping {j+1}: Value prop too long ({value_len} chars)")
                    all_valid = False
                
                # Check if product is integrated in value prop
                has_product = any(p['product_name'].lower() in mapping['value_proposition'].lower() 
                                 for p in products)
                if not has_product:
                    print(f"⚠️  {persona_name} Mapping {j+1}: No product name found in value prop")
                    all_valid = False
        
        if all_valid:
            print("✅ All mappings passed validation!")
        else:
            print("\n⚠️  Some validation warnings found (see above)")
        
        print_section("✅ TEST COMPLETE")
        print("All three generators working successfully!")
        print("\nWorkflow:")
        print("  1. ✅ Products generated")
        print("  2. ✅ Personas generated (with products)")
        print("  3. ✅ Mappings generated (with products + personas)")
        print("\nStyle: Regie.ai format")
        print("  - Concise pain points (<300 chars)")
        print("  - Product-integrated value props (<300 chars)")
        print("  - 3-10 mappings per persona")
        
    except Exception as e:
        print(f"❌ Mapping generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        test_full_workflow()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

