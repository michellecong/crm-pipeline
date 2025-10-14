from fastapi.testclient import TestClient
from app.main import app
import os

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_pdf_process_success():
    test_pdf_path = "tests/fixtures/test.pdf"
    
    if not os.path.exists(test_pdf_path):
        return
    
    with open(test_pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/pdf/process/",
            files={"file": ("test.pdf", f, "application/pdf")},
            params={"chunk_size": 500, "overlap": 50}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data
    assert "chunks" in data
    assert data["chunk_stats"]["total_chunks"] > 0


def test_pdf_process_invalid_file():
    response = client.post(
        "/api/v1/pdf/process/",
        files={"file": ("test.txt", b"not a pdf", "text/plain")}
    )
    
    assert response.status_code == 400
    assert "Only PDF files allowed" in response.json()["detail"]
