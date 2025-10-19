import asyncio
import pytest
from datetime import datetime


@pytest.mark.parametrize(
    "payload",
    [
        {
            "company_name": "OpenAI",
            "include_news": True,
            "include_case_studies": True,
        },
        {
            "company_name": "Databricks",
            "include_news": False,
            "include_case_studies": True,
        },
    ],
)
def test_search_company_success(client, monkeypatch, payload):
    async def fake_search_company_async(company_name: str, include_news: bool, include_case_studies: bool):
        return {
            "company_name": company_name,
            "official_website": f"https://{company_name.lower()}.com",
            "news_articles": ([
                {
                    "title": "News A",
                    "url": "https://news.example.com/a",
                    "snippet": "Snippet A",
                }
            ] if include_news else []),
            "case_studies": ([
                {
                    "title": "Case A",
                    "url": "https://blog.example.com/case-a",
                    "snippet": "Snippet CA",
                }
            ] if include_case_studies else []),
            "search_timestamp": datetime.now().isoformat(),
        }

    # Monkeypatch the async function used by the router
    import app.routers.search as search_router
    monkeypatch.setattr(search_router, "search_company_async", fake_search_company_async)

    response = client.post("/api/v1/search/company", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == payload["company_name"]
    assert data["official_website"].startswith("https://")
    # Validate total_results reflects lists length
    expected_total = len(data.get("news_articles", [])) + len(data.get("case_studies", []))
    assert data["total_results"] == expected_total


def test_search_company_empty_name_returns_400(client):
    response = client.post(
        "/api/v1/search/company",
        json={"company_name": "   ", "include_news": True, "include_case_studies": True},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Company name cannot be empty"


def test_search_company_internal_error(client, monkeypatch):
    async def failing_search_company_async(*args, **kwargs):
        raise RuntimeError("boom")

    import app.routers.search as search_router
    monkeypatch.setattr(search_router, "search_company_async", failing_search_company_async)

    response = client.post(
        "/api/v1/search/company",
        json={"company_name": "OpenAI", "include_news": True, "include_case_studies": True},
    )
    assert response.status_code == 500
    assert "Search failed" in response.json()["detail"]


def test_search_test_endpoint_success(client, monkeypatch):
    async def fake_search_company_async(company_name: str, include_news: bool, include_case_studies: bool):
        return {"official_website": "https://google.com"}

    import app.routers.search as search_router
    monkeypatch.setattr(search_router, "search_company_async", fake_search_company_async)

    response = client.get("/api/v1/search/test")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Search service working" in data["message"]


