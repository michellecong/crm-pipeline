"""
Data source model for SQLAlchemy ORM
"""
from sqlalchemy import Column, Integer, String, Text, BigInteger, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum


class SourceType(enum.Enum):
    """Enum for source types"""
    WEBSITE = 'website'
    FILE = 'file'


class DataSource(Base):
    """Data source model representing scraped websites or uploaded files"""
    
    __tablename__ = 'data_sources'
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    message_id = Column(Integer, ForeignKey('conversation_messages.id', ondelete='SET NULL'), nullable=True)
    
    # Source identification
    source_type = Column(Enum(SourceType), nullable=False)
    
    # Source details
    file_name = Column(String(255), nullable=True)  # Filename or page title
    website_url = Column(Text, nullable=True)  # URL or storage path
    
    # Content metadata
    title = Column(String(500), nullable=True)
    content_preview = Column(Text, nullable=True)  # First 500 characters
    text_length = Column(Integer, nullable=True)  # Total character count
    total_chunks = Column(Integer, nullable=True)  # Number of chunks
    file_size_bytes = Column(BigInteger, nullable=True)  # File size
    
    # Timestamps
    scraped_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<DataSource(id={self.id}, source_type='{self.source_type}', website_url='{self.website_url}')>"


