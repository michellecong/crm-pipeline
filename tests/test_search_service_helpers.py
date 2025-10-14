import pytest

from app.services.search_service import AsyncCompanySearchService


def test_classify_result_news():
    svc = AsyncCompanySearchService()
    item = {"title": "Press Release", "link": "https://example.com/news/launch"}
    assert svc._classify_result(item) == "news"


def test_classify_result_case_study():
    svc = AsyncCompanySearchService()
    item = {"title": "Amazing Case Study", "link": "https://example.com/blog/case-study-abc"}
    assert svc._classify_result(item) == "case_study"


def test_is_valid_url_filters_social():
    svc = AsyncCompanySearchService()
    assert not svc._is_valid_url("https://facebook.com/page")
    assert svc._is_valid_url("https://company.com/about")


def test_extract_domain():
    svc = AsyncCompanySearchService()
    assert svc._extract_domain("https://www.example.com/path") == "example.com"


def test_identify_official_website_prefers_potential_official():
    svc = AsyncCompanySearchService()
    results = [
        {"url": "https://news.example.com/a", "type": "news"},
        {"url": "https://openai.com", "type": "potential_official"},
        {"url": "https://blog.example.com/b", "type": "other"},
    ]
    assert svc.identify_official_website("OpenAI", results) == "https://openai.com"


def test_identify_official_website_fallback_contains_slug():
    svc = AsyncCompanySearchService()
    results = [
        {"url": "https://news.example.com/a", "type": "news"},
        {"url": "https://openai.example.io/team", "type": "other"},
    ]
    assert svc.identify_official_website("Open AI", results) == "https://openai.example.io/team"


