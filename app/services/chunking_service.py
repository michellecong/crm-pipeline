from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter


class ChunkingService:
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50, min_chunk_size: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        if not text or len(text) == 0:
            return []
        
        chunks_text = self.splitter.split_text(text)
        
        chunks = []
        
        for index, chunk_text in enumerate(chunks_text):
            if len(chunk_text) < self.min_chunk_size and index > 0:
                chunks[-1]["text"] += " " + chunk_text
                chunks[-1]["char_count"] = len(chunks[-1]["text"])
            else:
                chunks.append({
                    "index": len(chunks),
                    "text": chunk_text,
                    "char_count": len(chunk_text)
                })
        
        return chunks
    
    def get_chunk_stats(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not chunks:
            return {
                "total_chunks": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0
            }
        
        chunk_sizes = [c["char_count"] for c in chunks]
        
        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(chunk_sizes) // len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes)
        }