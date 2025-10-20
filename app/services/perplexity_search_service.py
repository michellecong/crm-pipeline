import aiohttp
from typing import List, Dict, Optional, Union
from datetime import datetime

from ..config import settings


class PerplexitySearchClient:
    """
    Minimal client for Perplexity POST /search connectivity.

    This client only sends a search request and returns the raw JSON payload
    from Perplexity without any normalization or business logic.
    """

    def __init__(self):
        self.api_key = settings.PERPLEXITY_API_KEY
        self.base_url = (getattr(settings, "PERPLEXITY_BASE_URL", None) or "https://api.perplexity.ai").rstrip("/")
        self.connector = None
        self.session = None

    async def __aenter__(self):
        self.connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT),
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.connector:
            await self.connector.close()

    async def search(
        self,
        query: Union[str, List[str]],
        max_results: int = 10,
        search_domain_filter: Optional[List[str]] = None,
        max_tokens_per_page: Optional[int] = 1024,
        country: Optional[str] = None,
    ) -> Dict:
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY is not set in environment variables")

        # Validate according to docs
        if isinstance(query, list):
            if not query:
                raise ValueError("query array must not be empty")
            if len(query) > 5:
                raise ValueError("query array supports up to 5 items")
            for q in query:
                if not isinstance(q, str) or not q.strip():
                    raise ValueError("each query in the array must be a non-empty string")
        else:
            if not isinstance(query, str) or not query.strip():
                raise ValueError("query must be a non-empty string or a non-empty list of strings")

        if not isinstance(max_results, int) or max_results < 1 or max_results > 20:
            raise ValueError("max_results must be an integer between 1 and 20")

        if search_domain_filter is not None:
            if not isinstance(search_domain_filter, list):
                raise ValueError("search_domain_filter must be a list of strings")
            if len(search_domain_filter) > 20:
                raise ValueError("search_domain_filter supports up to 20 domains")
            for d in search_domain_filter:
                if not isinstance(d, str) or not d.strip():
                    raise ValueError("each domain in search_domain_filter must be a non-empty string")

        if max_tokens_per_page is not None:
            if not isinstance(max_tokens_per_page, int) or max_tokens_per_page < 1:
                raise ValueError("max_tokens_per_page must be a positive integer")

        if country is not None and (not isinstance(country, str) or not country.strip()):
            raise ValueError("country must be a non-empty string country code when provided")

        body: Dict = {
            "query": query,
            "max_results": max_results,
        }
        if search_domain_filter:
            body["search_domain_filter"] = search_domain_filter
        if max_tokens_per_page is not None:
            body["max_tokens_per_page"] = max_tokens_per_page
        if country:
            body["country"] = country

        url = f"{self.base_url}/search"
        async with self.session.post(url, json=body) as resp:
            # Map API errors into meaningful exceptions
            if resp.status == 429:
                text = await resp.text()
                raise RuntimeError(f"Perplexity rate limit exceeded (429): {text}")
            if resp.status == 400:
                text = await resp.text()
                raise ValueError(f"Perplexity bad request (400): {text}")
            if resp.status >= 500:
                text = await resp.text()
                raise RuntimeError(f"Perplexity server error ({resp.status}): {text}")
            resp.raise_for_status()
            return await resp.json()


async def perplexity_search(
    query: Union[str, List[str]],
    max_results: int = 10,
    search_domain_filter: Optional[List[str]] = None,
    max_tokens_per_page: Optional[int] = 1024,
    country: Optional[str] = None,
) -> Dict:
    """
    Convenience helper for a one-shot Perplexity /search call.
    Returns the raw response dictionary, including the `results` array.
    """
    async with PerplexitySearchClient() as client:
        return await client.search(
            query=query,
            max_results=max_results,
            search_domain_filter=search_domain_filter,
            max_tokens_per_page=max_tokens_per_page,
            country=country,
        )


async def search_company_perplexity_async(company_name: str, include_news: bool = True, include_case_studies: bool = True) -> Dict:
    """
    Minimal company search: map Perplexity /search results to news_articles only.
    """
    resp = await perplexity_search(
        query=company_name.strip(),
        max_results=10,
    )

    items: List[Dict] = []
    for r in resp.get("results", []):
        title = r.get("title", "") or ""
        url = r.get("url", "") or ""
        snippet = r.get("snippet", "") or ""
        if url:
            items.append({"title": title, "url": url, "snippet": snippet})

    return {
        "company_name": company_name,
        "official_website": None,
        "news_articles": items if include_news else [],
        "case_studies": [] if include_case_studies else [],
        "search_timestamp": datetime.now().isoformat(),
    }