# services/firecrawl_service.py
"""
Firecrawl service for web scraping and content extraction
"""
import asyncio
from typing import List, Dict, Optional
from firecrawl import FirecrawlApp
from ..config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FirecrawlService:
    """Service for crawling web pages using Firecrawl"""
    
    def __init__(self):
        if not settings.FIRECRAWL_API_KEY:
            raise ValueError("FIRECRAWL_API_KEY is not set in environment variables")
        self.app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)
    
    async def scrape_url(self, url: str, formats: List[str] = None) -> Dict:
        """
        Scrape a single URL and return its content
        
        Args:
            url: The URL to scrape
            formats: List of output formats (default: ['markdown'])
            
        Returns:
            Dict with scraped content including markdown, html, metadata
        """
        if formats is None:
            formats = ['markdown']  # Only request markdown for faster scraping
        
        try:
            logger.info(f"Scraping URL: {url}")
            
            # Run synchronous Firecrawl call in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.app.scrape(url, formats=formats)
            )
            
            # Firecrawl 4.x returns a Document object, not a dict
            metadata_obj = getattr(result, 'metadata', None)
            metadata_dict = {}
            if metadata_obj:
                # Convert metadata object to dict
                metadata_dict = {
                    'title': getattr(metadata_obj, 'title', ''),
                    'description': getattr(metadata_obj, 'description', ''),
                    'language': getattr(metadata_obj, 'language', ''),
                    'sourceURL': getattr(metadata_obj, 'sourceURL', url),
                }
            
            return {
                'url': url,
                'success': True,
                'markdown': getattr(result, 'markdown', '') or '',
                'html': getattr(result, 'html', '') or '',
                'metadata': metadata_dict,
                'error': None
            }
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {
                'url': url,
                'success': False,
                'markdown': '',
                'html': '',
                'metadata': {},
                'error': str(e)
            }
    
    async def scrape_multiple_urls(self, urls: List[str], max_concurrent: int = 3) -> List[Dict]:
        """
        Scrape multiple URLs concurrently
        
        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum number of concurrent scrapes
            
        Returns:
            List of scrape results
        """
        logger.info(f"Scraping {len(urls)} URLs with max {max_concurrent} concurrent requests")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str) -> Dict:
            async with semaphore:
                return await self.scrape_url(url)
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error dicts
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'url': urls[i],
                    'success': False,
                    'markdown': '',
                    'html': '',
                    'metadata': {},
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r['success'])
        logger.info(f"Successfully scraped {success_count}/{len(urls)} URLs")
        
        return processed_results
    
    async def extract_content_summary(self, scrape_result: Dict) -> Dict:
        """
        Extract key information from scraped content
        
        Args:
            scrape_result: Result from scrape_url
            
        Returns:
            Dict with extracted summary information
        """
        markdown = scrape_result.get('markdown', '')
        metadata = scrape_result.get('metadata', {})
        
        # Extract basic information
        title = metadata.get('title', '')
        description = metadata.get('description', '')
        
        # Get first N characters of content for summary
        content_preview = markdown[:1000] if markdown else ''
        
        return {
            'url': scrape_result['url'],
            'title': title,
            'description': description,
            'content_preview': content_preview,
            'content_length': len(markdown),
            'success': scrape_result['success']
        }


# Singleton instance
_firecrawl_service = None


def get_firecrawl_service() -> FirecrawlService:
    """Get or create FirecrawlService singleton"""
    global _firecrawl_service
    if _firecrawl_service is None:
        _firecrawl_service = FirecrawlService()
    return _firecrawl_service


async def scrape_urls_async(urls: List[str], max_concurrent: int = 3) -> List[Dict]:
    """
    Convenience function to scrape multiple URLs
    
    Args:
        urls: List of URLs to scrape
        max_concurrent: Maximum concurrent requests
        
    Returns:
        List of scrape results
    """
    service = get_firecrawl_service()
    return await service.scrape_multiple_urls(urls, max_concurrent)

