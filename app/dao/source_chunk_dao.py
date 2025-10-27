"""
Source chunk DAO for database operations
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.source_chunk import SourceChunk


class SourceChunkDAO:
    """Data Access Object for SourceChunk operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, source_id: int, chunks_content: str, chunks_index: int) -> SourceChunk:
        """Create a new source chunk"""
        chunk = SourceChunk(
            source_id=source_id,
            chunks_content=chunks_content,
            chunks_index=chunks_index
        )
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        return chunk
    
    def create_batch(self, source_id: int, chunks: List[str]) -> List[SourceChunk]:
        """Create multiple chunks for a source"""
        chunk_objects = []
        for index, content in enumerate(chunks):
            chunk = SourceChunk(
                source_id=source_id,
                chunks_content=content,
                chunks_index=index
            )
            chunk_objects.append(chunk)
            self.db.add(chunk)
        
        self.db.commit()
        
        # Refresh all chunks
        for chunk in chunk_objects:
            self.db.refresh(chunk)
        
        return chunk_objects
    
    def get_by_source_id(self, source_id: int) -> List[SourceChunk]:
        """Get all chunks for a source"""
        return self.db.query(SourceChunk).filter(
            SourceChunk.source_id == source_id
        ).order_by(SourceChunk.chunks_index).all()
    
    def get_by_id(self, chunk_id: int) -> Optional[SourceChunk]:
        """Get chunk by ID"""
        return self.db.query(SourceChunk).filter(SourceChunk.id == chunk_id).first()


