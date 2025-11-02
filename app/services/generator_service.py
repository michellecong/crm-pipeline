from typing import Dict
from ..generators.base_generator import BaseGenerator
from ..generators.persona_generator import PersonaGenerator
from ..generators.product_generator import ProductGenerator
from ..generators.mapping_generator import MappingGenerator
from ..generators.outreach_generator import OutreachGenerator
from .data_aggregator import DataAggregator
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GeneratorService:
    """Main service for managing generators"""
    
    def __init__(self):
        self.generators: Dict[str, BaseGenerator] = {
            "personas": PersonaGenerator(),
            "products": ProductGenerator(),
            "mappings": MappingGenerator(),
            "outreach": OutreachGenerator()
        }
        self.data_aggregator = DataAggregator()
    
    def get_generator(self, generator_type: str) -> BaseGenerator:
        """Get a generator by type"""
        if generator_type not in self.generators:
            raise ValueError(f"Unknown generator type: {generator_type}")
        return self.generators[generator_type]
    
    async def generate(self, generator_type: str, company_name: str, **kwargs) -> Dict:
        """
        Generate content using specified generator.
        
        For personas: Generates buyer company archetypes (market segments)
        Auto-injects products if available and not explicitly provided.
        
        For mappings: Auto-injects products and personas if not provided.
        
        For outreach: Uses personas_with_mappings from kwargs directly.
        """
        generator = self.get_generator(generator_type)
        
        # Auto-inject products for persona generation if not provided
        if generator_type == "personas" and "products" not in kwargs:
            products = self._load_latest_products(company_name)
            if products:
                kwargs["products"] = products
                logger.info(f"✅ Auto-loaded {len(products)} products from previous generation")
            else:
                logger.info("ℹ️  No saved products found. Generating personas from web content only.")
        
        # Auto-inject products and personas for mapping generation if not provided
        if generator_type == "mappings":
            if "products" not in kwargs:
                products = self._load_latest_products(company_name)
                if products:
                    kwargs["products"] = products
                    logger.info(f"✅ Auto-loaded {len(products)} products for mapping generation")
                else:
                    logger.warning("⚠️  No saved products found. Mappings may be less specific.")
            
            if "personas" not in kwargs:
                personas = self._load_latest_personas(company_name)
                if personas:
                    kwargs["personas"] = personas
                    logger.info(f"✅ Auto-loaded {len(personas)} personas for mapping generation")
                else:
                    logger.warning("⚠️  No saved personas found. Cannot generate mappings without personas.")
                    raise ValueError("Personas are required for mapping generation. Please generate personas first.")
        
        # For outreach, use minimal context (personas_with_mappings provides the data)
        if generator_type == "outreach":
            if "personas_with_mappings" not in kwargs:
                raise ValueError("personas_with_mappings is required for outreach generation")
            context = f"Generating outreach sequences for {company_name}"
        else:
            context = await self.data_aggregator.prepare_context(
                company_name,
                kwargs.get('max_context_chars', 15000),
                kwargs.get('include_news', True),
                kwargs.get('include_case_studies', True),
                kwargs.get('max_urls', 10),
                kwargs.get('use_llm_search', False),
                kwargs.get('provider', 'google')
            )
        
        logger.info(f"Prepared context length: {len(context)} chars for {company_name}")
        
        result = await generator.generate(company_name, context, **kwargs)
        
        # Check if generation was successful
        if generator_type == 'personas':
            success = bool(result.get('personas'))
        elif generator_type == 'outreach':
            success = bool(result.get('sequences'))
        else:
            success = bool(result)
        
        # Save generated content to file
        saved_filepath = None
        if success:
            saved_filepath = self._save_generated_content(
                generator_type, company_name, result
            )
        
        return {
            "success": success,
            "company_name": company_name,
            "generator_type": generator_type,
            "result": result,
            "context_length": len(context),
            "generated_at": datetime.now().isoformat(),
            "saved_filepath": saved_filepath
        }
    
    def get_available_generators(self) -> list:
        """Get list of available generator types"""
        return list(self.generators.keys())
    
    def _load_latest_products(self, company_name: str) -> list:
        """
        Load the most recent product catalog for a company from saved files.
        
        Returns:
            List of products if found, None otherwise
        """
        import json
        import glob
        from pathlib import Path
        
        # Normalize company name for filename matching
        normalized_name = company_name.lower().replace(' ', '_')
        pattern = f"data/generated/{normalized_name}_products_*.json"
        
        # Find all matching product files
        files = glob.glob(pattern)
        
        if not files:
            logger.debug(f"No saved products found for {company_name}")
            return None
        
        # Sort by filename (timestamp) to get most recent
        latest_file = sorted(files, reverse=True)[0]
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                products = data.get("result", {}).get("products", [])
                
                if products:
                    logger.info(f"📦 Loaded {len(products)} products from: {Path(latest_file).name}")
                    return products
                else:
                    logger.warning(f"Product file found but no products in it: {latest_file}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to load products from {latest_file}: {e}")
            return None
    
    def _load_latest_personas(self, company_name: str) -> list:
        """
        Load the most recent personas for a company from saved files.
        
        Returns:
            List of personas if found, None otherwise
        """
        import json
        import glob
        from pathlib import Path
        
        # Normalize company name for filename matching
        normalized_name = company_name.lower().replace(' ', '_')
        pattern = f"data/generated/{normalized_name}_personas_*.json"
        
        # Find all matching persona files
        files = glob.glob(pattern)
        
        if not files:
            logger.debug(f"No saved personas found for {company_name}")
            return None
        
        # Sort by filename (timestamp) to get most recent
        latest_file = sorted(files, reverse=True)[0]
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                personas = data.get("result", {}).get("personas", [])
                
                if personas:
                    logger.info(f"👥 Loaded {len(personas)} personas from: {Path(latest_file).name}")
                    return personas
                else:
                    logger.warning(f"Persona file found but no personas in it: {latest_file}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to load personas from {latest_file}: {e}")
            return None
    
    def _save_generated_content(self, generator_type: str, company_name: str, result: Dict) -> str:
        """Save generated content to file"""
        import json
        from pathlib import Path
        
        # Create generated directory if it doesn't exist
        generated_dir = Path("data/generated")
        generated_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"{company_name.lower().replace(' ', '_')}_{generator_type}_{timestamp}.json"
        filepath = generated_dir / filename
        
        # Prepare data to save
        data_to_save = {
            "company_name": company_name,
            "generator_type": generator_type,
            "generated_at": datetime.now().isoformat(),
            "result": result
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved generated content to: {filepath}")
        return str(filepath)

# Singleton instance
_generator_service = None

def get_generator_service() -> GeneratorService:
    """Get or create GeneratorService singleton"""
    global _generator_service
    if _generator_service is None:
        _generator_service = GeneratorService()
    return _generator_service