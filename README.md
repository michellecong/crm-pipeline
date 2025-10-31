# CRM Pipeline API

Data collection API for scraping company information from the web.

## Quick Start

### 1. Create Virtual Environment 

Before installing dependencies, create and activate a virtual environment:

**Mac/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Configure API Keys

Create a `.env` file:

```bash
# Google Custom Search (used for web search)
GOOGLE_CSE_API_KEY=your_google_api_key
GOOGLE_CSE_CX=your_search_engine_cx

# Firecrawl - for web scraping
FIRECRAWL_API_KEY=your_firecrawl_key_here

# OpenAI - for LLM services and LLM web search
OPENAI_API_KEY=your_openai_key_here

# Optional: OpenAI Configuration (defaults shown)
# OPENAI_MODEL=gpt-4.1  # Use gpt-4.1 or newer for web search support
# OPENAI_TEMPERATURE=0.0
# OPENAI_MAX_TOKENS=2000

# Perplexity - for provider-based web search (optional if using Google only)
# Set this to enable the Perplexity provider
PERPLEXITY_API_KEY=your_perplexity_key_here
```

**API Keys:**
- Firecrawl: [firecrawl.dev](https://www.firecrawl.dev/) (Free: 500 credits/month)
- OpenAI: [platform.openai.com](https://platform.openai.com/api-keys)
- Perplexity: [perplexity.ai](https://www.perplexity.ai)

### 4. Run Server

```bash
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Use API

```bash
# Search company (Google - default provider)
curl -X POST http://localhost:8000/api/v1/search/company \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "include_news": true,
    "include_case_studies": true
  }'

# Search company (Perplexity provider)
curl -X POST http://localhost:8000/api/v1/search/company \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "include_news": true,
    "include_case_studies": true,
    "provider": "perplexity"
  }'

# Scrape company data
curl -X POST http://localhost:8000/api/v1/scrape/company \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "max_urls": 5,
    "save_to_file": true
  }'

# View saved data
curl http://localhost:8000/api/v1/scrape/saved

# Generate personas from company data
curl -X POST http://localhost:8000/api/v1/llm/persona/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 3
  }'

# LLM-powered web search (structured JSON with guaranteed official website)
curl -X POST http://localhost:8000/api/v1/search/web \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce"
  }'
```

The API supports both Google Custom Search and Perplexity Search. Use the `provider` field on `/api/v1/search/company` to select `google` (default) or `perplexity`.

The `/api/v1/search/web` endpoint uses OpenAI's LLM with web search capabilities to intelligently plan and execute search queries, returning structured JSON with company information including official website, products, news, and case studies.

## API Documentation

Interactive docs: http://localhost:8000/docs

## Main Endpoints

### Data Collection
| Endpoint                 | Method | Description                                    |
| ------------------------ | ------ | ---------------------------------------------- |
| `/api/v1/search/company` | POST   | Search for company URLs (Google/Perplexity)    |
| `/api/v1/search/web`     | POST   | LLM-powered web search (structured JSON)       |
| `/api/v1/scrape/company` | POST   | Search and scrape content                      |
| `/api/v1/scrape/saved`   | GET    | List saved data                                |
| `/api/v1/pdf/process/`   | POST   | Process PDF and chunk text                     |

### LLM Service
| Endpoint                     | Method | Description                    |
| ---------------------------- | ------ | ------------------------------ |
| `/api/v1/llm/generate`      | POST   | Generate text with LLM         |
| `/api/v1/llm/persona/generate` | POST | Generate buyer personas        |
| `/api/v1/llm/test`          | GET    | Test LLM connectivity          |
| `/api/v1/llm/config`        | GET    | Get LLM configuration          |
| `/api/v1/llm/config`        | PATCH  | Update LLM configuration       |

## Data Storage

Scraped data is saved to `data/scraped/` as JSON files when `save_to_file: true`.

## Testing

### Test LLM Service (Mock - No API Key Required)
```bash
python -m pytest tests/test_llm_mock.py -v
```

### Test LLM Connection (Requires API Key)
```bash
python tests/test_llm_connection.py
```

### Test All Services
```bash
python -m pytest tests/ -v
```

### Test Persona Generation

#### Basic Persona Generation
```bash
# Generate 3 personas for Salesforce
curl -X POST http://localhost:8000/api/v1/llm/persona/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 3
  }'
```

#### Generate More Personas
```bash
# Generate 5 personas for Microsoft
curl -X POST http://localhost:8000/api/v1/llm/persona/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Microsoft",
    "generate_count": 5
  }'
```

#### Expected Response Format
```json
{
  "company_name": "Salesforce",
  "personas": [
    {
      "name": "Chief Financial Officer (CFO)",
      "tier": "tier_1",
      "job_title": "Chief Financial Officer",
      "industry": "Technology / Cloud Software",
      "department": "Finance",
      "location": "San Francisco, CA",
      "company_size": 79000,
      "description": "Senior executive responsible for financial strategy...",
      "decision_power": "final_approver",
      "pain_points": ["Controlling SaaS spend", "Demonstrating ROI"],
      "goals": ["Drive profitable growth", "Improve capital allocation"],
      "communication_preferences": ["Executive summaries", "Data-driven reports"]
    }
  ],
  "tier_classification": {
    "tier_1": ["persona_1"],
    "tier_2": ["persona_2"],
    "tier_3": ["persona_3"]
  },
  "context_length": 4621,
  "generated_at": "2025-10-23T14:43:29.571252",
  "total_personas": 3,
  "model": "gpt-4o"
}
```

#### Testing Different Companies
```bash
# Test with different company types
curl -X POST http://localhost:8000/api/v1/llm/persona/generate \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Tesla", "generate_count": 3}'

