from typing import Dict, Optional
from ..generators.base_generator import BaseGenerator
from ..generators.persona_generator import PersonaGenerator
from ..generators.product_generator import ProductGenerator
from ..generators.mapping_generator import MappingGenerator
from ..generators.outreach_generator import OutreachGenerator
from ..generators.baseline_generator import BaselineGenerator
from ..generators.two_stage_generator import TwoStageGenerator
from ..generators.three_stage_generator import ThreeStageGenerator
from .data_aggregator import DataAggregator
from .crm_data_loader import CRMDataLoader
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
            "outreach": OutreachGenerator(),
            "baseline": BaselineGenerator(),
            "two_stage": TwoStageGenerator(),
            "three_stage": ThreeStageGenerator()
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
        
        # Note: CRM and PDF data are now automatically loaded by DataAggregator.prepare_context()
        # No need for separate CRM injection here - it's included in the context string
        crm_data_provided = False  # Keep for backward compatibility with validation logic
        
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
        
        # For products, skip context preparation (uses Perplexity web search instead)
        content_processing_tokens = {}
        if generator_type == "products":
            context = f"Generating products for {company_name} using web search"
        # For outreach, use minimal context (personas_with_mappings provides the data)
        elif generator_type == "outreach":
            if "personas_with_mappings" not in kwargs:
                raise ValueError("personas_with_mappings is required for outreach generation")
            context = f"Generating outreach sequences for {company_name}"
        else:
            # Prepare comprehensive context (Web + CRM + PDF)
            # CRM and PDF are automatically included if available in their respective folders
            context, content_processing_tokens = await self.data_aggregator.prepare_context(
                company_name,
                kwargs.get('max_context_chars', 15000),
                kwargs.get('include_news', True),
                kwargs.get('include_case_studies', True),
                kwargs.get('max_urls', 10),
                kwargs.get('use_llm_search', False),
                kwargs.get('provider', 'google'),
                include_crm=True,   # CRM data auto-loaded from crm-data folder
                include_pdf=True,   # PDF data auto-loaded from pdf-data folder
                crm_folder="crm-data",
                pdf_folder="pdf-data"
            )
            if content_processing_tokens:
                logger.info(
                    f"Content processing used {content_processing_tokens.get('total_tokens', 0)} tokens "
                    f"(prompt: {content_processing_tokens.get('prompt_tokens', 0)}, "
                    f"completion: {content_processing_tokens.get('completion_tokens', 0)})"
                )
        
        logger.info(f"Prepared context length: {len(context)} chars for {company_name}")
        
        result = await generator.generate(company_name, context, **kwargs)
        
        # For personas and two_stage, log data_sources information if present
        # CRM/PDF data are now automatically included in context by DataAggregator
        if generator_type == 'personas' or generator_type == 'two_stage':
            if 'data_sources' in result:
                reported_crm_usage = result['data_sources'].get('crm_data_used', False)
                logger.info(
                    f"✅ Data sources used: CRM={'Yes' if reported_crm_usage else 'No'}, "
                    f"Web=Yes, PDF={'Check logs' if reported_crm_usage else 'Check logs'}"
                )
        
        # Check if generation was successful
        if generator_type == 'personas':
            success = bool(result.get('personas'))
        elif generator_type == 'outreach':
            success = bool(result.get('sequences'))
        elif generator_type == 'baseline':
            # Baseline returns all 4 outputs in one response
            success = bool(result.get('products') and result.get('personas'))
        elif generator_type == 'two_stage':
            # Two-stage returns personas, personas_with_mappings, and sequences
            success = bool(result.get('personas') and result.get('personas_with_mappings') and result.get('sequences'))
        else:
            success = bool(result)
        
        # Save generated content to file
        saved_filepath = None
        if success:
            saved_filepath = self._save_generated_content(
                generator_type, company_name, result
            )
        
        response_dict = {
            "success": success,
            "company_name": company_name,
            "generator_type": generator_type,
            "result": result,
            "context_length": len(context),
            "generated_at": datetime.now().isoformat(),
            "saved_filepath": saved_filepath
        }
        
        # Add content processing tokens if available
        if content_processing_tokens:
            response_dict["content_processing_tokens"] = content_processing_tokens
        
        return response_dict
    
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
    
    def _load_crm_data(self, crm_data_dir: str = "crm-data") -> Optional[str]:
        """
        Load CRM data from crm-data folder and return text summary for persona generation.
        
        Handles multiple CSV files with different structures automatically:
        - Identifies file types (Account, Contact, Opportunity, etc.)
        - Maps fields from different CRM systems (Salesforce, HubSpot, Pipedrive)
        - Merges data and generates statistics
        
        Args:
            crm_data_dir: Directory containing CRM CSV files
            
        Returns:
            Text summary string for LLM, or None if no data found
        """
        try:
            crm_summary = CRMDataLoader.load_crm_data_for_persona(crm_data_dir)
            if crm_summary:
                logger.info(f"📊 Loaded CRM data summary ({len(crm_summary)} chars)")
                return crm_summary
            return None
        except Exception as e:
            logger.warning(f"Failed to load CRM data: {e}")
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
        # Special handling for two_stage and three_stage generator types
        if generator_type == "two_stage":
            filename = f"{company_name.lower().replace(' ', '_')}_two_stage_{timestamp}.json"
        elif generator_type == "three_stage":
            filename = f"{company_name.lower().replace(' ', '_')}_three_stage_{timestamp}.json"
        else:
            filename = f"{company_name.lower().replace(' ', '_')}_{generator_type}_{timestamp}.json"
        filepath = generated_dir / filename
        
        # Prepare data to save
        data_to_save = {
            "company_name": company_name,
            "generator_type": generator_type,
            "generated_at": datetime.now().isoformat(),
            "result": result
        }
        
        # Add pipeline description for multi-stage generators
        if generator_type == "two_stage":
            data_to_save["pipeline_description"] = "Two-Stage Pipeline: Stage 1 (Products) → Stage 2 (Personas + Mappings + Sequences)"
            data_to_save["pipeline_stages"] = 2
        elif generator_type == "three_stage":
            data_to_save["pipeline_description"] = "Three-Stage Pipeline: Stage 1 (Products) → Stage 2 (Personas) → Stage 3 (Mappings + Sequences)"
            data_to_save["pipeline_stages"] = 3
        elif generator_type == "baseline":
            data_to_save["pipeline_description"] = "Baseline Single-Shot: All outputs generated in one LLM call"
            data_to_save["pipeline_stages"] = 1
        
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