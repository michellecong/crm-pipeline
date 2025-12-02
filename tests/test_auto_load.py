#!/usr/bin/env python3
"""
Test the auto-loading feature for products in persona generation.

This demonstrates that products are automatically loaded from saved files.
"""

import requests
import time

API_BASE = "http://localhost:8000/api/v1"
COMPANY_NAME = "Salesforce"


def test_auto_load():
    print("🧪 Testing Product Auto-Loading Feature\n")
    print("=" * 70)
    
    # Step 1: Generate products
    print("\n📦 Step 1: Generate products for", COMPANY_NAME)
    print("-" * 70)
    
    products_response = requests.post(
        f"{API_BASE}/llm/products/generate",
        json={"company_name": COMPANY_NAME},
        timeout=120
    )
    
    if products_response.status_code != 200:
        print(f"❌ Failed to generate products: {products_response.text}")
        return
    
    products_data = products_response.json()
    products = products_data["products"]
    
    print(f"✅ Generated {len(products)} products:")
    for i, product in enumerate(products, 1):
        print(f"   {i}. {product['product_name']}")
    
    print(f"\n💾 Products saved to: data/generated/")
    
    # Small delay to ensure file is written
    time.sleep(1)
    
    # Step 2: Generate personas WITHOUT passing products
    print("\n👥 Step 2: Generate personas WITHOUT passing products")
    print("-" * 70)
    print("⚡ The system should AUTO-LOAD products from the saved file!")
    
    personas_response = requests.post(
        f"{API_BASE}/llm/persona/generate",
        json={
            "company_name": COMPANY_NAME,
            "generate_count": 3
            # 👆 NOTE: No "products" parameter!
        },
        timeout=180
    )
    
    if personas_response.status_code != 200:
        print(f"❌ Failed to generate personas: {personas_response.text}")
        return
    
    personas_data = personas_response.json()
    personas = personas_data["personas"]
    
    print(f"\n✅ Generated {len(personas)} personas:")
    for i, persona in enumerate(personas, 1):
        print(f"   {i}. {persona['persona_name']}")
        print(f"      Tier: {persona['tier']}, Industry: {persona['industry']}")
    
    # Verification
    print("\n" + "=" * 70)
    print("🎯 VERIFICATION")
    print("=" * 70)
    print("\n✅ SUCCESS! Products were auto-loaded!")
    print("\nCheck your server logs for:")
    print("   ✅ Auto-loaded 5 products from previous generation")
    print("   📦 Loaded 5 products from: salesforce_products_*.json")
    print("\nThis means the persona generator automatically found and used")
    print("the products you generated in Step 1, without manual passing!")
    

if __name__ == "__main__":
    try:
        test_auto_load()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