curl -X POST http://localhost:8000/api/v1/llm/persona/generate \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Shopify", "generate_count": 4}'

curl -X POST http://localhost:8000/api/v1/llm/persona/generate \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Stripe", "generate_count": 3}'
```

### Test LLM Web Search

#### Basic LLM Web Search
```bash
# Search for company information using LLM-powered web search
curl -X POST http://localhost:8000/api/v1/search/web \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce"
  }'
```

#### What is LLM Web Search?

The LLM Web Search endpoint (`/api/v1/search/web`) uses OpenAI's language model with web search capabilities to intelligently gather company information. Unlike traditional search APIs, this endpoint:

**Key Features:**
- **Intelligent Query Planning**: LLM automatically plans and executes strategic search queries
- **Guaranteed Official Website**: Ensures the company's official website is always included
- **Structured JSON Output**: Returns validated, structured data with products, news, and case studies
- **High-Authority Sources**: Prioritizes reputable sources (Bloomberg, Reuters, TechCrunch, etc.)
- **Deduplication**: Automatically removes duplicate URLs

**Use Cases:**
- Automated company research for B2B sales intelligence
- Building buyer personas based on customer case studies
- Identifying customer pain points from success stories
- Tracking company news and product launches

#### Expected Response Format
```json
{
  "company": "Salesforce",
  "queries_planned": [
    "Salesforce official website",
    "site:salesforce.com products solutions",
    "Salesforce customer case study success story",
    "Salesforce news announcement 2024 2025"
  ],
  "official_website": [
    {
      "url": "https://www.salesforce.com",
      "title": "Salesforce: The Customer Company - CRM & Cloud Solutions"
    }
  ],
  "products": [
    {
      "url": "https://www.salesforce.com/products/sales-cloud/",
      "title": "Sales Cloud - Sales CRM & Customer Relationship Management"
    }
  ],
  "news": [
    {
      "url": "https://techcrunch.com/2024/...",
      "title": "Salesforce announces new AI features",
      "published_at": "2024-10-15"
    }
  ],
  "case_studies": [
    {
      "url": "https://www.salesforce.com/customer-success-stories/...",
      "title": "How Company X Increased Sales by 40% with Salesforce"
    }
  ],
  "collected_at": "2025-10-31T12:00:00"
}
```

#### Testing Different Companies
```bash
# Test with various companies
curl -X POST http://localhost:8000/api/v1/search/web \
  -H "Content-Type: application/json" \
  -d '{"company_name": "DocuSign"}'

curl -X POST http://localhost:8000/api/v1/search/web \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Miro"}'
```

#### Command Line Test Script
```bash
# Run the test script
python test_llm_web_search.py
```

This script demonstrates both freeform and structured versions of the LLM web search functionality.

## Troubleshooting

**SSL Certificate Error (macOS)**:

```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

**Missing API Key**:

- Check `.env` file exists in project root
- Restart server after adding keys

**LLM Service Not Working**:

- Ensure `OPENAI_API_KEY` is set in `.env`
- Test with: `GET /api/v1/llm/test`
- Check API quota at https://platform.openai.com/usage

**Persona Generation Issues**:

- **No scraped data**: The endpoint will automatically scrape company data if none exists
- **Slow response**: Persona generation takes 10-30 seconds depending on company size
- **Empty personas**: Check that company name is spelled correctly
- **API errors**: Ensure all API keys (Google CSE, Firecrawl, OpenAI) are valid
- **Token limits**: Increase `max_completion_tokens` if personas are truncated


## Project Structure

```
crm-pipeline/
├── app/
│   ├── main.py                      # FastAPI app
│   ├── routers/                     # API endpoints
│   │   ├── search.py               # Search & LLM web search endpoints
│   │   ├── scraping.py             # Web scraping endpoints
│   │   └── llm.py                  # LLM & persona generation endpoints
│   ├── services/                    # Business logic
│   │   ├── llm_web_search_service.py  # LLM-powered web search
│   │   ├── search_service.py       # Traditional search (Google/Perplexity)
│   │   ├── llm_service.py          # LLM text generation
│   │   └── generator_service.py    # Persona generation
│   └── schemas/                     # Data models
│       └── search.py               # Search & LLM web search schemas
├── data/
│   ├── scraped/                     # Saved scraped data
│   └── generated/                   # Generated personas
├── tests/                           # Tests
├── test_llm_web_search.py          # LLM web search test script
├── requirements.txt                 # Dependencies
└── .env                             # API keys (create this)
```

## Cost

- Smart Proxy: ~$0.01/10 searches
- Firecrawl: ~10 credits/10 URLs (500 free/month)
