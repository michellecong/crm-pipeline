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
    
    try:
        # Step 1: Check configuration
        print("\n[1/4] Checking configuration...")
        if not settings.OPENAI_API_KEY:
            print("✗ OPENAI_API_KEY not found in settings")
            print("\nTo fix this:")
            print("1. Create/update .env file in project root")
            print("2. Add: OPENAI_API_KEY=your-api-key-here")
            print("3. Restart and run this test again")
            return False
        
        print(f"✓ API key found: {settings.OPENAI_API_KEY[:8]}...")
        print(f"  Model: {settings.OPENAI_MODEL}")
        print(f"  Temperature: {settings.OPENAI_TEMPERATURE}")
        print(f"  Max Tokens: {settings.OPENAI_MAX_TOKENS}")
        
        # Step 2: Initialize service
        print("\n[2/4] Initializing LLM service...")
        # Use gpt-3.5-turbo for testing (faster and cheaper)
        llm_config = LLMConfig(
            model="gpt-3.5-turbo",
            temperature=0.0,
            max_tokens=50
        )
        service = LLMService(config=llm_config)
        print("✓ Service initialized successfully")
        
        # Step 3: Make test request
        print("\n[3/4] Sending test request to OpenAI...")
        response = service.generate(
            prompt="Say 'Connection successful!' if you can read this."
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
        
        print("\n" + "=" * 60)
        print("✓ API CONNECTION TEST PASSED")
        print("=" * 60)
        print("\n✓ Everything is working! You're ready to use the LLM service.")
        
        return True
        
    except ValueError as e:
        print(f"\n✗ Configuration Error: {e}")
        print("\nTo fix this:")
        print("1. Make sure .env file exists in project root")
        print("2. Verify OPENAI_API_KEY is set in .env")
        print("3. Or set environment variable: export OPENAI_API_KEY='your-key'")
        return False
        
    except Exception as e:
        print(f"\n✗ Connection Error: {e}")
        print("\nPossible issues:")
        print("1. Invalid API key")
        print("2. Network connection problem")
        print("3. OpenAI service is down")
        print("4. API quota exceeded")
        return False


if __name__ == "__main__":
    success = test_api_connection()
    
    if not success:
        exit(1)

