# services/data_store.py
"""
Simple data storage service for scraped data
Saves to JSON files for easy access and LLM processing
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataStore:
    """Simple file-based data storage"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Create subdirectory for scraped data
        (self.data_dir / "scraped").mkdir(exist_ok=True)
    
    def save_scraped_data(self, company_name: str, data: Dict) -> str:
        """
        Save scraped data to JSON file
        
        Returns:
            filepath: Path to saved file
        """
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


def get_data_store() -> DataStore:
    """Get or create DataStore singleton"""
    global _data_store
    if _data_store is None:
        _data_store = DataStore()
    return _data_store

