"""
LLM Service Module

Handles all interactions with OpenAI's API for language model operations.
Provides a clean interface for making requests and processing responses.
"""

import asyncio
from typing import Optional, Dict, Any, List
from openai import OpenAI
import logging

from ..config import settings

# Configure module logger
logger = logging.getLogger(__name__)


class LLMConfig:
    """
    Configuration settings for the LLM service.
    
    Attributes:
        model: The OpenAI model identifier to use
        temperature: Controls randomness in responses (0.0 = deterministic, 2.0 = very random)
        max_tokens: Maximum number of tokens in the response
        top_p: Nucleus sampling parameter
        frequency_penalty: Penalty for token frequency (-2.0 to 2.0)
        presence_penalty: Penalty for token presence (-2.0 to 2.0)
    """
    
    def __init__(
        self,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        frequency_penalty: float = None,
        presence_penalty: float = None
    ):
        # Use settings from config if not provided
        self.model = model if model is not None else settings.OPENAI_MODEL
        self.temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
        self.max_tokens = max_tokens if max_tokens is not None else settings.OPENAI_MAX_TOKENS
        self.top_p = top_p if top_p is not None else settings.OPENAI_TOP_P
        self.frequency_penalty = frequency_penalty if frequency_penalty is not None else settings.OPENAI_FREQUENCY_PENALTY
        self.presence_penalty = presence_penalty if presence_penalty is not None else settings.OPENAI_PRESENCE_PENALTY
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty
        }


class LLMResponse:
    """
    Represents a response from the LLM.
    
    Attributes:
        content: The generated text content
        model: The model that generated the response
        finish_reason: Reason why the generation stopped
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total number of tokens used
    """
    
    def __init__(
        self,
        content: str,
        model: str,
        finish_reason: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int
    ):
        self.content = content
        self.model = model
        self.finish_reason = finish_reason
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        return {
            "content": self.content,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "usage": {
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens
            }
        }


class LLMService:
    """
    Service for interacting with OpenAI's Language Models.
    
    Handles authentication, request preparation, sending requests,
    and processing responses from OpenAI's API.
    """
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None):
        """
        Initialize the LLM service.
        
        Args:
            api_key: OpenAI API key. If not provided, reads from settings
            config: LLM configuration settings. If not provided, uses defaults from settings
            
        Raises:
            ValueError: If API key is not provided and not found in settings
        """
        self.api_key = self._get_api_key(api_key)
        self.config = config if config else LLMConfig()
        self.client = self._initialize_client()
        
        logger.info(f"LLM Service initialized with model: {self.config.model}")
    
    def _get_api_key(self, api_key: Optional[str]) -> str:
        """
        Retrieve API key from parameter or settings.
        
        Args:
            api_key: API key passed as parameter
            
        Returns:
            Valid API key string
            
        Raises:
            ValueError: If API key is not found
        """
        if api_key:
            return api_key
        
        # Try to get from settings
        if settings.OPENAI_API_KEY:
            return settings.OPENAI_API_KEY
        
        raise ValueError(
            "OpenAI API key is required. "
            "Set OPENAI_API_KEY in .env file or environment variable."
        )
    
    def _initialize_client(self) -> OpenAI:
        """
        Initialize the OpenAI client with the API key.
        
        Returns:
            Configured OpenAI client instance
        """
        return OpenAI(api_key=self.api_key)
    
    def _prepare_messages(
        self,
        prompt: str,
        system_message: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Prepare message array for the API request.
        
        Args:
            prompt: The user's prompt text
            system_message: Optional system message to set context
            
        Returns:
            List of message dictionaries in OpenAI format
        """
        messages = []
        
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return messages
    
    def _prepare_request_params(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Prepare the complete request parameters for the API call.
        
        Args:
            messages: List of messages to send
            temperature: Override default temperature if provided
            max_tokens: Override default max_tokens if provided
            
        Returns:
            Dictionary of request parameters
        """
        params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty
        }
        
        return params
    
    def _send_request(self, params: Dict[str, Any]):
        """
        Send the request to OpenAI's API.
        
        Args:
            params: Request parameters dictionary
            
        Returns:
            Raw API response object
            
        Raises:
            Exception: If API request fails
        """
        try:
            logger.debug(f"Sending request to OpenAI API with model: {params['model']}")
            response = self.client.chat.completions.create(**params)
            logger.debug("Request successful")
            return response
            
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            raise
    
    def _process_response(self, raw_response) -> LLMResponse:
        """
        Process the raw API response into a structured LLMResponse object.
        
        Args:
            raw_response: Raw response from OpenAI API
            
        Returns:
            Structured LLMResponse object
        """
        choice = raw_response.choices[0]
        usage = raw_response.usage
        
        response = LLMResponse(
            content=choice.message.content,
            model=raw_response.model,
            finish_reason=choice.finish_reason,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens
        )
        
        logger.info(
            f"Response processed: {response.total_tokens} tokens used "
            f"(prompt: {response.prompt_tokens}, completion: {response.completion_tokens})"
        )
        
        return response
    
    def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Generate a completion from the language model (synchronous).
        
        This is the main public interface for generating text. It handles the complete
        workflow: preparing the request, sending it, and processing the response.
        
        Args:
            prompt: The text prompt to send to the model
            system_message: Optional system message to set context/behavior
            temperature: Override default temperature for this request
            max_tokens: Override default max_tokens for this request
            
        Returns:
            LLMResponse object containing the generated text and metadata
            
        Raises:
            Exception: If request fails at any stage
            
        Example:
            >>> service = LLMService()
            >>> response = service.generate("What is Python?")
            >>> print(response.content)
        """
        # Step 1: Prepare messages
        messages = self._prepare_messages(prompt, system_message)
        
        # Step 2: Prepare request parameters
        params = self._prepare_request_params(messages, temperature, max_tokens)
        
        # Step 3: Send request
        raw_response = self._send_request(params)
        
        # Step 4: Process response
        response = self._process_response(raw_response)
        
        return response
    
    async def generate_async(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Generate a completion from the language model (asynchronous).
        
        This async version wraps the synchronous OpenAI call to work with FastAPI.
        
        Args:
            prompt: The text prompt to send to the model
            system_message: Optional system message to set context/behavior
            temperature: Override default temperature for this request
            max_tokens: Override default max_tokens for this request
            
        Returns:
            LLMResponse object containing the generated text and metadata
            
        Example:
            >>> service = LLMService()
            >>> response = await service.generate_async("What is Python?")
            >>> print(response.content)
        """
        # Run the synchronous generate method in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.generate(prompt, system_message, temperature, max_tokens)
        )
    
    def update_config(self, **kwargs):
        """
        Update configuration parameters.
        
        Args:
            **kwargs: Configuration parameters to update
            
        Example:
            >>> service.update_config(temperature=0.8, max_tokens=1000)
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated config: {key} = {value}")
            else:
                logger.warning(f"Unknown configuration parameter: {key}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration as dictionary.
        
        Returns:
            Dictionary of current configuration settings
        """
        return self.config.to_dict()


# Singleton instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get or create LLMService singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

