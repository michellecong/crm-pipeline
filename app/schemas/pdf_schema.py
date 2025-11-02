from pydantic import BaseModel


class PDFMetadata(BaseModel):
    title: str
    author: str
    subject: str
    creator: str
    creation_date: str


class PDFProcessResponse(BaseModel):
    filename: str
    page_count: int
    total_text_length: int
    metadata: PDFMetadata
    extracted_text: str