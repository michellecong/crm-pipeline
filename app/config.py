# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class Settings:
    # Smart Proxy configuration
    SMART_PROXY_API_KEY = os.getenv("SMART_PROXY_API_KEY")
    SMART_PROXY_BASE_URL = "https://scraper.smartproxy.org/v1/query"

    # Search result limits
    MAX_NEWS_RESULTS = 10
    MAX_CASE_STUDY_RESULTS = 15
    MAX_OFFICIAL_SITE_RESULTS = 5

    REQUEST_TIMEOUT = 30


# Create global settings instance
settings = Settings()


# Manual test: print the first 10 characters of the API key
if __name__ == "__main__":
    print(f"✅ API Key loaded: {settings.SMART_PROXY_API_KEY[:10]}...")


