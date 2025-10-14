from app.services.pdf_service import PDFService
import os

def test_pdf_service_basic():
    service = PDFService()
    assert service is not None


def test_extract_text():
    test_pdf = "tests/fixtures/test.pdf"
    
    if not os.path.exists(test_pdf):
        return
    
    service = PDFService()
    result = service.extract_text(test_pdf)
    
    assert "filename" in result
    assert "page_count" in result
    assert "extracted_text" in result
    assert result["page_count"] > 0
    assert len(result["extracted_text"]) > 0