"""
LLM Service Module

Handles all interactions with OpenAI's API for language model operations.
Provides a clean interface for making requests and processing responses.
"""

import asyncio
from typing import Optional, Dict, Any, List, Literal
from openai import OpenAI
import aiohttp
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
        max_completion_tokens: Maximum number of tokens in the response
    """
    
    def __init__(
        self,
        model: str = None,
        temperature: float = None,
        max_completion_tokens: int = None
    ):
        # Use settings from config if not provided
        self.model = model if model is not None else settings.OPENAI_MODEL
        self.temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
        self.max_completion_tokens = max_completion_tokens if max_completion_tokens is not None else settings.OPENAI_MAX_COMPLETION_TOKENS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_completion_tokens": self.max_completion_tokens
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
        citations: Optional list of citations/source URLs (from Perplexity)
    """
    
    def __init__(
        self,
        content: str,
        model: str,
        finish_reason: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        citations: Optional[List[Dict[str, str]]] = None
    ):
        self.content = content
        self.model = model
        self.finish_reason = finish_reason
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.citations = citations or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        result = {
            "content": self.content,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "usage": {
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens
            }
        }
        if self.citations:
            result["citations"] = self.citations
        return result


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
        self.client = self._initialize_client() # Initialize the OpenAI client
        
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
        max_completion_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Prepare the complete request parameters for the API call.
        
        Args:
            messages: List of messages to send
            temperature: Override default temperature if provided
            max_completion_tokens: Override default max_completion_tokens if provided
            
        Returns:
            Dictionary of request parameters
        """
        params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_completion_tokens": max_completion_tokens if max_completion_tokens is not None else self.config.max_completion_tokens,
            "response_format": {"type": "text"}
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
            content=choice.message.content if choice.message.content is not None else "",
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
        max_completion_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Generate a completion from the language model (synchronous).
        
        This is the main public interface for generating text. It handles the complete
        workflow: preparing the request, sending it, and processing the response.
        
        Args:
            prompt: The text prompt to send to the model
            system_message: Optional system message to set context/behavior
            temperature: Override default temperature for this request
            max_completion_tokens: Override default max_completion_tokens for this request
            
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
        params = self._prepare_request_params(messages, temperature, max_completion_tokens)
        
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
        max_completion_tokens: Optional[int] = None,
        provider: Literal["openai", "perplexity"] = "openai"
    ) -> LLMResponse:
        """
        Generate a completion from the language model (asynchronous).
        
        This async version wraps the synchronous OpenAI call to work with FastAPI.
        Supports both OpenAI and Perplexity providers.
        
        Args:
            prompt: The text prompt to send to the model
            system_message: Optional system message to set context/behavior
            temperature: Override default temperature for this request
            max_completion_tokens: Override default max_completion_tokens for this request
            provider: LLM provider to use ("openai" or "perplexity")
            
        Returns:
            LLMResponse object containing the generated text and metadata
            
        Example:
            >>> service = LLMService()
            >>> response = await service.generate_async("What is Python?")
            >>> print(response.content)
        """
        if provider == "perplexity":
            return await self._generate_perplexity_async(
                prompt, system_message, temperature, max_completion_tokens
            )
        else:
            # Run the synchronous generate method in a thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self.generate(prompt, system_message, temperature, max_completion_tokens)
            )
    
    def update_config(self, **kwargs):
        """
        Update configuration parameters.
        
        Args:
            **kwargs: Configuration parameters to update
            
        Example:
            >>> service.update_config(temperature=0.8, max_completion_tokens=1000)
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
    
    async def _generate_perplexity_async(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_completion_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Generate a completion using Perplexity API (asynchronous).
        
        Args:
            prompt: The text prompt to send to the model
            system_message: Optional system message to set context/behavior
            temperature: Override default temperature for this request
            max_completion_tokens: Override default max_completion_tokens for this request
            
        Returns:
            LLMResponse object containing the generated text, metadata, and citations
            
        Raises:
            ValueError: If Perplexity API key is not configured
            Exception: If API request fails
        """
        if not settings.PERPLEXITY_API_KEY:
            raise ValueError(
                "Perplexity API key is required for web search. "
                "Set PERPLEXITY_API_KEY in .env file or environment variable."
            )
        
        # Prepare messages
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request parameters
        model = settings.PERPLEXITY_MODEL
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_completion_tokens if max_completion_tokens is not None else self.config.max_completion_tokens,
        }
        
        # Send request to Perplexity API
        url = f"{settings.PERPLEXITY_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.debug(f"Sending request to Perplexity API with model: {model}")
            # Disable SSL verification to avoid certificate issues on macOS
            ssl_context = False  # Disables SSL verification
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=params, ssl=ssl_context) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Process Perplexity response
                    choice = data["choices"][0]
                    message = choice["message"]
                    usage = data.get("usage", {})
                    
                    # Extract citations from Perplexity response
                    citations = []
                    if "citations" in message:
                        citations = message["citations"]
                    elif "citations" in data:
                        citations = data["citations"]
                    
                    # Convert citations to standard format
                    formatted_citations = []
                    if citations:
                        for citation in citations:
                            if isinstance(citation, dict):
                                formatted_citations.append({
                                    "url": citation.get("url", ""),
                                    "title": citation.get("title", "")
                                })
                            elif isinstance(citation, str):
                                formatted_citations.append({"url": citation, "title": ""})
                    
                    llm_response = LLMResponse(
                        content=message.get("content", ""),
                        model=data.get("model", model),
                        finish_reason=choice.get("finish_reason", "stop"),
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                        citations=formatted_citations
                    )
                    
                    logger.info(
                        f"Perplexity response processed: {llm_response.total_tokens} tokens used "
                        f"(prompt: {llm_response.prompt_tokens}, completion: {llm_response.completion_tokens}), "
                        f"{len(formatted_citations)} citations"
                    )
                    
                    return llm_response
                    
        except aiohttp.ClientError as e:
            logger.error(f"Perplexity API request failed: {str(e)}")
            raise Exception(f"Perplexity API request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error calling Perplexity API: {str(e)}")
            raise

# Singleton instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get or create LLMService singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
