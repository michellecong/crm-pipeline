"""
Data source DAO for database operations
"""
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from app.models.data_source import DataSource, SourceType


class DataSourceDAO:
    """Data Access Object for DataSource operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, conversation_id: int, source_type: SourceType, website_url: Optional[str] = None,
               file_name: Optional[str] = None, title: Optional[str] = None,
               content_preview: Optional[str] = None, text_length: Optional[int] = None,
               total_chunks: Optional[int] = None, file_size_bytes: Optional[int] = None,
               message_id: Optional[int] = None, scraped_at: Optional[datetime] = None) -> DataSource:
        """Create a new data source"""
        data_source = DataSource(
            conversation_id=conversation_id,
            source_type=source_type,
            website_url=website_url,
            file_name=file_name,
            title=title,
            content_preview=content_preview,
            text_length=text_length,
            total_chunks=total_chunks,
            file_size_bytes=file_size_bytes,
            message_id=message_id,
            scraped_at=scraped_at or datetime.now()
        )
        self.db.add(data_source)
        self.db.commit()
        self.db.refresh(data_source)
        return data_source
    
    def get_by_id(self, source_id: int) -> Optional[DataSource]:
        """Get data source by ID"""
        return self.db.query(DataSource).filter(DataSource.id == source_id).first()
    
    def get_by_conversation_id(self, conversation_id: int) -> List[DataSource]:
        """Get all data sources for a conversation"""
        return self.db.query(DataSource).filter(
            DataSource.conversation_id == conversation_id
        ).all()


