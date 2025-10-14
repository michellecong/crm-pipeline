from pydantic import BaseModel
from typing import List


class PDFMetadata(BaseModel):
    title: str
    author: str
    subject: str
    creator: str
    creation_date: str


class ChunkData(BaseModel):
    index: int
    text: str
    char_count: int


class ChunkStats(BaseModel):
    total_chunks: int
    avg_chunk_size: int
    min_chunk_size: int
    max_chunk_size: int


class ChunkingParams(BaseModel):
    chunk_size: int
    overlap: int
    min_chunk_size: int


class PDFProcessResponse(BaseModel):
    filename: str
    page_count: int
    total_text_length: int
    metadata: PDFMetadata
    chunking_params: ChunkingParams
    chunk_stats: ChunkStats
    chunks: List[ChunkData]