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

# OpenAI - for LLM services
OPENAI_API_KEY=your_openai_key_here

# Optional: OpenAI Configuration (defaults shown)
# OPENAI_MODEL=gpt-5-mini
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

# Generate product catalog from company data
curl -X POST http://localhost:8000/api/v1/llm/products/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "max_products": 10
  }'

# Response format:
# {
#   "products": [
#     {
#       "product_name": "Sales Cloud",
#       "description": "Complete CRM platform for managing sales pipelines..."
#     }
#   ]
# }

# Generate personas (auto-loads products if available)
curl -X POST http://localhost:8000/api/v1/llm/persona/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 3
  }'
# Note: If you previously generated products for this company, they will be
# automatically loaded and used. Otherwise, personas are generated from web content.

# Generate personas WITH explicit product catalog (override auto-load)
curl -X POST http://localhost:8000/api/v1/llm/persona/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 3,
    "products": [
      {
        "product_name": "Sales Cloud",
        "description": "Complete CRM platform for managing sales pipelines..."
      },
      {
        "product_name": "Service Cloud",
        "description": "Customer service platform that unifies support across channels..."
      }
    ]
  }'
```

The API supports both Google Custom Search and Perplexity Search. Use the `provider` field on `/api/v1/search/company` to select `google` (default) or `perplexity`.

## Product Auto-Loading Feature

The persona generator automatically loads previously generated products for the same company:

**Workflow:**
1. Generate products: `POST /api/v1/llm/products/generate`
   - Products saved to `data/generated/salesforce_products_*.json`
2. Generate personas: `POST /api/v1/llm/persona/generate`
   - System automatically finds and loads latest products
   - Personas are generated with product context
   - No manual passing required!

**Behavior:**
- ✅ **Products found**: Auto-loaded and used for persona generation
- ℹ️ **No products found**: Personas generated from web content only
- 🔄 **Override**: Pass explicit `products` parameter to use different products

**Logs to watch for:**
```
✅ Auto-loaded 5 products from previous generation
📦 Loaded 5 products from: salesforce_products_2025-10-30T21-27-16.json
```

## API Documentation

Interactive docs: http://localhost:8000/docs

## Main Endpoints

### Data Collection
| Endpoint                 | Method | Description               |
| ------------------------ | ------ | ------------------------- |
| `/api/v1/search/company` | POST   | Search for company URLs   |
| `/api/v1/scrape/company` | POST   | Search and scrape content |
| `/api/v1/scrape/saved`   | GET    | List saved data           |
| `/api/v1/pdf/process/`   | POST   | Process PDF and chunk text|

### LLM Service
| Endpoint                     | Method | Description                    |
| ---------------------------- | ------ | ------------------------------ |
| `/api/v1/llm/generate`      | POST   | Generate text with LLM         |
| `/api/v1/llm/products/generate` | POST | Generate product catalog       |
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
│   ├── main.py              # FastAPI app
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic
│   └── schemas/             # Data models
├── data/scraped/            # Saved data
├── tests/                   # Tests
├── requirements.txt         # Dependencies
└── .env                     # API keys (create this)
```

## Cost

- Smart Proxy: ~$0.01/10 searches
- Firecrawl: ~10 credits/10 URLs (500 free/month)
