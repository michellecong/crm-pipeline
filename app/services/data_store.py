# services/data_store.py
"""
Data storage service for scraped data
Supports both file-based (legacy) and database storage
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

from sqlalchemy.orm import Session
from app.dao import DataSourceDAO, SourceChunkDAO
from app.models.data_source import SourceType
from app.services.chunking_service import ChunkingService

logger = logging.getLogger(__name__)


class DataStore:
    """Data storage service with support for database and file storage"""
    
    def __init__(self, data_dir: str = "data", db: Optional[Session] = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.db = db
        
        # Create subdirectory for scraped data (for file mode)
        (self.data_dir / "scraped").mkdir(exist_ok=True)
        
        # Initialize DAOs if database is available
        if self.db:
            self.data_source_dao = DataSourceDAO(db)
            self.source_chunk_dao = SourceChunkDAO(db)
            self.chunking_service = ChunkingService()
        else:
            logger.warning("Database not provided, using file storage only")
    
    def save_scraped_data(self, company_name: str, data: Dict, 
                          user_id: int = 1, save_to_file: bool = False) -> str:
        """
        Save scraped data to database or file based on parameters
        
        Args:
            company_name: Company name
            data: Scraped data dictionary
            user_id: User ID (default: 1 for single-user system)
            save_to_file: If True, save to file only (skip database)
            
        Returns:
            str: Database ID or filepath
        """
        # If save_to_file is True, only save to file (even if db is available)
        if save_to_file:
            return self._save_to_file(company_name, data)
        
        # Otherwise, save to database if available
        if self.db:
            return self._save_to_database(company_name, data, user_id)
        
        # Fallback to file storage if no db available
        return self._save_to_file(company_name, data)
    
    def _save_to_database(self, company_name: str, data: Dict, user_id: int) -> str:
        """Save scraped data to database"""
        try:
            # Use a default conversation_id = 1 for now
            # (In the future, this should be created by the user/conversation flow)
            conversation_id = 1
            
            # Process each scraped content item
            saved_sources = []
            scraped_content = data.get('scraped_content', [])
            
            for item in scraped_content:
                if not item.get('success'):
                    continue
                
                # Determine source type
                content_type = item.get('content_type', 'unknown')
                if content_type == 'website':
                    source_type = SourceType.WEBSITE
                else:
                    source_type = SourceType.WEBSITE  # Default to website for now
                
                # Get content to chunk
                content = item.get('processed_markdown') or item.get(
                    'markdown', ''
                )
                
                if not content:
                    continue
                
                # Create preview (first 500 characters)
                preview = content[:500]
                
                # Chunk the content
                chunks = self.chunking_service.chunk_text(content)
                
                # Create data source
                data_source = self.data_source_dao.create(
                    conversation_id=conversation_id,
                    source_type=source_type,
                    website_url=item.get('url'),
                    file_name=company_name,  # Store company name
                    title=item.get('title'),
                    content_preview=preview,
                    text_length=len(content),
                    total_chunks=len(chunks),
                    scraped_at=datetime.fromisoformat(item.get('scraped_at'))
                )
                
                # Save chunks
                chunk_contents = [chunk['text'] for chunk in chunks]
                self.source_chunk_dao.create_batch(data_source.id, chunk_contents)
                
                saved_sources.append({
                    'source_id': data_source.id,
                    'url': item.get('url'),
                    'chunks_count': len(chunks)
                })
            
            logger.info(
                f"Saved {len(saved_sources)} data sources to database for {company_name}"
            )
            return f"conversation_{conversation_id}"
            
        except Exception as e:
            logger.error(f"Failed to save to database: {e}", exc_info=True)
            raise
    
    def _save_to_file(self, company_name: str, data: Dict) -> str:
        """Save scraped data to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{company_name.lower().replace(' ', '_')}_{timestamp}.json"
        filepath = self.data_dir / "scraped" / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved scraped data to: {filepath}")
        return str(filepath)
    
    def load_latest_scraped_data(self, company_name: str) -> Optional[Dict]:
        """
        Load the most recent scraped data for a company
        
        Returns:
            Dict with scraped data or None if not found
        """
        pattern = f"{company_name.lower().replace(' ', '_')}_*.json"
        files = list((self.data_dir / "scraped").glob(pattern))
        
        if not files:
            logger.warning(f"No scraped data found for {company_name}")
            return None
        
        # Get the most recent file
        latest_file = max(files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded scraped data from: {latest_file}")
        return data
    
    def list_scraped_companies(self) -> List[Dict]:
        """
        List all scraped companies with metadata
        
        Returns:
            List of dicts with company info
        """
        files = list((self.data_dir / "scraped").glob("*.json"))
        
        companies = []
        for filepath in files:
            # Parse filename: companyname_timestamp.json
            filename = filepath.stem  # Remove .json
            parts = filename.rsplit('_', 2)  # Split from right, max 2 splits
            
            if len(parts) >= 2:
                company_name = ' '.join(parts[:-2]).replace('_', ' ').title()
                timestamp = f"{parts[-2]}_{parts[-1]}"
            else:
                company_name = filename.replace('_', ' ').title()
                timestamp = "unknown"
            
            stat = filepath.stat()
            companies.append({
                'company_name': company_name,
                'filename': filepath.name,
                'filepath': str(filepath),
                'timestamp': timestamp,
                'size_kb': round(stat.st_size / 1024, 2),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        # Sort by modification time, newest first
        companies.sort(key=lambda x: x['modified'], reverse=True)
        return companies
    


# Singleton instance
_data_store = None


def get_data_store(db: Optional[Session] = None) -> DataStore:
    """
    Get or create DataStore singleton
    
    Args:
        db: Database session (optional, for file storage only)
        
    Returns:
        DataStore instance
    """
    global _data_store
    
    # If db is provided, create a new instance with db
    if db is not None:
        return DataStore(db=db)
    
    # Otherwise use singleton (file storage)
    if _data_store is None:
        _data_store = DataStore()
    return _data_store

