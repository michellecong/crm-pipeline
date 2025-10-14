#!/usr/bin/env python3
"""
Quick verification script to check if everything is set up correctly.
This checks the codebase structure without requiring an API key.
"""

print("="*60)
print("LLM Service Setup Verification")
print("="*60)

# Test 1: Check imports
print("\n[1/5] Testing imports...")
try:
    from app.services.llm_service import LLMConfig, LLMResponse
    from app.schemas.llm_schema import LLMGenerateRequest
    from app.config import settings
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    exit(1)

# Test 2: Check configuration
print("\n[2/5] Checking configuration...")
try:
    config = LLMConfig()
    print("✓ LLMConfig created successfully")
    print(f"  - Model: {config.model}")
    print(f"  - Temperature: {config.temperature}")
    print(f"  - Max tokens: {config.max_tokens}")
    
    assert config.model == "gpt-5-mini", f"Expected gpt-5-mini, got {config.model}"
    print("✓ Default model is gpt-5-mini")
except Exception as e:
    print(f"✗ Configuration test failed: {e}")
    exit(1)

# Test 3: Test LLMResponse
print("\n[3/5] Testing LLMResponse...")
try:
    response = LLMResponse(
        content="Test response",
        model="gpt-5-mini",
        finish_reason="stop",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30
    )
    print("✓ LLMResponse created successfully")
    print(f"  - Content length: {len(response.content)} chars")
    print(f"  - Total tokens: {response.total_tokens}")
    
    response_dict = response.to_dict()
    assert "content" in response_dict
    assert "usage" in response_dict
    print("✓ Response to_dict() works")
except Exception as e:
    print(f"✗ LLMResponse test failed: {e}")
    exit(1)

# Test 4: Check Pydantic schemas
print("\n[4/5] Testing Pydantic schemas...")
try:
    request = LLMGenerateRequest(
        prompt="Test prompt",
        temperature=0.5,
        max_tokens=100
    )
    print("✓ LLMGenerateRequest validated successfully")
    print(f"  - Prompt length: {len(request.prompt)} chars")
    print(f"  - Temperature: {request.temperature}")
except Exception as e:
    print(f"✗ Schema test failed: {e}")
    exit(1)

# Test 5: Check API key status
print("\n[5/5] Checking API key status...")
if settings.OPENAI_API_KEY:
    print(f"✓ API key is configured: {settings.OPENAI_API_KEY[:8]}...")
    print("  You can test real LLM calls!")
else:
    print("⚠ API key NOT configured yet")
    print("  This is expected - waiting for industry partner")
    print("  All code structure is ready!")

# Summary
print("\n" + "="*60)
print("🎉 VERIFICATION SUCCESSFUL!")
print("="*60)
print("\n✓ Code structure is correct")
print("✓ All imports working")
print("✓ Configuration properly set up")
print("✓ Schemas validated")
print("✓ Default model: gpt-5-mini")

if not settings.OPENAI_API_KEY:
    print("\n📝 Next steps:")
    print("1. Wait for API key from industry partner")
    print("2. Add to .env file: OPENAI_API_KEY=your-key")
    print("3. Test connection: python tests/test_llm_connection.py")
    print("4. Test API: curl http://localhost:8000/api/v1/llm/test")
else:
    print("\n🚀 You're ready to go!")
    print("   Run: python tests/test_llm_connection.py")

print("\n" + "="*60)

