import fitz
from pathlib import Path
from typing import Dict, Any


class PDFService:
    
    def extract_text(self, pdf_path: str) -> Dict[str, Any]:
        doc = fitz.open(pdf_path)
        
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        
        metadata = doc.metadata
        
        result = {
            "filename": Path(pdf_path).name,
            "page_count": len(doc),
            "text_length": len(full_text),
            "extracted_text": full_text,
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "creation_date": metadata.get("creationDate", "")
            }
        }
        
        doc.close()
        return result