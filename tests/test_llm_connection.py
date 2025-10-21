"""
LLM Connection Test

Tests if the LLM service can successfully connect to OpenAI's API.
Requires valid OPENAI_API_KEY in .env file.
"""

from app.services.llm_service import LLMService, LLMConfig
from app.config import settings


def test_api_connection():
    """
    Test if API connection works with a simple request.
    """
    print("=" * 60)
    print("LLM Service - API Connection Test")
    print("=" * 60)
    
    # Step 1: Check configuration
    print("\n[1/4] Checking configuration...")
    assert settings.OPENAI_API_KEY, (
        "OPENAI_API_KEY not found in settings\n"
        "To fix this:\n"
        "1. Create/update .env file in project root\n"
        "2. Add: OPENAI_API_KEY=your-api-key-here\n"
        "3. Restart and run this test again"
    )
    
    print(f"✓ API key found: {settings.OPENAI_API_KEY[:8]}...")
    print(f"  Model: {settings.OPENAI_MODEL}")
    print(f"  Temperature: {settings.OPENAI_TEMPERATURE}")
    print(f"  Max Completion Tokens: {settings.OPENAI_MAX_COMPLETION_TOKENS}")
    
    # Step 2: Initialize service
    print("\n[2/4] Initializing LLM service...")
    # Use gpt-5-mini for testing
    llm_config = LLMConfig(
        model="gpt-5-mini",
        temperature=1.0,
        max_completion_tokens=500  # Give it plenty of room
    )
    service = LLMService(config=llm_config)
    print("✓ Service initialized successfully")
    
    # Step 3: Make test request
    print("\n[3/4] Sending test request to OpenAI...")
    response = service.generate(
        prompt="Say hello"
    )
    
    # Step 4: Check response
    print("\n[4/4] Processing response...")
    print(f"✓ Response received!")
    print(f"\nResponse Content:")
    print(f"  {response.content}")
    print(f"\nToken Usage:")
    print(f"  Prompt tokens: {response.prompt_tokens}")
    print(f"  Completion tokens: {response.completion_tokens}")
    print(f"  Total tokens: {response.total_tokens}")
    print(f"\nModel: {response.model}")
    print(f"Finish reason: {response.finish_reason}")
    
    print("\n" + "=" * 60)
    print("✓ API CONNECTION TEST PASSED")
    print("=" * 60)
    print("\n✓ Everything is working! You're ready to use the LLM service.")
    
    # Assert the response is valid
    assert response.total_tokens > 0, "Token usage should be greater than 0"
    assert response.completion_tokens > 0, "Should have generated completion tokens"
    assert response.content and len(response.content.strip()) > 0, "Response content should not be empty"
    assert response.finish_reason == "stop", f"Expected finish_reason 'stop' but got '{response.finish_reason}'"


if __name__ == "__main__":
    try:
        test_api_connection()
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Connection Error: {e}")
        print("\nPossible issues:")
        print("1. Invalid API key")
        print("2. Network connection problem")
        print("3. OpenAI service is down")
        print("4. API quota exceeded")
        exit(1)

