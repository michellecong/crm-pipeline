"""
Test script to verify pipeline stats tracking (timing and costs)
"""
import asyncio
import httpx
import json

async def test_pipeline_stats():
    """Test the pipeline generation with stats tracking"""
    
    url = "http://localhost:8000/api/v1/llm/pipeline/generate"
    
    payload = {
        "company_name": "Asana",
        "generate_count": 3  # Use smaller count for faster test
    }
    
    print(f"🚀 Testing pipeline generation for {payload['company_name']}...")
    print(f"   Generating {payload['generate_count']} personas")
    print()
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Display results summary
            print("✅ Pipeline generation successful!")
            print()
            
            payload_data = data.get("payload", {})
            stats = data.get("stats", {})
            
            # Display counts
            print("📊 Generated Content:")
            print(f"   Products: {len(payload_data.get('products', []))}")
            print(f"   Personas: {len(payload_data.get('personas', []))}")
            print(f"   Mappings: {len(payload_data.get('personas_with_mappings', []))}")
            print(f"   Sequences: {len(payload_data.get('sequences', []))}")
            print()
            
            # Display stats
            if stats:
                print("⏱️  Performance Breakdown:")
                print("━" * 80)
                
                stages = stats.get("stages", [])
                for stage in stages:
                    stage_name = stage.get("stage_name", "unknown").capitalize()
                    duration = stage.get("duration_seconds", 0)
                    tokens = stage.get("total_tokens", 0)
                    model = stage.get("model", "unknown")
                    
                    print(f"   {stage_name:12} | {duration:6.2f}s | {tokens:8,} tokens | {model}")
                
                print("━" * 80)
                
                # Display totals
                total_duration = stats.get("total_duration_seconds", 0)
                total_tokens = stats.get("total_tokens", 0)
                
                print(f"   {'TOTAL':12} | {total_duration:6.2f}s | {total_tokens:8,} tokens")
                print("━" * 80)
                print()
                
                # Per-stage breakdown
                print("📈 Stage Details:")
                for stage in stages:
                    stage_name = stage.get("stage_name", "unknown").capitalize()
                    prompt_tokens = stage.get("prompt_tokens", 0)
                    completion_tokens = stage.get("completion_tokens", 0)
                    
                    print(f"   {stage_name}:")
                    print(f"      Input:  {prompt_tokens:,} tokens")
                    print(f"      Output: {completion_tokens:,} tokens")
                
                print()
                
                # Efficiency metrics
                avg_tokens_per_stage = total_tokens / len(stages) if stages else 0
                tokens_per_second = total_tokens / total_duration if total_duration > 0 else 0
                
                print("💡 Efficiency Metrics:")
                print(f"   Average tokens per stage: {avg_tokens_per_stage:,.1f}")
                print(f"   Tokens per second:        {tokens_per_second:,.1f}")
            else:
                print("⚠️  No stats data available")
            
            print()
            print("✨ Test completed successfully!")
            
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP error: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_pipeline_stats())

