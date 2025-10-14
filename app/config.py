# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class Settings:
    # Smart Proxy configuration
    SMART_PROXY_API_KEY = os.getenv("SMART_PROXY_API_KEY")
    SMART_PROXY_BASE_URL = "https://scraper.smartproxy.org/v1/query"

    # Firecrawl configuration
    FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
    FIRECRAWL_BASE_URL = "https://api.firecrawl.dev"

    # Search result limits (actual results may be less)
    MAX_NEWS_RESULTS = 10
    MAX_CASE_STUDY_RESULTS = 10
    MAX_OFFICIAL_SITE_RESULTS = 2

    REQUEST_TIMEOUT = 30
    
    # Scraping limits
    MAX_URLS_TO_CRAWL = 20
    MAX_CONCURRENT_SCRAPES = 10  # Concurrent scrape count for better performance


# Create global settings instance
settings = Settings()


# Manual test: print the first 10 characters of the API key
if __name__ == "__main__":
    print(f"✅ API Key loaded: {settings.SMART_PROXY_API_KEY[:10]}...")


