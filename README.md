# CRM Pipeline API

Data collection API for scraping company information from the web.

## Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file:

```bash
# Smart Proxy - for Google search (Already configured ✅)
SMART_PROXY_API_KEY=your_key_here

# Firecrawl - for web scraping
FIRECRAWL_API_KEY=your_firecrawl_key_here
```

Get Firecrawl API key: https://www.firecrawl.dev/ (Free: 500 credits/month)

### 3. Run Server

```bash
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Use API

```bash
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
```

## API Documentation

Interactive docs: http://localhost:8000/docs

## Main Endpoints

| Endpoint                 | Method | Description               |
| ------------------------ | ------ | ------------------------- |
| `/api/v1/search/company` | POST   | Search for company URLs   |
| `/api/v1/scrape/company` | POST   | Search and scrape content |
| `/api/v1/scrape/saved`   | GET    | List saved data           |

## Data Storage

Scraped data is saved to `data/scraped/` as JSON files when `save_to_file: true`.

## Troubleshooting

**SSL Certificate Error (macOS)**:

```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

**Missing API Key**:

- Check `.env` file exists in project root
- Restart server after adding keys

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
