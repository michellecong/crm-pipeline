# controllers/scraping_controller.py
"""
Controller for scraping operations - handles business logic
"""
from typing import Dict, List
from ..services.search_service import search_company_async
from ..services.firecrawl_service import scrape_urls_async
from ..services.data_store import get_data_store
from ..config import settings
from datetime import datetime
import logging
from ..services.text_cleaning import strip_links

logger = logging.getLogger(__name__)


class ScrapingController:
    """Controller for handling scraping business logic"""
    
    async def scrape_company(
        self,
        company_name: str,
        include_news: bool = True,
        include_case_studies: bool = True,
        max_urls: int = 10,
        save_to_file: bool = False
    ) -> Dict:
        """
        Main business logic for scraping company data
        
        Args:
            company_name: Target company name
            include_news: Include news articles
            include_case_studies: Include case studies
            max_urls: Maximum URLs to scrape
            save_to_file: Save scraped data to file
            
        Returns:
            Dict with scraped data and metadata
        """
        logger.info(f"Starting data scraping for: {company_name}")
        
        # Step 1: Search for company information
        logger.info(f"Step 1/2: Searching for {company_name}...")
        search_results = await search_company_async(
            company_name=company_name,
            include_news=include_news,
            include_case_studies=include_case_studies
        )
        
        # Collect URLs to scrape with their types
        urls_to_scrape = []
        url_types = {}  # Map URL to type
        
        # Add official website (highest priority)
        if search_results.get('official_website'):
            url = search_results['official_website']
            urls_to_scrape.append(url)
            url_types[url] = 'website'
        
        # Add news articles
        for article in search_results.get('news_articles', []):
            if article.get('url') and len(urls_to_scrape) < max_urls:
                url = article['url']
                urls_to_scrape.append(url)
                url_types[url] = 'news'
        
        # Add case studies
        for case in search_results.get('case_studies', []):
            if case.get('url') and len(urls_to_scrape) < max_urls:
                url = case['url']
                urls_to_scrape.append(url)
                url_types[url] = 'case_study'
        
        total_urls_found = len(urls_to_scrape)
        
        if not urls_to_scrape:
            raise ValueError(f"No URLs found for company: {company_name}")
        
        logger.info(f"Found {total_urls_found} URLs to scrape")
        
        # Step 2: Scrape all URLs with Firecrawl
        logger.info(f"Step 2/2: Scraping {len(urls_to_scrape)} URLs...")
        scraped_data = await scrape_urls_async(urls_to_scrape, max_concurrent=10)
        
        # Format scraped content
        scraped_content = []
        successful_count = 0
        
        for item in scraped_data:
            if item['success']:
                successful_count += 1
            
            # Clean markdown and drop raw HTML to only keep cleaned content
            cleaned_markdown = strip_links(item.get('markdown', '') or '')

            content = {
                'url': item['url'],
                'title': item.get('metadata', {}).get('title'),
                'markdown': cleaned_markdown,
                'html': item.get('html'),
                'metadata': item.get('metadata', {}),
                'content_type': url_types.get(item['url'], 'unknown'),
                'success': item['success'],
                'error': item.get('error'),
                'scraped_at': datetime.now().isoformat()
            }
            scraped_content.append(content)
        
        logger.info(f"Successfully scraped {successful_count}/{len(urls_to_scrape)} URLs")
        
        # Prepare search results summary
        search_summary = {
            "official_website": search_results.get('official_website'),
            "news_count": len(search_results.get('news_articles', [])),
            "case_studies_count": len(search_results.get('case_studies', [])),
            "total_search_results": search_results.get('total_results', 0)
        }
        
        # Save to file if requested
        saved_filepath = None
        if save_to_file:
            data_store = get_data_store()
            response_dict = {
                "company_name": company_name,
                "official_website": search_results.get('official_website'),
                "total_urls_found": total_urls_found,
                "total_urls_scraped": len(scraped_data),
                "successful_scrapes": successful_count,
                "scraped_content": scraped_content,
                "search_results_summary": search_summary,
                "scraping_timestamp": datetime.now().isoformat()
            }
            saved_filepath = data_store.save_scraped_data(company_name, response_dict)
            logger.info(f"Saved data to: {saved_filepath}")
        
        # Build final response
        result = {
            "company_name": company_name,
            "official_website": search_results.get('official_website'),
            "total_urls_found": total_urls_found,
            "total_urls_scraped": len(scraped_data),
            "successful_scrapes": successful_count,
            "scraped_content": scraped_content,
            "search_results_summary": search_summary,
            "scraping_timestamp": datetime.now().isoformat(),
            "saved_filepath": saved_filepath
        }
        
        logger.info(f"Data scraping completed for {company_name}")
        return result
    
    async def list_saved_data(self) -> Dict:
        """
        List all saved scraped data
        
        Returns:
            Dict with list of saved files
        """
        data_store = get_data_store()
        companies = data_store.list_scraped_companies()
        
        return {
            "total_files": len(companies),
            "saved_data": companies,
            "timestamp": datetime.now().isoformat(),
            "note": "Saved scraped data ready for processing"
        }


# Singleton instance
_controller = None


def get_scraping_controller() -> ScrapingController:
    """Get or create ScrapingController singleton"""
    global _controller
    if _controller is None:
        _controller = ScrapingController()
    return _controller

