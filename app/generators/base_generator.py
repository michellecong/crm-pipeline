# generators/base_generator.py
"""
Base generator class for all LLM content generators
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..services.llm_service import get_llm_service
import logging

logger = logging.getLogger(__name__)

class BaseGenerator(ABC):
    """Base class for all generators"""
    
    def __init__(self):
        self.llm_service = get_llm_service()
    
    @abstractmethod
    def get_system_message(self) -> str:
        """Get the system message for this generator"""
        pass
    
    @abstractmethod
    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
        """Build the prompt for this generator"""
        pass
    
    @abstractmethod
    def parse_response(self, response: str) -> Dict:
        """Parse the LLM response into structured data"""
        pass
    
    async def generate(self, company_name: str, context: str, **kwargs) -> Dict:
        """Main generation method"""
        try:
            prompt = self.build_prompt(company_name, context, **kwargs)
            system_message = self.get_system_message()
            
            response = await self.llm_service.generate_async(
                prompt=prompt,
                system_message=system_message,
                temperature=1.0,
                max_completion_tokens=10000
            )
            
            parsed_result = self.parse_response(response.content)
            parsed_result["model"] = response.model
            return parsed_result
            
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            raise
