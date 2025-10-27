"""
Source chunk model for SQLAlchemy ORM
"""
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class SourceChunk(Base):
    """Source chunk model representing text chunks from data sources"""
    
    __tablename__ = 'source_chunks'
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey('data_sources.id', ondelete='CASCADE'), nullable=False)
    
    chunks_content = Column(Text, nullable=False)
    chunks_index = Column(Integer, nullable=False)  # Position in original document
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<SourceChunk(id={self.id}, source_id={self.source_id}, chunks_index={self.chunks_index})>"


