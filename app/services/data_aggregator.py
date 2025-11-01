# services/data_aggregator.py
"""
Service for aggregating and preparing data for generators
"""
from typing import Dict
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
                             provider: str = "google") -> str:
        """Prepare context from pre-processed scraped data (cleaned and LLM-processed)"""
        # Load scraped data
        scraped_data = self.data_store.load_latest_scraped_data(company_name)
        
        # Fallback to scraping if no cached data
        if not scraped_data:
            logger.info(f"No cached data found for {company_name}, "
                        f"starting scraping...")
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
        
        if not scraped_data:
            raise ValueError(f"No scraped data found for {company_name}")
        
        # Extract and combine pre-processed content (already cleaned and LLM-processed)
        content_parts = []
        char_count = 0
        
        # Prioritize official website
        if scraped_data.get("official_website"):
            website_content = scraped_data["official_website"]
            # Use processed content if available, otherwise use original
            if isinstance(website_content, dict) and 'processed_markdown' in website_content:
                website_content = website_content['processed_markdown']
            content_parts.append(f"OFFICIAL WEBSITE:\n{website_content}")
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
                
                content_parts.append(f"\n--- {content_type.upper()} ---\n"
                                   f"URL: {url}\n\n{markdown}")
                char_count += len(content_parts[-1])
        
        return "\n".join(content_parts)
    
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
