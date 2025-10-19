import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
import re
import time
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
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

        # Stage 1: find official domain first to optimize subsequent queries
        try:
            official_candidates = await self._search_official_site(company_name)
        except Exception:
            official_candidates = []

        official_website = self.identify_official_website(company_name, official_candidates)
        official_domain = self._extract_domain(official_website) if official_website else None

        # Stage 2: search news and case studies using domain-aware keywords
        tasks: List[asyncio.Task] = []
        if include_news:
            tasks.append(asyncio.create_task(self._search_news(company_name, official_domain)))
        else:
            tasks.append(asyncio.create_task(self._return_empty_list()))

        if include_case_studies:
            tasks.append(asyncio.create_task(self._search_case_studies(company_name, official_domain)))
        else:
            tasks.append(asyncio.create_task(self._return_empty_list()))

        try:
            news_results, case_study_results = await asyncio.gather(*tasks, return_exceptions=True)
            news_results = news_results if not isinstance(news_results, Exception) else []
            case_study_results = case_study_results if not isinstance(case_study_results, Exception) else []
        except Exception:
            news_results, case_study_results = [], []

        results = {
            "company_name": company_name,
            "official_website": official_website,
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

    async def _search_news(self, company_name: str, official_domain: Optional[str] = None) -> List[Dict]:
        name = company_name.lower()
        keywords = [
            f"{name} news 2025",
            f"{name} latest news",
            f"{name} press release"
        ]
        # Exclude official domain from all queries to prioritize third-party sources
        if official_domain:
            keywords = [f"{kw} -site:{official_domain}" for kw in keywords]
        results = await self._concurrent_keyword_search(keywords, settings.MAX_NEWS_RESULTS, per_domain_cap=1)
        return results

    async def _search_case_studies(self, company_name: str, official_domain: Optional[str] = None) -> List[Dict]:
        name = company_name.lower()
        keywords = [
            f"{name} case study",
            f"{name} customer success story",
            f"{name} use case"
        ]
        # Exclude official domain from all queries to prioritize third-party sources
        if official_domain:
            keywords = [f"{kw} -site:{official_domain}" for kw in keywords]
        results = await self._concurrent_keyword_search(keywords, settings.MAX_CASE_STUDY_RESULTS, per_domain_cap=1)
        return results

    async def _concurrent_keyword_search(self, keywords: List[str], max_results: int, per_domain_cap: int = 1) -> List[Dict]:
        tasks = [self._single_search_google(keyword) for keyword in keywords]
        try:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            search_results = []

        flattened: List[Dict] = []
        for results in search_results:
            if isinstance(results, Exception) or not results:
                continue
            flattened.extend(results)

        deduped = self._deduplicate_results(flattened, max_results=max_results, per_domain_cap=per_domain_cap)
        return deduped

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
                        canonical_url, domain = self._canonicalize_url(link)
                        results.append({
                            'title': item.get('title', ''),
                            'url': canonical_url or link,
                            'snippet': item.get('snippet', ''),
                            'display_link': item.get('displayLink', ''),
                            'type': self._classify_result({
                                'title': item.get('title', ''),
                                'link': canonical_url or link
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

    def _canonicalize_url(self, url: str) -> Tuple[str, str]:
        """Return a canonical URL and its domain to maximize de-duplication.

        Rules:
        - Lowercase scheme and host, strip leading www.
        - Remove tracking query params (utm_*, gclid, fbclid, msclkid, ref, source, scm, icid).
        - Sort remaining query params.
        - Remove fragments.
        - Normalize trailing slash (remove if not root).
        """
        try:
            parts = urlsplit(url)
            scheme = (parts.scheme or 'https').lower()
            netloc = (parts.netloc or '').lower()
            if netloc.startswith('www.'):
                netloc = netloc[4:]

            # Drop default ports
            if netloc.endswith(':80') and scheme == 'http':
                netloc = netloc[:-3]
            if netloc.endswith(':443') and scheme == 'https':
                netloc = netloc[:-4]

            # Clean query params
            tracking_prefixes = ('utm_',)
            tracking_exact = {'gclid', 'fbclid', 'msclkid', 'ref', 'source', 'scm', 'icid', 'sr_share'}
            query_pairs = parse_qsl(parts.query, keep_blank_values=False)
            filtered = []
            for k, v in query_pairs:
                if k in tracking_exact:
                    continue
                if any(k.startswith(pref) for pref in tracking_prefixes):
                    continue
                filtered.append((k, v))
            # Sort for stability
            filtered.sort()
            query = urlencode(filtered, doseq=True)

            # Normalize path
            path = parts.path or '/'
            if path != '/' and path.endswith('/'):
                path = path[:-1]

            canonical = urlunsplit((scheme, netloc, path, query, ''))
            domain = netloc
            return canonical, domain
        except Exception:
            return url, self._extract_domain(url)

    def _normalize_title(self, title: str) -> List[str]:
        cleaned = re.sub(r'[^a-z0-9\s]', ' ', (title or '').lower())
        tokens = [t for t in cleaned.split() if len(t) > 2]
        return tokens

    def _titles_too_similar(self, a: str, b: str, threshold: float = 0.85) -> bool:
        ta = set(self._normalize_title(a))
        tb = set(self._normalize_title(b))
        if not ta or not tb:
            return False
        overlap = len(ta & tb) / float(len(ta | tb))
        return overlap >= threshold

    def _deduplicate_results(self, results: List[Dict], max_results: int, per_domain_cap: int = 1) -> List[Dict]:
        seen_url_keys = set()
        domain_counts: Dict[str, int] = {}
        kept: List[Dict] = []

        for item in results:
            url = item.get('url') or ''
            title = item.get('title') or ''
            if not url or not self._is_valid_url(url):
                continue

            canonical_url, domain = self._canonicalize_url(url)
            url_key = canonical_url

            # Enforce per-domain cap
            count = domain_counts.get(domain, 0)
            if per_domain_cap > 0 and count >= per_domain_cap:
                continue

            # Skip if URL already seen
            if url_key in seen_url_keys:
                continue

            # Skip if title is near-duplicate of an already kept item
            is_dup_title = False
            for existing in kept:
                if self._titles_too_similar(existing.get('title', ''), title):
                    is_dup_title = True
                    break
            if is_dup_title:
                continue

            # Keep the item
            item['url'] = canonical_url
            seen_url_keys.add(url_key)
            domain_counts[domain] = count + 1
            kept.append(item)

            if len(kept) >= max_results:
                break

        return kept



async def search_company_async(company_name: str, include_news: bool = True,
                              include_case_studies: bool = True) -> Dict:
    async with AsyncCompanySearchService() as service:
        return await service.search_company(company_name, include_news, include_case_studies)

