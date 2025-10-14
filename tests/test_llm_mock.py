"""
Mock Test Suite

Tests LLM service functionality without making real API calls.
Uses mock objects to simulate OpenAI responses.
"""

from unittest.mock import Mock, patch
from app.services.llm_service import LLMService, LLMConfig, LLMResponse
import os


class MockOpenAIResponse:
    """Mock OpenAI API response object."""
    
    def __init__(self, content="Mock response", model="gpt-5-mini"):
        self.choices = [
            Mock(
                message=Mock(content=content),
                finish_reason="stop"
            )
        ]
        self.model = model
        self.usage = Mock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )


def test_config_loading():
    """Test configuration loading (no API call)."""
    print("\n" + "="*60)
    print("Test 1: Configuration Loading")
    print("="*60)
    
    try:
        config = LLMConfig(
            model="gpt-5-mini",
            temperature=0.0,
            max_tokens=2000
        )
        
        print("✓ Config created successfully")
        print(f"  Model: {config.model}")
        print(f"  Temperature: {config.temperature}")
        print(f"  Max Tokens: {config.max_tokens}")
        
        # Test to_dict
        config_dict = config.to_dict()
        assert "model" in config_dict
        assert config_dict["temperature"] == 0.0
        
        print("✓ Config to_dict works")
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_llm_response_creation():
    """Test LLMResponse object creation (no API call)."""
    print("\n" + "="*60)
    print("Test 2: LLMResponse Object")
    print("="*60)
    
    try:
        response = LLMResponse(
            content="This is a test response",
            model="gpt-5-mini",
            finish_reason="stop",
            prompt_tokens=15,
            completion_tokens=25,
            total_tokens=40
        )
        
        print("✓ Response object created")
        print(f"  Content: {response.content}")
        print(f"  Total tokens: {response.total_tokens}")
        
        # Test to_dict
        response_dict = response.to_dict()
        assert "content" in response_dict
        assert "usage" in response_dict
        assert response_dict["usage"]["total_tokens"] == 40
        
        print("✓ Response to_dict works")
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_message_preparation():
    """Test message preparation (no API call)."""
    print("\n" + "="*60)
    print("Test 3: Message Preparation")
    print("="*60)
    
    try:
        # Set a dummy API key for testing
        os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mock-testing"
        
        service = LLMService()
        
        # Test user message only
        messages = service._prepare_messages("Hello, world!")
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello, world!"
        print("✓ User message preparation works")
        
        # Test with system message
        messages = service._prepare_messages(
            "Hello!",
            system_message="You are a helpful assistant."
        )
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        print("✓ System + User message preparation works")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_request_params_preparation():
    """Test request parameters preparation (no API call)."""
    print("\n" + "="*60)
    print("Test 4: Request Parameters")
    print("="*60)
    
    try:
        os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mock-testing"
        
        config = LLMConfig(temperature=0.5, max_tokens=1000)
        service = LLMService(config=config)
        
        messages = [{"role": "user", "content": "Test"}]
        params = service._prepare_request_params(messages)
        
        assert params["model"] == "gpt-5-mini"
        assert params["temperature"] == 0.5
        assert params["max_tokens"] == 1000
        assert params["messages"] == messages
        
        print("✓ Request params prepared correctly")
        print(f"  Model: {params['model']}")
        print(f"  Temperature: {params['temperature']}")
        print(f"  Max Tokens: {params['max_tokens']}")
        
        # Test parameter override
        params = service._prepare_request_params(
            messages,
            temperature=0.8,
            max_tokens=500
        )
        assert params["temperature"] == 0.8
        assert params["max_tokens"] == 500
        
        print("✓ Parameter override works")
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_mock_api_call():
    """Test complete generation flow with mocked API (no real API call)."""
    print("\n" + "="*60)
    print("Test 5: Mock API Call (Simulated)")
    print("="*60)
    
    try:
        os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mock-testing"
        
        # Create service
        service = LLMService()
        
        # Mock the OpenAI client's chat.completions.create method
        mock_response = MockOpenAIResponse(
            content="Hello! This is a simulated response from the LLM.",
            model="gpt-5-mini"
        )
        
        with patch.object(service.client.chat.completions, 'create', return_value=mock_response):
            # Make "API call" (actually mocked)
            response = service.generate(
                prompt="Say hello!",
                system_message="You are a friendly assistant."
            )
            
            print("✓ Mock API call successful")
            print(f"\n  Response content: {response.content}")
            print(f"  Model: {response.model}")
            print("  Tokens used:")
            print(f"    - Prompt: {response.prompt_tokens}")
            print(f"    - Completion: {response.completion_tokens}")
            print(f"    - Total: {response.total_tokens}")
            
            # Verify response structure
            assert response.content == "Hello! This is a simulated response from the LLM."
            assert response.total_tokens == 30
            assert response.finish_reason == "stop"
            
            print("\n✓ Response structure validated")
            return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_update():
    """Test configuration update (no API call)."""
    print("\n" + "="*60)
    print("Test 6: Configuration Update")
    print("="*60)
    
    try:
        os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mock-testing"
        
        service = LLMService()
        
        # Check initial config
        initial_temp = service.config.temperature
        print(f"  Initial temperature: {initial_temp}")
        
        # Update config
        service.update_config(temperature=0.9, max_tokens=1500)
        
        # Verify update
        assert service.config.temperature == 0.9
        assert service.config.max_tokens == 1500
        
        print("✓ Config updated successfully")
        print(f"  New temperature: {service.config.temperature}")
        print(f"  New max_tokens: {service.config.max_tokens}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_multiple_generations():
    """Test multiple generations with different prompts (mocked)."""
    print("\n" + "="*60)
    print("Test 7: Multiple Generations")
    print("="*60)
    
    try:
        os.environ["OPENAI_API_KEY"] = "sk-test-key-for-mock-testing"
        
        service = LLMService()
        
        prompts = [
            "What is Python?",
            "Explain machine learning.",
            "Write a haiku about coding."
        ]
        
        responses = []
        
        for i, prompt in enumerate(prompts, 1):
            mock_response = MockOpenAIResponse(
                content=f"Mock response {i} for: {prompt}",
                model="gpt-5-mini"
            )
            
            with patch.object(service.client.chat.completions, 'create', return_value=mock_response):
                response = service.generate(prompt)
                responses.append(response)
                print(f"  Generation {i}: ✓ Success")
        
        print(f"\n✓ Generated {len(responses)} responses")
        print(f"  Total tokens used: {sum(r.total_tokens for r in responses)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def run_all_tests():
    """Run all mock tests."""
    print("="*60)
    print("LLM Service - Mock Test Suite")
    print("(No real API calls - 100% simulated)")
    print("="*60)
    
    tests = [
        ("Configuration Loading", test_config_loading),
        ("LLMResponse Object", test_llm_response_creation),
        ("Message Preparation", test_message_preparation),
        ("Request Parameters", test_request_params_preparation),
        ("Mock API Call", test_mock_api_call),
        ("Configuration Update", test_config_update),
        ("Multiple Generations", test_multiple_generations),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            failed += 1
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Total Tests: {passed + failed}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    
    if failed == 0:
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("\n✓ Your code structure is correct!")
        print("✓ All functions work as expected!")
        print("✓ Ready for real API calls once you get the API key!")
        print("\nNext steps:")
        print("1. Get OpenAI API key from your industry partner")
        print("2. Add to .env: OPENAI_API_KEY=your-key")
        print("3. Run: python -m pytest tests/test_llm_connection.py")
        print("4. Test API endpoint: POST /api/v1/llm/test")
    else:
        print(f"\n⚠ {failed} test(s) failed - review errors above")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

