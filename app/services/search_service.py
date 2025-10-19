import asyncio
import aiohttp
from typing import List, Dict, Optional
import re
import time
from datetime import datetime
from ..config import settings


class AsyncCompanySearchService:
    def __init__(self):
        self.google_base_url = settings.GOOGLE_CSE_BASE_URL
        self.google_api_key = settings.GOOGLE_CSE_API_KEY
        self.google_cx = settings.GOOGLE_CSE_CX
        self.connector = None
        self.session = None

    async def __aenter__(self):
        self.connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.connector:
            await self.connector.close()

    async def search_company(self, company_name: str, include_news: bool = True,
                             include_case_studies: bool = True) -> Dict:
        start_time = time.time()

        tasks = []
        tasks.append(self._search_official_site(company_name))
        tasks.append(self._search_news(company_name) if include_news else self._return_empty_list())
        tasks.append(self._search_case_studies(company_name) if include_case_studies else self._return_empty_list())

        try:
            official_results, news_results, case_study_results = await asyncio.gather(
                *tasks, return_exceptions=True
            )

            official_results = official_results if not isinstance(official_results, Exception) else []
            news_results = news_results if not isinstance(news_results, Exception) else []
            case_study_results = case_study_results if not isinstance(case_study_results, Exception) else []

        except Exception:
            return self._empty_result(company_name)

        results = {
            "company_name": company_name,
            "official_website": self.identify_official_website(company_name, official_results),
            "news_articles": news_results,
            "case_studies": case_study_results,
            "search_timestamp": datetime.now().isoformat()
        }
        _ = time.time() - start_time
        return results

    async def _return_empty_list(self) -> List[Dict]:
        return []

    async def _search_official_site(self, company_name: str) -> List[Dict]:
        keywords = [
            f"{company_name.lower()}",
            f"{company_name.lower()} official website"
        ]
        return await self._concurrent_keyword_search(keywords, settings.MAX_OFFICIAL_SITE_RESULTS)

    async def _search_news(self, company_name: str) -> List[Dict]:
        keywords = [
            f"{company_name.lower()} news 2025",
            f"{company_name.lower()} latest news",
            f"{company_name.lower()} press release"
        ]
        return await self._concurrent_keyword_search(keywords, settings.MAX_NEWS_RESULTS)

    async def _search_case_studies(self, company_name: str) -> List[Dict]:
        keywords = [
            f"{company_name.lower()} case study",
            f"{company_name.lower()} customer success story",
            f"{company_name.lower()} use case"
        ]
        return await self._concurrent_keyword_search(keywords, settings.MAX_CASE_STUDY_RESULTS)

    async def _concurrent_keyword_search(self, keywords: List[str], max_results: int) -> List[Dict]:
        tasks = [self._single_search_google(keyword) for keyword in keywords]
        try:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results: List[Dict] = []
            seen_urls = set()
            for i, results in enumerate(search_results):
                if isinstance(results, Exception):
                    continue
                for result in results:
                    url = result.get('url', '')
                    if url and url not in seen_urls and self._is_valid_url(url):
                        seen_urls.add(url)
                        all_results.append(result)
                        if len(all_results) >= max_results:
                            break
                if len(all_results) >= max_results:
                    break
            return all_results[:max_results]
        except Exception:
            return []

    # Only Google CSE is supported now

    async def _single_search_google(self, keyword: str) -> List[Dict]:
        if not self.google_api_key or not self.google_cx:
            return []
        params = {
            "key": self.google_api_key,
            "cx": self.google_cx,
            "q": keyword,
            "num": 10,
            "hl": "en"
        }
        try:
            async with self.session.get(self.google_base_url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                items = data.get('items', []) or []
                results: List[Dict] = []
                for item in items:
                    link = item.get('link', '')
                    if link:
                        results.append({
                            'title': item.get('title', ''),
                            'url': link,
                            'snippet': item.get('snippet', ''),
                            'display_link': item.get('displayLink', ''),
                            'type': self._classify_result({
                                'title': item.get('title', ''),
                                'link': link
                            })
                        })
                return results
        except Exception:
            return []

    def _classify_result(self, item: Dict) -> str:
        title = item.get('title', '').lower()
        url = item.get('link', '').lower()
        if 'case study' in title or 'case-study' in url:
            return 'case_study'
        if 'news' in url or 'press' in url or 'blog' in url:
            return 'news'
        if any(domain in url for domain in ['.com/', '.io/', '.ai/']):
            return 'potential_official'
        return 'other'

    def _is_valid_url(self, url: str) -> bool:
        if not url:
            return False
        exclude_patterns = [
            'facebook.com', 'twitter.com', 'linkedin.com/company',
            'youtube.com', 'reddit.com', 'instagram.com'
        ]
        return not any(pattern in url.lower() for pattern in exclude_patterns)

    def identify_official_website(self, company_name: str, results: List[Dict]) -> Optional[str]:
        if not results:
            return None
        company_slug = company_name.lower().replace(' ', '').replace(',', '')
        # Prefer items classified as potential official site
        for result in results:
            if result.get('type') == 'potential_official':
                return result['url']
        # Fallback: any domain that contains the company slug
        for result in results:
            domain = self._extract_domain(result['url'])
            if company_slug in domain:
                return result['url']
        return results[0]['url'] if results else None

    def _extract_domain(self, url: str) -> str:
        match = re.search(r'https?://(?:www\.)?([^/]+)', url.lower())
        return match.group(1) if match else ""



async def search_company_async(company_name: str, include_news: bool = True,
                              include_case_studies: bool = True) -> Dict:
    async with AsyncCompanySearchService() as service:
        return await service.search_company(company_name, include_news, include_case_studies)

