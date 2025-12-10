# LLM-Driven B2B Sales Intelligence and Outreach Planning System

Comprehensive B2B sales intelligence platform that generates buyer personas, pain-point to value-proposition mappings, and multi-touch outreach sequences from company web data, CRM data, and PDF documents.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Core Features](#core-features)
  - [Data Sources Integration](#data-sources-integration)
  - [Pipeline Generation](#pipeline-generation)
  - [Export Functionality](#export-functionality)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

---

## Quick Start

### 1. Create Virtual Environment

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

Create a `.env` file in the project root:
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

# Perplexity - for web search and product generation
# Required for product generation (uses Perplexity for web search with citations)
PERPLEXITY_API_KEY=your_perplexity_key_here
# Optional: Perplexity model (default: sonar)
# PERPLEXITY_MODEL=sonar
```

**API Keys:**
- Firecrawl: [firecrawl.dev](https://www.firecrawl.dev/) (Free: 500 credits/month)
- OpenAI: [platform.openai.com](https://platform.openai.com/api-keys)
- Perplexity: [perplexity.ai](https://www.perplexity.ai) (Required for product generation)

### 4. Run Server
```bash
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test the API
```bash
# Generate full pipeline
curl -X POST http://localhost:8000/api/v1/llm/pipeline/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 5,
    "provider": "google"
  }'
```

Interactive API docs: http://localhost:8000/docs

---

## Configuration

### Environment Variables

All API keys are configured in `.env` file (see Quick Start section).

### Data Folders

The system uses three data folders:

```
crm-pipeline/
├── crm-data/          # Create this folder for CRM CSV files (optional)
├── pdf-data/          # Create this folder for PDF documents (optional)
└── data/              # Auto-created by the system
    ├── scraped/       # Auto-generated web scraping results
    └── generated/     # Auto-generated personas, mappings, sequences
```

**Note**: `crm-data/` and `pdf-data/` folders are NOT included in git (they're in `.gitignore`). Create them manually when needed:

```bash
mkdir -p crm-data  # For CRM CSV files
mkdir -p pdf-data  # For PDF documents
```

---

## Core Features

### Data Sources Integration

The system supports **three data sources** that are automatically combined:

1. **Web Scraped Content** (Required) - Automatically scraped from company websites
2. **CRM Customer Data** (Optional) - CSV files from your CRM system
3. **PDF Documents** (Optional) - Product guides, case studies, company materials

All three sources are **automatically integrated** through the `DataAggregator` service. Simply place your files in the appropriate folders and the system will use them automatically.

#### How It Works

**Step 1: Prepare your data files**
```bash
# Add CRM data
cp your_crm_export.csv crm-data/

# Add PDF documents
cp your_product_guide.pdf pdf-data/
cp your_case_studies.pdf pdf-data/
```

**Step 2: Generate content (automatically uses all available data)**
```bash
curl -X POST http://localhost:8000/api/v1/llm/persona/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 5
  }'
```

The system will **automatically**:
- ✅ Scrape web content
- ✅ Load CRM data from `crm-data/` (if files exist)
- ✅ Load PDF documents from `pdf-data/` (if files exist)
- ✅ Combine all sources into one comprehensive context
- ✅ Generate personas using all available information

#### CRM Data Format

**Supported CRM Systems:**
- ✅ Salesforce
- ✅ HubSpot
- ✅ Pipedrive
- ✅ Generic CSV formats

**Supported File Types:**
- **Accounts/Companies** (company information)
- **Contacts** (people, job titles, departments)
- **Opportunities/Deals** (sales pipeline, deal stages, amounts)

**Example Files:**

**accounts.csv** (Company data):
```csv
company_name,industry,country,company_size,revenue
Acme Corp,Technology,United States,500,5000000
TechStart Inc,SaaS,Canada,150,1000000
```

**contacts.csv** (Contact data):
```csv
firstname,lastname,email,job_title,department
John,Smith,john@acme.com,VP of Sales,Sales
Jane,Doe,jane@techstart.com,Director of Marketing,Marketing
```

**opportunities.csv** (Deal data):
```csv
deal_name,deal_stage,deal_amount,company_name
Q4 Enterprise Deal,Qualified To Buy,250000,Acme Corp
Annual Subscription,Decision Maker Brought-In,50000,TechStart Inc
```

The system automatically:
- Identifies file types
- Detects CRM system (Salesforce/HubSpot/Pipedrive)
- Normalizes column names
- Generates statistics (industry distribution, location, job titles, deal stages)
- Creates a text summary for LLM consumption

#### PDF Documents

**Supported Content:**
- Product guides
- Case studies
- Company overview documents
- Technical documentation
- Sales materials

**Limits:**
- Maximum PDFs: 5 files (to avoid context overflow)
- Maximum per PDF: 5,000 characters (automatically truncated)

#### Data Flow

```
User uploads files → Folders (crm-data/, pdf-data/)
                            ↓
                     DataAggregator
                            ↓
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
   Web Content        CRM Data           PDF Data
   (Required)         (Optional)         (Optional)
        ↓                  ↓                  ↓
        └──────────────────┴──────────────────┘
                            ↓
                  Combined Context String
                            ↓
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
   Persona Gen       Mapping Gen       Outreach Gen
```

**Log Output Example:**
```
[DataAggregator] Preparing context for Salesforce
✅ Web content loaded: 12,450 chars
✅ CRM data loaded: 3,200 chars
✅ PDF data loaded: 4,100 chars
[DataAggregator] Total context prepared: 19,750 chars
```

Or if no optional data:
```
[DataAggregator] Preparing context for Salesforce
✅ Web content loaded: 12,450 chars
ℹ️  No CRM data available (folder empty or not found)
ℹ️  No PDF data available (folder empty or not found)
[DataAggregator] Total context prepared: 12,450 chars
```

**Benefits:**
- ✅ **Richer personas** - Based on actual customer data
- ✅ **Better targeting** - Job titles from real contacts
- ✅ **Accurate geography** - Customer location distribution
- ✅ **Precise pain points** - From case studies and sales materials
- ✅ **Product alignment** - From internal product documents

---

### Pipeline Generation

The system provides a **production-ready 4-stage pipeline** and two alternative approaches for comparison and testing.

#### 4-Stage Pipeline (Production - Recommended)

**Endpoint**: `POST /api/v1/llm/pipeline/generate`

This is the **final production pipeline** with the best performance and quality.

**Architecture**: 4 sequential LLM calls with explicit inter-stage data flow
- **Stage 1**: Generate products from web content
- **Stage 2**: Generate personas using products + web content + CRM + PDF
- **Stage 3**: Generate mappings using personas + products
- **Stage 4**: Generate sequences using personas_with_mappings

**Key Features:**
- ✅ Personas receive actual products JSON for context
- ✅ Mappings receive actual personas + products for context
- ✅ Each stage can be optimized independently
- ✅ Best quality through explicit information flow
- ✅ Highest performance and accuracy

**Use Case**: Production deployment, best quality output

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/llm/pipeline/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 5,
    "provider": "google"
  }'
```

#### Alternative Approaches (For Comparison & Testing)

The following endpoints are provided for **comparison and testing purposes** to evaluate different architectural approaches:

**3-Stage Pipeline** (`POST /api/v1/llm/three-stage/generate`)
- Consolidates final two stages (mappings + sequences) into one call
- Used for ablation studies to test impact of stage consolidation

**2-Stage Pipeline** (`POST /api/v1/llm/two-stage/generate`)
- Consolidates persona-related outputs (personas + mappings + sequences) into one call
- Used for architectural comparison studies

**Note**: These alternative approaches are primarily used for research, evaluation, and architectural comparison purposes. The 4-stage pipeline is recommended for production use.

#### Auto-Loading Features

The system automatically loads previously generated data:

**Persona Generation:**
- Auto-loads products if available
- Auto-loads CRM and PDF data if folders contain files

**Mapping Generation:**
- Auto-loads products AND personas (both required)
- Auto-loads CRM and PDF data if available

**Logs to watch for:**
```
✅ Auto-loaded 5 products from previous generation
📦 Loaded 5 products from: salesforce_products_2025-10-30.json
👥 Loaded 3 personas from: salesforce_personas_2025-10-30.json
✅ CRM data loaded: 3,200 chars
✅ PDF data loaded: 4,100 chars
```

---

### Export Functionality

The system supports exporting generated content in **three formats**:

1. **JSON** (default) - Original format, automatically saved
2. **CSV** - For spreadsheet applications (Excel, Google Sheets)
3. **Markdown** - For documentation and easy reading

#### API Endpoints

##### 1. Export from Saved File

**Endpoint**: `GET /api/v1/export/{file_path}?format={format}`

Export a previously saved JSON file to CSV or Markdown format.

**Parameters:**
- `file_path`: Path to the JSON file (relative to `data/generated/`)
- `format`: Export format (`json`, `csv`, or `markdown`)

**Example:**
```bash
# Export personas to CSV
curl -X GET "http://localhost:8000/api/v1/export/salesforce_personas_2025-12-06T23-56-15.json?format=csv" \
  --output personas.csv

# Export personas to Markdown
curl -X GET "http://localhost:8000/api/v1/export/salesforce_personas_2025-12-06T23-56-15.json?format=markdown" \
  --output personas.md

# Get original JSON
curl -X GET "http://localhost:8000/api/v1/export/salesforce_personas_2025-12-06T23-56-15.json?format=json" \
  --output personas.json
```

##### 2. Convert Data Directly

**Endpoint**: `POST /api/v1/export/convert?format={format}&content_type={type}`

Convert data directly from request body without saving to file first.

**Parameters:**
- `format`: Export format (`json`, `csv`, or `markdown`)
- `content_type`: Optional content type (auto-detected if not provided)

**Request Body**: JSON data (same format as saved files)

**Example:**
```bash
# Convert personas data to CSV
curl -X POST "http://localhost:8000/api/v1/export/convert?format=csv&content_type=personas" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generator_type": "personas",
    "generated_at": "2025-12-06T23:56:15",
    "result": {
      "personas": [...]
    }
  }' \
  --output personas.csv
```

#### Export Formats

##### CSV Format

**Personas CSV:**
```csv
persona_name,tier,industry,company_size_range,company_type,location,job_titles,excluded_job_titles,description
US Enterprise SaaS - Revenue Leaders,tier_1,SaaS,2000-10000 employees,Enterprise B2B SaaS,California,"CRO; VP Sales; ...","HR Manager; IT Director; ...","High-growth SaaS companies..."
```

**Products CSV:**
```csv
product_name,description,source_url
Sales Cloud,Complete CRM platform...,https://www.salesforce.com/products/sales-cloud
Service Cloud,Customer service platform...,https://www.salesforce.com/products/service-cloud
```

**Mappings CSV:**
```csv
persona_name,pain_point,value_proposition
US Enterprise SaaS - Revenue Leaders,Sales teams struggle with...,Agents consolidate multiple tools...
```

**Sequences CSV:**
```csv
sequence_name,persona_name,objective,total_touches,duration_days,touch_order,touch_type,timing_days,touch_objective,subject_line,content_suggestion,hints
Revenue Leaders Outreach Sequence,US Enterprise SaaS - Revenue Leaders,Secure discovery meeting,5,14,1,email,0,Introduce pipeline visibility,30% forecast accuracy boost,Hi {first_name}...,Personalize with recent news
```

##### Markdown Format

**Personas Markdown:**
```markdown
# Salesforce - Personas

**Generated at:** 2025-12-06T23:56:15

---

## Persona 1: US Enterprise SaaS - Revenue Leaders

**Tier:** tier_1

**Industry:** SaaS

**Company Size:** 2000-10000 employees

**Location:** California

**Company Type:** Enterprise B2B SaaS companies

### Target Job Titles

- CRO
- VP Sales
- Chief Revenue Officer
...

### Excluded Job Titles

- HR Manager
- IT Director
...

### Description

High-growth SaaS companies with 200-500 sales reps...
```

#### Supported Content Types

| Content Type | JSON | CSV | Markdown | Notes |
|--------------|------|-----|----------|-------|
| **personas** | ✅ | ✅ | ✅ | Full persona details |
| **products** | ✅ | ✅ | ✅ | Product catalog |
| **mappings** | ✅ | ✅ | ✅ | Pain-point mappings |
| **sequences** | ✅ | ✅ | ✅ | Outreach sequences |
| **pipeline** | ✅ | ✅ | ✅ | All components (products + personas + mappings + sequences) |
| **two_stage** | ✅ | ✅ | ✅ | Products + personas+mappings+sequences |
| **three_stage** | ✅ | ✅ | ✅ | Products + personas + mappings+sequences |

---

## API Documentation

### Main Endpoints

#### Data Collection
| Endpoint                 | Method | Description                                    |
| ------------------------ | ------ | ---------------------------------------------- |
| `/api/v1/search/company` | POST   | Search for company URLs (Google/Perplexity)    |
| `/api/v1/scrape/company` | POST   | Search and scrape content                      |
| `/api/v1/scrape/saved`   | GET    | List saved data                                |
| `/api/v1/pdf/process/`   | POST   | Process PDF and chunk text                     |
| `/api/v1/crm/parse`      | POST   | Upload and parse CRM CSV file                  |

#### LLM Service
| Endpoint                     | Method | Description                    |
| ---------------------------- | ------ | ------------------------------ |
| `/api/v1/llm/generate`      | POST   | Generate text with LLM         |
| `/api/v1/llm/products/generate` | POST | Generate product catalog (uses Perplexity web search) |
| `/api/v1/llm/persona/generate` | POST | Generate buyer personas        |
| `/api/v1/llm/mappings/generate` | POST | Generate pain-point to value-prop mappings |
| `/api/v1/llm/pipeline/generate` | POST   | Run full 4-stage pipeline (products → personas → mappings → sequences) |
| `/api/v1/llm/three-stage/generate` | POST   | Run 3-stage pipeline (products → personas → mappings+sequences) |
| `/api/v1/llm/two-stage/generate` | POST   | Run 2-stage pipeline (products → personas+mappings+sequences) |
| `/api/v1/llm/test`          | GET    | Test LLM connectivity          |
| `/api/v1/llm/config`        | GET    | Get LLM configuration          |
| `/api/v1/llm/config`        | PATCH  | Update LLM configuration       |

#### Outreach Sequences
| Endpoint                     | Method | Description                    |
| ---------------------------- | ------ | ------------------------------ |
| `/api/v1/outreach/generate` | POST   | Generate multi-touch outreach sequences |

#### Export
| Endpoint                     | Method | Description                    |
| ---------------------------- | ------ | ------------------------------ |
| `/api/v1/export/{file_path}` | GET    | Export saved file to JSON/CSV/Markdown |
| `/api/v1/export/convert`     | POST   | Convert data directly to JSON/CSV/Markdown |

#### Pipeline Evaluation
| Endpoint                              | Method | Description                                         |
| ------------------------------------- | ------ | --------------------------------------------------- |
| `/api/v1/pipeline/evaluation/completeness` | POST   | Evaluate pipeline completeness (products, personas, mappings, sequences) |

### Search Options

The system provides two search methods:

- **Google Custom Search** (default): `POST /api/v1/search/company` with `"provider": "google"`
- **Perplexity Search**: `POST /api/v1/search/company` with `"provider": "perplexity"`

### Product Generation

The product generation endpoint uses Perplexity's web search capabilities to find and extract product information directly from the company's official website.

**Features:**
- **Web Search Integration**: Uses Perplexity Sonar model for real-time web search
- **Source URLs**: Each product includes the official product page URL (`source_url`)
- **Comprehensive Coverage**: Generates 15-25+ products for large companies
- **B2B Sales Focus**: Optimized for products that business decision-makers purchase

**Requirements:**
- **PERPLEXITY_API_KEY**: Required for product generation
- Product generation does not use scraped context data (uses web search instead)
- Other generators (personas, mappings, outreach) continue to use OpenAI with scraped context

### Outreach Sequences

Generate multi-touch sales outreach sequences for each persona with pain point-value proposition mappings.

**Features:**
- **4-6 touch sequences** per persona
- **Multi-channel strategy**: Email → LinkedIn → Email → Phone → Follow-up
- **Personalized content**: References specific pain points and value propositions
- **Timing optimization**: 2-3 day intervals, 10-21 day total duration
- **Channel-specific guidelines**: Subject lines, content templates, execution hints

**Touch Types:**
- **Email**: Low commitment, high deliverability
- **LinkedIn**: Social proof and credibility building
- **Phone**: High-intent moments
- **Video**: High effort, high impact (used sparingly)

**Sequence Strategy by Tier:**
- **tier_1 (Enterprise)**: 5-6 touches, 14-21 days
- **tier_2 (Mid-market)**: 5 touches, 12-14 days
- **tier_3 (SMB)**: 4 touches, 10 days

---

## Testing

### Test CRM Service
```bash
# Run CRM service tests
pytest tests/test_crm_service.py -v

# Run with coverage
pytest tests/test_crm_service.py --cov=services.crm_service --cov-report=html
```

### Test LLM Connection (Requires API Key)
```bash
python tests/test_llm_connection.py
```

### Test Outreach Generation
```bash
# Run outreach tests
python -m pytest tests/test_outreach.py -v
```

### Test All Services
```bash
python -m pytest tests/ -v
```

### Test CRM Upload
```bash
# Upload a CRM CSV file
curl -X POST http://localhost:8000/api/v1/crm/parse \
  -F "file=@tests/fixtures/mock_crm_data.csv"
```

### Test Persona Generation
```bash
# Generate 3 personas for Salesforce
curl -X POST http://localhost:8000/api/v1/llm/persona/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 3
  }'
```

### Test Export
```bash
# Export personas to CSV
curl -X GET "http://localhost:8000/api/v1/export/salesforce_personas_2025-12-06T23-56-15.json?format=csv" \
  --output personas.csv
```

---

## Troubleshooting

### SSL Certificate Error (macOS)
```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

### Missing API Key
- Check `.env` file exists in project root
- Restart server after adding keys

### LLM Service Not Working
- Ensure `OPENAI_API_KEY` is set in `.env`
- Test with: `GET /api/v1/llm/test`
- Check API quota at https://platform.openai.com/usage

### CRM Upload Issues
- **File too large**: Maximum file size is 20MB. Filter your CRM export to include only recent data or essential columns
- **Invalid format**: Only CSV files are supported. Export from CRM as CSV
- **Empty results**: Check that CSV has proper headers and data rows
- **Column not detected**: Ensure column names contain keywords like "industry", "country", "amount", etc.
- **Special characters**: Use UTF-8 encoding when exporting from your CRM

### CRM Data Not Loading
```bash
# Check if files exist
ls -la crm-data/

# Check file format
head crm-data/accounts.csv

# Check logs
# Look for: "✅ CRM data loaded" or "ℹ️  No CRM data available"
```

### PDF Data Not Loading
```bash
# Check if files exist
ls -la pdf-data/

# Check file format
file pdf-data/*.pdf

# Check logs
# Look for: "✅ PDF data loaded" or "ℹ️  No PDF data available"
```

### Persona Generation Issues
- **No scraped data**: The endpoint will automatically scrape company data if none exists
- **Slow response**: Persona generation takes 10-30 seconds depending on company size
- **Empty personas**: Check that company name is spelled correctly
- **API errors**: Ensure all API keys (Google CSE, Firecrawl, OpenAI) are valid
- **Token limits**: Increase `max_completion_tokens` if personas are truncated

### Context Too Large
If you get context overflow errors:
- Reduce `max_chars` parameter (default: 15000)
- Limit number of PDFs (system limits to 5 automatically)
- Use fewer/smaller CRM files

### Export Issues
- **File Not Found**: Check that the file exists in `data/generated/`
- **Invalid Format**: Use only `json`, `csv`, or `markdown`
- **Empty Data**: Ensure the JSON file contains valid data

---

## Project Structure

```
crm-pipeline/
├── app/
│   ├── main.py                      # FastAPI app
│   ├── routers/                     # API endpoints
│   │   ├── search.py               # Search endpoints (Google/Perplexity)
│   │   ├── scraping.py             # Web scraping endpoints
│   │   ├── llm.py                  # LLM, persona, mapping & outreach generation endpoints
│   │   ├── crm.py                  # CRM upload & parsing endpoints
│   │   ├── pdf.py                  # PDF processing endpoints
│   │   ├── export.py               # Export endpoints
│   │   └── pipeline_evaluate.py    # Pipeline evaluation endpoints
│   ├── generators/                  # Content generators
│   │   ├── base_generator.py       # Base class for all generators
│   │   ├── product_generator.py    # Product catalog generation (uses Perplexity web search)
│   │   ├── persona_generator.py    # Buyer persona generation
│   │   ├── mapping_generator.py    # Pain-point to value-prop mapping generation
│   │   ├── outreach_generator.py   # Outreach sequence generation
│   │   ├── three_stage_generator.py # 3-stage pipeline (mappings + sequences consolidated)
│   │   └── two_stage_generator.py  # 2-stage pipeline (personas + mappings + sequences)
│   ├── services/                    # Business logic
│   │   ├── search_service.py       # Search (Google/Perplexity)
│   │   ├── llm_service.py          # LLM text generation (supports OpenAI and Perplexity)
│   │   ├── generator_service.py    # Generator orchestration
│   │   ├── crm_service.py          # CRM file parsing & analysis
│   │   ├── pdf_service.py          # PDF text extraction
│   │   ├── data_aggregator.py      # Data source aggregation (Web + CRM + PDF)
│   │   └── export_service.py       # Export format conversion
│   └── schemas/                     # Data models
│       ├── search.py               # Search schemas
│       ├── product_schemas.py      # Product catalog schemas (includes source_url)
│       ├── persona_schemas.py      # Persona schemas
│       ├── mapping_schemas.py      # Mapping schemas
│       ├── outreach_schemas.py     # Outreach sequence schemas
│       ├── pipeline_schemas.py     # Full pipeline schemas
│       ├── three_stage_schemas.py  # 3-stage pipeline schemas
│       ├── two_stage_schemas.py    # 2-stage pipeline schemas
│       └── crm_schemas.py          # CRM data schemas
├── crm-data/                        # CRM CSV files (user-created, not in git)
├── pdf-data/                        # PDF documents (user-created, not in git)
├── data/                            # Auto-created by the system
│   ├── scraped/                     # Saved scraped data
│   └── generated/                  # Generated content (products, personas, mappings, sequences)
├── tests/                           # Tests
│   ├── fixtures/
│   │   └── mock_crm_data.csv       # Sample CRM data for testing
│   ├── test_crm_service.py         # CRM service tests
│   ├── test_outreach.py            # Outreach generation tests
│   ├── test_product_generator_perplexity.py  # Product generator with Perplexity tests
│   └── conftest.py                 # Shared test fixtures
├── frontend/                        # React frontend application
├── requirements.txt                 # Dependencies
└── .env                             # API keys (create this)
```

---

## Data Storage

### Generated Content Storage

All generated content is automatically saved to `data/generated/` with timestamped filenames:

- **Products**: `{company}_products_{timestamp}.json` (includes source_url for each product)
- **Personas**: `{company}_personas_{timestamp}.json`
- **Mappings**: `{company}_mappings_{timestamp}.json`
- **Outreach Sequences**: `{company}_outreach_{timestamp}.json`
- **4-Stage Pipeline**: `{company}_pipeline_{timestamp}.json` (all components in one file)
- **3-Stage Pipeline**: `{company}_three_stage_{timestamp}.json` (mappings + sequences in one file)
- **2-Stage Pipeline**: `{company}_two_stage_{timestamp}.json` (personas + mappings + sequences)

### Scraped Data Storage

Scraped data is saved to `data/scraped/` as JSON files when `save_to_file: true`.

---

## Cost

- Smart Proxy: ~$0.01/10 searches
- Firecrawl: ~10 credits/10 URLs (500 free/month)
- OpenAI API: Variable based on usage (see https://openai.com/pricing)
- Perplexity API: Variable based on usage (see https://www.perplexity.ai/pricing)