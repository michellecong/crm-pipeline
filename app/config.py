# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class Settings:
    # Google Custom Search configuration
    GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY")
    GOOGLE_CSE_CX = os.getenv("GOOGLE_CSE_CX")
    GOOGLE_CSE_BASE_URL = "https://www.googleapis.com/customsearch/v1"

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

    # OpenAI configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "1.0"))
    OPENAI_MAX_COMPLETION_TOKENS = int(os.getenv("OPENAI_MAX_COMPLETION_TOKENS", "2000"))
    OPENAI_TOP_P = float(os.getenv("OPENAI_TOP_P", "1.0"))
    OPENAI_FREQUENCY_PENALTY = float(os.getenv("OPENAI_FREQUENCY_PENALTY", "0.0"))
    OPENAI_PRESENCE_PENALTY = float(os.getenv("OPENAI_PRESENCE_PENALTY", "0.0"))

    # Perplexity configuration
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
    PERPLEXITY_BASE_URL = "https://api.perplexity.ai"

    # Database configuration
    DATABASE_URL = os.getenv("DATABASE_URL")

# Create global settings instance
settings = Settings()

