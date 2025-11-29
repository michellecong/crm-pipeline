"""
Test script for three-stage pipeline endpoint
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_three_stage_pipeline():
    """Test the three-stage pipeline endpoint"""
    
    base_url = "http://localhost:8000"
    
    # Test data
    request_data = {
        "company_name": "Asana",
        "generate_count": 3,  # Use 3 for faster testing
        "use_llm_search": True,
        "provider": "google"
    }
    
    print("=" * 80)
    print("THREE-STAGE PIPELINE TEST")
    print("=" * 80)
    print(f"\nCompany: {request_data['company_name']}")
    print(f"Persona Count: {request_data['generate_count']}")
    print(f"LLM Search: {request_data['use_llm_search']}")
    print(f"Provider: {request_data['provider']}")
    print("\n" + "=" * 80)
    
    start_time = datetime.now()
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            print("\n🚀 Calling three-stage pipeline endpoint...")
            print(f"   POST {base_url}/llm/three-stage/generate")
            
            response = await client.post(
                f"{base_url}/llm/three-stage/generate",
                json=request_data
            )
            
            response.raise_for_status()
            result = response.json()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n✅ Pipeline completed in {duration:.2f}s")
            print("\n" + "=" * 80)
            print("RESULTS SUMMARY")
            print("=" * 80)
            
            # Products
            products = result.get("products", [])
            print(f"\n📦 Products Generated: {len(products)}")
            for i, product in enumerate(products[:3], 1):
                print(f"   {i}. {product['product_name']}")
            if len(products) > 3:
                print(f"   ... and {len(products) - 3} more")
            
            # Personas
            personas = result.get("personas", [])
            print(f"\n👥 Personas Generated: {len(personas)}")
            for i, persona in enumerate(personas, 1):
                print(f"   {i}. {persona['persona_name']} ({persona['tier']})")
            
            # Mappings
            personas_with_mappings = result.get("personas_with_mappings", [])
            total_mappings = sum(len(p.get("mappings", [])) for p in personas_with_mappings)
            print(f"\n🔗 Mappings Generated: {total_mappings}")
            for i, pwm in enumerate(personas_with_mappings, 1):
                mapping_count = len(pwm.get("mappings", []))
                print(f"   {i}. {pwm['persona_name']}: {mapping_count} mappings")
            
            # Sequences
            sequences = result.get("sequences", [])
            print(f"\n📧 Outreach Sequences Generated: {len(sequences)}")
            for i, seq in enumerate(sequences, 1):
                touches = len(seq.get("touches", []))
                duration_days = seq.get("duration_days", 0)
                print(f"   {i}. {seq['name']}")
                print(f"      - {touches} touches over {duration_days} days")
            
            # Statistics
            stats = result.get("statistics", {})
            if stats:
                print("\n" + "=" * 80)
                print("STATISTICS")
                print("=" * 80)
                print(f"\n⏱️  Runtimes:")
                print(f"   - Stage 1 (Products):  {stats['stage1_runtime_seconds']:.2f}s")
                print(f"   - Stage 2 (Personas):  {stats['stage2_runtime_seconds']:.2f}s")
                print(f"   - Stage 3 (Map+Seq):   {stats['stage3_runtime_seconds']:.2f}s")
                print(f"   - TOTAL:               {stats['total_runtime_seconds']:.2f}s")
                
                print(f"\n🪙 Token Usage:")
                print(f"   - Stage 1 (Products):  {stats['stage1_tokens']:,}")
                print(f"   - Stage 2 (Personas):  {stats['stage2_tokens']:,}")
                print(f"   - Stage 3 (Map+Seq):   {stats['stage3_tokens']:,}")
                print(f"   - TOTAL:               {stats['total_tokens']:,}")
            
            # Artifacts
            artifacts = result.get("artifacts", {})
            if artifacts:
                print("\n" + "=" * 80)
                print("SAVED FILES")
                print("=" * 80)
                if artifacts.get("products_file"):
                    print(f"   📦 Products:  {artifacts['products_file']}")
                if artifacts.get("personas_file"):
                    print(f"   👥 Personas:  {artifacts['personas_file']}")
                if artifacts.get("sequences_file"):
                    print(f"   📧 Stage 3:   {artifacts['sequences_file']}")
            
            print("\n" + "=" * 80)
            print("✅ THREE-STAGE PIPELINE TEST PASSED")
            print("=" * 80)
            
            # Save full result to file for inspection
            output_file = f"test_three_stage_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Full result saved to: {output_file}")
            
            return True
            
        except httpx.HTTPStatusError as e:
            print(f"\n❌ HTTP Error: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("\nStarting three-stage pipeline test...")
    print("Make sure the server is running on http://localhost:8000")
    print("Press Ctrl+C to cancel\n")
    
    try:
        success = asyncio.run(test_three_stage_pipeline())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Test cancelled by user")
        exit(1)

