# controllers/scraping_controller.py
"""
Controller for scraping operations - handles business logic
"""
from typing import Dict, Optional
from sqlalchemy.orm import Session
from ..services.llm_web_search_service import llm_company_web_search_structured
from ..services.firecrawl_service import scrape_urls_async
from ..services.content_processor import get_content_processor
from ..services.data_store import get_data_store
from ..services.search_service import search_company_async
from datetime import datetime
import logging
from ..services.text_cleaning import strip_links
from ..schemas.search import LLMCompanyWebSearchResponse, LLMCompanyWebItem, LLMCompanyWebNewsItem

logger = logging.getLogger(__name__)


class ScrapingController:
    """Controller for handling scraping business logic"""
    
    def _prepare_urls_for_scraping(
        self,
        search_results: LLMCompanyWebSearchResponse,
        max_urls: int,
        include_news: bool,
        include_case_studies: bool
    ) -> tuple[list[str], dict]:
        """
        Collect URLs to scrape from search results with their types
        
        Returns:
            Tuple of (urls_to_scrape, url_types)
        """
        urls_to_scrape: list[str] = []
        url_types: dict[str, str] = {}

        def add_url(url: Optional[str], kind: str) -> None:
            if not url or url in url_types or len(urls_to_scrape) >= max_urls:
                return
            urls_to_scrape.append(url)
            url_types[url] = kind

        for item in search_results.official_website:
            add_url(item.url, 'website')

        if include_news:
            for item in search_results.news:
                add_url(item.url, 'news')

        if include_case_studies:
            for item in search_results.case_studies:
                add_url(item.url, 'case_study')

        return urls_to_scrape, url_types
    
    def _adapt_basic_search_to_llm_response(
        self,
        company_name: str,
        basic: dict
    ) -> LLMCompanyWebSearchResponse:
        """
        Adapt non-LLM search result dict into LLMCompanyWebSearchResponse
        so the rest of the pipeline can stay unchanged.
        """
        official = basic.get("official_website") if isinstance(basic, dict) else None
        news_items = (basic.get("news_articles") or []) if isinstance(basic, dict) else []
        case_items = (basic.get("case_studies") or []) if isinstance(basic, dict) else []
        collected_at = basic.get("search_timestamp") if isinstance(basic, dict) else None

        return LLMCompanyWebSearchResponse(
            company=company_name,
            queries_planned=[],
            official_website=[LLMCompanyWebItem(url=official)] if official else [],
            news=[
                LLMCompanyWebNewsItem(
                    url=item.get("url", ""),
                    title=item.get("title")
                ) for item in news_items if item.get("url")
            ],
            case_studies=[
                LLMCompanyWebItem(
                    url=item.get("url", ""),
                    title=item.get("title")
                ) for item in case_items if item.get("url")
            ],
            collected_at=collected_at
        )
    
    def _format_scraped_content(
        self, 
        scraped_data: list, 
        url_types: dict
    ) -> tuple[list, int]:
        """
        Format scraped data into structured content
        
        Returns:
            Tuple of (scraped_content, successful_count)
        """
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
        
        return scraped_content, successful_count
    
    async def _process_content_batch(
        self, 
        scraped_content: list, 
        company_name: str
    ) -> tuple[list, dict]:
        """
        Batch process and clean scraped content with LLM
        
        Returns:
            Tuple of (processed content items, token usage dict)
        """
        content_processor = get_content_processor()
        token_usage = {}
        
        # Collect all content for batch processing
        content_batch = []
        for item in scraped_content:
            if item['success'] and item.get('markdown'):
                content_batch.append({
                    'item': item,
                    'content': item['markdown'],
                    'type': item['content_type']
                })
        
        processed_content = []
        if content_batch:
            try:
                logger.info(f"Batch processing {len(content_batch)} content items...")
                batch_processed = await content_processor.batch_process_content(
                    content_batch, company_name
                )
                
                # Extract token usage from first item (all items have the same token usage)
                if batch_processed and 'content_processing_tokens' in batch_processed[0]:
                    token_usage = batch_processed[0]['content_processing_tokens']
                
                # Merge processed content back with original items
                processed_items = {item['url']: item for item in batch_processed}
                
                for item in scraped_content:
                    if item['success'] and item.get('markdown'):
                        url = item['url']
                        if url in processed_items:
                            processed_item = item.copy()
                            processed_item['processed_markdown'] = processed_items[url]['processed_content']
                            processed_item['original_markdown_length'] = len(item['markdown'])
                            processed_item['processed_markdown_length'] = len(processed_items[url]['processed_content'])
                            processed_item['compression_ratio'] = len(processed_items[url]['processed_content']) / len(item['markdown']) if item['markdown'] else 0
                            processed_content.append(processed_item)
                        else:
                            processed_content.append(item)
                    else:
                        processed_content.append(item)
                        
                logger.info(f"Batch processing completed for {len(content_batch)} items")
                
            except Exception as e:
                logger.warning(f"Batch processing failed, falling back to rule-based cleaning: {str(e)}")
                # Fallback to rule-based cleaning only
                processed_content = self._fallback_clean_content(scraped_content, content_processor)
        else:
            processed_content = scraped_content
        
        return processed_content, token_usage
    
    def _fallback_clean_content(self, scraped_content: list, content_processor) -> list:
        """
        Fallback to rule-based cleaning when batch processing fails
        
        Returns:
            List of content items with rule-based cleaning applied
        """
        processed_content = []
        for item in scraped_content:
            if item['success'] and item.get('markdown'):
                try:
                    cleaned_markdown = content_processor.clean_markdown(item['markdown'])
                    processed_item = item.copy()
                    processed_item['processed_markdown'] = cleaned_markdown
                    processed_item['original_markdown_length'] = len(item['markdown'])
                    processed_item['processed_markdown_length'] = len(cleaned_markdown)
                    processed_item['compression_ratio'] = len(cleaned_markdown) / len(item['markdown']) if item['markdown'] else 0
                    processed_content.append(processed_item)
                except Exception as e:
                    logger.warning(f"Failed to clean content for {item['url']}: {str(e)}")
                    processed_content.append(item)
            else:
                processed_content.append(item)
        return processed_content
    
    def _build_response_dict(
        self,
        company_name: str,
        search_results: LLMCompanyWebSearchResponse,
        total_urls_found: int,
        scraped_data: list,
        successful_count: int,
        processed_content: list,
        saved_filepath: Optional[str]
    ) -> dict:
        """
        Build the final response dictionary
        
        Returns:
            Complete response dictionary with all metrics
        """
        official_url = search_results.official_website[0].url if search_results.official_website else None
        search_summary = {
            "official_website": official_url,
            "news_count": len(search_results.news),
            "case_studies_count": len(search_results.case_studies),
            "total_search_results": (
                len(search_results.official_website)
                + len(search_results.news)
                + len(search_results.case_studies)
            ),
            "queries_planned": search_results.queries_planned,
            "collected_at": search_results.collected_at,
            "official_website_entries": [item.model_dump() for item in search_results.official_website],
            "news_entries": [item.model_dump() for item in search_results.news],
            "case_study_entries": [item.model_dump() for item in search_results.case_studies],
        }

        return {
            "company_name": company_name,
            "official_website": official_url,
            "total_urls_found": total_urls_found,
            "total_urls_scraped": len(scraped_data),
            "successful_scrapes": successful_count,
            "scraped_content": processed_content,
            "search_results_summary": search_summary,
            "scraping_timestamp": datetime.now().isoformat(),
            "saved_filepath": saved_filepath,
            "content_processing": {
                "processed_items": len([item for item in processed_content if 'processed_markdown' in item]),
                "total_items": len(processed_content),
                "processing_timestamp": datetime.now().isoformat()
            }
        }
    
    async def scrape_company(
        self,
        company_name: str,
        max_urls: int = 10,
        include_news: bool = True,
        include_case_studies: bool = True,
        save_to_file: bool = False,
        db: Optional[Session] = None,
        use_llm_search: bool = True,
        provider: str = "google"
    ) -> Dict:
        """
        Main business logic for scraping company data
        
        Args:
            company_name: Target company name
            include_news: Include news articles
            include_case_studies: Include case studies
            max_urls: Maximum URLs to scrape
            save_to_file: Save scraped data to file
            db: Database session (optional)
            
        Returns:
            Dict with scraped data and metadata
        """
        logger.info(f"Starting data scraping for: {company_name}")
        
        # Step 1: Search for company information
        logger.info(f"Step 1/3: Searching for {company_name}...")
        if use_llm_search:
            search_results = await llm_company_web_search_structured(
                company_name=company_name
            )
            if search_results.queries_planned:
                logger.info(
                    "LLM planned search queries: %s",
                    " | ".join(search_results.queries_planned)
                )
        else:
            basic_results = await search_company_async(
                company_name=company_name,
                include_news=include_news,
                include_case_studies=include_case_studies,
                provider=provider
            )
            search_results = self._adapt_basic_search_to_llm_response(company_name, basic_results)
        
        # Collect URLs to scrape
        urls_to_scrape, url_types = self._prepare_urls_for_scraping(
            search_results,
            max_urls,
            include_news,
            include_case_studies
        )
        
        if not urls_to_scrape:
            raise ValueError(f"No URLs found for company: {company_name}")
        
        logger.info(f"Found {len(urls_to_scrape)} URLs to scrape")
        
        # Step 2: Scrape all URLs
        logger.info(f"Step 2/3: Scraping {len(urls_to_scrape)} URLs...")
        scraped_data = await scrape_urls_async(urls_to_scrape, max_concurrent=10)
        
        # Format scraped content
        scraped_content, successful_count = self._format_scraped_content(scraped_data, url_types)
        logger.info(f"Successfully scraped {successful_count}/{len(urls_to_scrape)} URLs")
        
        # Step 3: Process and clean content
        logger.info("Step 3/3: Processing and cleaning scraped content...")
        processed_content, content_processing_tokens = await self._process_content_batch(scraped_content, company_name)
        
        if content_processing_tokens:
            logger.info(
                f"Content processing completed for {len(processed_content)} items. "
                f"Tokens used: {content_processing_tokens.get('total_tokens', 0)} "
                f"(prompt: {content_processing_tokens.get('prompt_tokens', 0)}, "
                f"completion: {content_processing_tokens.get('completion_tokens', 0)})"
            )
        else:
            logger.info(f"Content processing completed for {len(processed_content)} items")
        
        # Save to database or file
        saved_filepath = None
        result = self._build_response_dict(
            company_name=company_name,
            search_results=search_results,
            total_urls_found=len(urls_to_scrape),
            scraped_data=scraped_data,
            successful_count=successful_count,
            processed_content=processed_content,
            saved_filepath=None
        )
        
        # Add content processing token usage to result
        if content_processing_tokens:
            result['content_processing_tokens'] = content_processing_tokens

        if db is not None or save_to_file:
            data_store = get_data_store(db=db)
            storage_payload = result.copy()

            # Save based on parameters: save_to_file=True will skip database
            if db is not None:
                saved_filepath = data_store.save_scraped_data(
                    company_name,
                    storage_payload,
                    user_id=1,
                    save_to_file=save_to_file
                )
            else:
                saved_filepath = data_store.save_scraped_data(
                    company_name,
                    storage_payload,
                    save_to_file=save_to_file
                )

            result["saved_filepath"] = saved_filepath
            logger.info(f"Saved data to: {saved_filepath}")
        else:
            saved_filepath = None
        
        logger.info(f"Data scraping completed for {company_name}")
        return result
    
    async def list_saved_data(self, db: Optional[Session] = None) -> Dict:
        """
        List all saved scraped data
        
        Args:
            db: Database session (optional)
            
        Returns:
            Dict with list of saved files
        """
        data_store = get_data_store(db=db)
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

