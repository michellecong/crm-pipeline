import pytest

from app.services.search_service import AsyncCompanySearchService


def test_dummy_placeholder_noop():
    # Classification removed; keep file non-empty with a noop test
    assert True


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
        {"url": "https://news.example.com/a"},
        {"url": "https://openai.com"},
        {"url": "https://blog.example.com/b"},
    ]
    assert svc.identify_official_website("OpenAI", results) == "https://openai.com"


def test_identify_official_website_fallback_contains_slug():
    svc = AsyncCompanySearchService()
    results = [
        {"url": "https://news.example.com/a"},
        {"url": "https://openai.example.io/team"},
    ]
    assert svc.identify_official_website("Open AI", results) == "https://openai.example.io/team"


