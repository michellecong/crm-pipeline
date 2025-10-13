from datetime import datetime


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "LLM-based CRM Pipeline API"
    assert data["docs"] == "/docs"
    # Validate timestamp is ISO format
    datetime.fromisoformat(data["timestamp"])  # should not raise


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    datetime.fromisoformat(data["timestamp"])  # should not raise


