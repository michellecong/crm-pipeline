# services/data_aggregator.py
"""
Service for aggregating and preparing data for generators
"""
from typing import Dict, Optional
from pathlib import Path
from ..services.data_store import get_data_store
from ..controllers.scraping_controller import get_scraping_controller
import logging

logger = logging.getLogger(__name__)


class DataAggregator:
    """Service for aggregating and preparing data for generators"""
    
    def __init__(self):
        self.data_store = get_data_store()
    
    async def prepare_context(self, company_name: str, max_chars: int = 15000,
                             include_news: bool = True,
                             include_case_studies: bool = True,
                             max_urls: int = 10,
                             use_llm_search: bool = False,
                             provider: str = "google",
                             include_crm: bool = True,
                             include_pdf: bool = True,
                             crm_folder: str = "crm-data",
                             pdf_folder: str = "pdf-data") -> tuple[str, dict]:
        """
        Prepare comprehensive context from multiple data sources:
        1. Web scraped content (required)
        2. CRM customer data (optional)
        3. PDF documents (optional)
        
        Args:
            company_name: Target company name
            max_chars: Maximum characters for web content
            include_news: Include news articles in web scraping
            include_case_studies: Include case studies in web scraping
            max_urls: Maximum URLs to scrape
            use_llm_search: Use LLM-powered search
            provider: Search provider (google/perplexity)
            include_crm: Include CRM data if available
            include_pdf: Include PDF documents if available
            crm_folder: Folder containing CRM CSV files
            pdf_folder: Folder containing PDF documents
        
        Returns:
            Tuple of (context string, content processing tokens dict)
        """
        context_parts = []
        content_processing_tokens = {}
        
        # ========================================
        # 1. WEB SCRAPED CONTENT (Required)
        # ========================================
        logger.info(f"[DataAggregator] Preparing context for {company_name}")
        
        # Load scraped data
        scraped_data = self.data_store.load_latest_scraped_data(company_name)
        
        # Fallback to scraping if no cached data
        if not scraped_data:
            logger.info(f"No cached data found for {company_name}, starting scraping...")
            controller = get_scraping_controller()
            scraped_data = await controller.scrape_company(
                company_name=company_name,
                include_news=include_news,
                include_case_studies=include_case_studies,
                max_urls=max_urls,
                save_to_file=True,
                use_llm_search=use_llm_search,
                provider=provider
            )
            # Extract content processing tokens from fresh scraping
            if scraped_data and 'content_processing_tokens' in scraped_data:
                content_processing_tokens = scraped_data['content_processing_tokens']
        else:
            # For cached data, try to extract content processing tokens if available
            if 'content_processing_tokens' in scraped_data:
                content_processing_tokens = scraped_data['content_processing_tokens']
        
        if not scraped_data:
            raise ValueError(f"No scraped data found for {company_name}")
        
        # Add section header for web content
        context_parts.append("=" * 80)
        context_parts.append("WEB SCRAPED CONTENT")
        context_parts.append("=" * 80)
        
        # Extract and combine pre-processed content (already cleaned and LLM-processed)
        char_count = 0
        
        # Prioritize official website
        if scraped_data.get("official_website"):
            website_content = scraped_data["official_website"]
            # Use processed content if available, otherwise use original
            if isinstance(website_content, dict) and 'processed_markdown' in website_content:
                website_content = website_content['processed_markdown']
            context_parts.append(f"\nOFFICIAL WEBSITE:\n{website_content}")
            char_count += len(website_content)
        
        # Add scraped content (cleaned)
        for item in scraped_data.get("scraped_content", []):
            if item.get("success"):
                content_type = item.get("content_type", "unknown")
                url = item.get("url", "")
                # Use processed content (cleaned and LLM-processed)
                markdown = item.get("processed_markdown") or item.get("markdown", "")
                
                if not markdown:
                    continue
                
                if char_count + len(markdown) > max_chars:
                    break
                
                context_parts.append(f"\n--- {content_type.upper()} ---\n"
                                   f"URL: {url}\n\n{markdown}")
                char_count += len(context_parts[-1])
        
        logger.info(f"✅ Web content loaded: {char_count} chars")
        
        # ========================================
        # 2. CRM CUSTOMER DATA (Optional)
        # ========================================
        if include_crm:
            crm_summary = self._load_crm_context(crm_folder)
            if crm_summary:
                context_parts.append("\n\n" + "=" * 80)
                context_parts.append("CRM CUSTOMER DATA")
                context_parts.append("=" * 80)
                context_parts.append(crm_summary)
                logger.info(f"✅ CRM data loaded: {len(crm_summary)} chars")
            else:
                logger.info("ℹ️  No CRM data available (folder empty or not found)")
        else:
            logger.info("ℹ️  CRM data skipped (include_crm=False)")
        
        # ========================================
        # 3. PDF DOCUMENTS (Optional)
        # ========================================
        if include_pdf:
            pdf_summary = self._load_pdf_context(pdf_folder)
            if pdf_summary:
                context_parts.append("\n\n" + "=" * 80)
                context_parts.append("PDF DOCUMENTS")
                context_parts.append("=" * 80)
                context_parts.append(pdf_summary)
                logger.info(f"✅ PDF data loaded: {len(pdf_summary)} chars")
            else:
                logger.info("ℹ️  No PDF data available (folder empty or not found)")
        else:
            logger.info("ℹ️  PDF data skipped (include_pdf=False)")
        
        # Combine all context parts
        full_context = "\n".join(context_parts)
        logger.info(f"[DataAggregator] Total context prepared: {len(full_context)} chars")
        
        return full_context, content_processing_tokens
    
    def _load_crm_context(self, crm_folder: str = "crm-data") -> Optional[str]:
        """
        Load CRM customer data summary for persona generation
        
        Args:
            crm_folder: Folder containing CRM CSV files
            
        Returns:
            Text summary string for LLM, or None if no data found
        """
        try:
            from .crm_data_loader import CRMDataLoader
            crm_summary = CRMDataLoader.load_crm_data_for_persona(crm_folder)
            return crm_summary
        except Exception as e:
            logger.warning(f"Failed to load CRM data from {crm_folder}: {e}")
            return None
    
    def _load_pdf_context(self, pdf_folder: str = "pdf-data") -> Optional[str]:
        """
        Load all PDF documents from specified folder
        
        Args:
            pdf_folder: Folder containing PDF files
            
        Returns:
            Combined text from all PDFs, or None if no PDFs found
        """
        try:
            from .pdf_service import PDFService
            
            pdf_dir = Path(pdf_folder)
            if not pdf_dir.exists():
                logger.debug(f"PDF folder not found: {pdf_folder}")
                return None
            
            pdf_files = list(pdf_dir.glob("*.pdf"))
            if not pdf_files:
                logger.debug(f"No PDF files found in {pdf_folder}")
                return None
            
            pdf_service = PDFService()
            pdf_contents = []
            max_pdfs = 5  # Limit to 5 PDFs to avoid context overflow
            max_chars_per_pdf = 5000  # Limit each PDF to 5000 chars
            
            logger.info(f"Found {len(pdf_files)} PDF file(s) in {pdf_folder}")
            
            for pdf_file in pdf_files[:max_pdfs]:
                try:
                    result = pdf_service.extract_text(str(pdf_file))
                    pdf_text = result['extracted_text']
                    
                    # Truncate if too long
                    if len(pdf_text) > max_chars_per_pdf:
                        pdf_text = pdf_text[:max_chars_per_pdf] + "\n... [truncated]"
                    
                    pdf_contents.append(
                        f"\n--- PDF: {result['filename']} ({result['page_count']} pages) ---\n"
                        f"{pdf_text}"
                    )
                    logger.debug(f"Loaded PDF: {result['filename']} ({result['text_length']} chars)")
                except Exception as e:
                    logger.warning(f"Failed to load {pdf_file.name}: {e}")
            
            if pdf_contents:
                return "\n".join(pdf_contents)
            return None
            
        except Exception as e:
            logger.warning(f"Failed to load PDF data from {pdf_folder}: {e}")
            return None
    
    def get_data_summary(self, company_name: str) -> Dict:
        """Get summary of available data"""
        scraped_data = self.data_store.load_latest_scraped_data(company_name)
        
        if not scraped_data:
            return {"available": False, "message": "No data found"}
        
        return {
            "available": True,
            "official_website": scraped_data.get("official_website"),
            "total_content_items": len(scraped_data.get("scraped_content", [])),
            "successful_scrapes": sum(
                1 for item in scraped_data.get("scraped_content", [])
                if item.get("success")
            ),
            "content_types": list(set(
                item.get("content_type", "unknown")
                for item in scraped_data.get("scraped_content", [])
            ))
        }


# Singleton instance
_data_aggregator = None


def get_data_aggregator() -> DataAggregator:
    """Get or create DataAggregator singleton"""
    global _data_aggregator
    if _data_aggregator is None:
        _data_aggregator = DataAggregator()
    return _data_aggregator
