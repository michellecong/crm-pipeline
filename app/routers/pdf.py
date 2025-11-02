from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
from app.services.pdf_service import PDFService
from app.schemas.pdf_schema import PDFProcessResponse

router = APIRouter(prefix="/pdf", tags=["PDF Processing"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

pdf_service = PDFService()


@router.post("/process/", response_model=PDFProcessResponse)
async def process_pdf(file: UploadFile = File(...)):
    """
    Process PDF file and extract full text content.
    
    Returns complete extracted text without chunking.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    file_path = UPLOAD_DIR / file.filename
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        extraction_result = pdf_service.extract_text(str(file_path))
        
        return {
            "filename": extraction_result["filename"],
            "page_count": extraction_result["page_count"],
            "total_text_length": extraction_result["text_length"],
            "metadata": extraction_result["metadata"],
            "extracted_text": extraction_result["extracted_text"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        file_path.unlink(missing_ok=True)