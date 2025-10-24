# services/generator_service.py
"""
Main service for managing generators
"""
from typing import Dict
from ..generators.base_generator import BaseGenerator
from ..generators.persona_generator import PersonaGenerator
from .data_aggregator import DataAggregator
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GeneratorService:
    """Main service for managing generators"""
    
    def __init__(self):
        self.generators: Dict[str, BaseGenerator] = {
            "personas": PersonaGenerator()
        }
        self.data_aggregator = DataAggregator()
    
    def get_generator(self, generator_type: str) -> BaseGenerator:
        """Get a generator by type"""
        if generator_type not in self.generators:
            raise ValueError(f"Unknown generator type: {generator_type}")
        return self.generators[generator_type]
    
    async def generate(self, generator_type: str, company_name: str,
                      **kwargs) -> Dict:
        """Generate content using specified generator"""
        generator = self.get_generator(generator_type)
        context = await self.data_aggregator.prepare_context(
            company_name,
            kwargs.get('max_context_chars', 15000),
            kwargs.get('include_news', True),
            kwargs.get('include_case_studies', True),
            kwargs.get('max_urls', 8)
        )
        
        result = await generator.generate(company_name, context, **kwargs)
        
        # Check if generation was successful
        success = bool(result.get('personas')) if generator_type == 'personas' else bool(result)
        
        return {
            "success": success,
            "company_name": company_name,
            "generator_type": generator_type,
            "result": result,
            "context_length": len(context),
            "generated_at": datetime.now().isoformat()
        }
    
    def get_available_generators(self) -> list:
        """Get list of available generator types"""
        return list(self.generators.keys())

# Singleton instance
_generator_service = None


def get_generator_service() -> GeneratorService:
    """Get or create GeneratorService singleton"""
    global _generator_service
    if _generator_service is None:
        _generator_service = GeneratorService()
    return _generator_service
