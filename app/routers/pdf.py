from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
from app.services.pdf_service import PDFService
from app.services.chunking_service import ChunkingService
from app.schemas.pdf_schema import PDFProcessResponse

router = APIRouter(prefix="/pdf", tags=["PDF Processing"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

pdf_service = PDFService()


@router.post("/process/", response_model=PDFProcessResponse)
async def process_pdf(
    file: UploadFile = File(...),
    chunk_size: int = 500,
    overlap: int = 50,
    min_chunk_size: int = 200
):
    
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    file_path = UPLOAD_DIR / file.filename
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        extraction_result = pdf_service.extract_text(str(file_path))
        
        chunker = ChunkingService(
            chunk_size=chunk_size,
            overlap=overlap,
            min_chunk_size=min_chunk_size
        )
        chunks = chunker.chunk_text(extraction_result["extracted_text"])
        chunk_stats = chunker.get_chunk_stats(chunks)
        
        return {
            "filename": extraction_result["filename"],
            "page_count": extraction_result["page_count"],
            "total_text_length": extraction_result["text_length"],
            "metadata": extraction_result["metadata"],
            "chunking_params": {
                "chunk_size": chunk_size,
                "overlap": overlap,
                "min_chunk_size": min_chunk_size
            },
            "chunk_stats": chunk_stats,
            "chunks": chunks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        file_path.unlink(missing_ok=True)