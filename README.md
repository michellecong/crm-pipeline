# CRM Pipeline API

Comprehensive B2B sales intelligence platform that generates buyer personas, pain-point to value-proposition mappings, and multi-touch outreach sequences from company web data.

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

# LLM-powered web search (intelligent search with structured JSON)
curl -X POST http://localhost:8000/api/v1/search/web \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce"
  }'
# Note: Uses OpenAI's LLM to intelligently plan and execute searches,
# returning structured JSON with official website, products, news, and case studies.

# Upload and parse CRM CSV file
curl -X POST http://localhost:8000/api/v1/crm/parse \
  -F "file=@/path/to/your/crm_export.csv"

# Response format:
# {
#   "success": true,
#   "data": {
#     "full_content": "company_name  company_industry  deal_amount...",
#     "summary": {
#       "total_rows": 150,
#       "total_columns": 28,
#       "columns": ["company_name", "company_industry", ...],
#       "preview": [...],
#       "industry_distribution": {"Technology": 45, "Finance": 30, ...},
#       "location_distribution": {"United States": 60, "Canada": 40, ...},
#       "deal_amount_stats": {
#         "mean": 65432.10,
#         "median": 58000.00,
#         "min": 25000.00,
#         "max": 150000.00,
#         "count": 150
#       }
#     }
#   }
# }

# Generate product catalog using web search
curl -X POST http://localhost:8000/api/v1/llm/products/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce"
  }'

# Response format:
# {
#   "products": [
#     {
#       "product_name": "Sales Cloud",
#       "description": "Complete CRM platform for managing sales pipelines...",
#       "source_url": "https://www.salesforce.com/products/sales-cloud"
#     }
#   ]
# }
# Note: Product generation uses Perplexity web search to find official product pages
# and automatically includes source URLs for each product.

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

# Generate pain-point to value-prop mappings (auto-loads products + personas)
curl -X POST http://localhost:8000/api/v1/llm/mappings/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce"
  }'
# Note: Requires personas to be generated first. Products and personas are auto-loaded.

# Generate outreach sequences (requires personas_with_mappings)
curl -X POST http://localhost:8000/api/v1/outreach/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "personas_with_mappings": [...]
  }'
# Creates 4-6 touch sales cadences for each persona

# Run full pipeline (products → personas → mappings → sequences)
curl -X POST http://localhost:8000/api/v1/llm/pipeline/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 5,
    "use_llm_search": true,
    "provider": "perplexity"
  }'
# Response includes generated products, personas, personas_with_mappings, sequences, and artifact file paths.

# Generate baseline (single-shot generation for comparison)
curl -X POST http://localhost:8000/api/v1/llm/baseline/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 5,
    "use_llm_search": true,
    "provider": "google"
  }'
# Generates all 4 outputs (products, personas, mappings, sequences) in ONE LLM call
# Useful for baseline comparison with multi-stage pipeline
```

## Search Options

The system provides multiple search methods:

### **Traditional Search**
- **Google Custom Search** (default): `POST /api/v1/search/company` with `"provider": "google"`
- **Perplexity Search**: `POST /api/v1/search/company` with `"provider": "perplexity"`

### **LLM-Powered Intelligent Search**
- **Endpoint**: `POST /api/v1/search/web`
- **How it works**: Uses OpenAI's LLM with web search capabilities to intelligently plan and execute multi-step searches
- **Output**: Structured JSON with guaranteed official website, products, news, and case studies
- **Best for**: Complex research requiring intelligent query planning and data synthesis

## CRM Data Upload & Analysis

Upload and analyze CRM CSV files to extract customer insights for persona generation.

### **Features**
- Parse CSV files (max 20MB)
- Automatic column detection (industry, location, job titles, deal stages, etc.)
- Statistical analysis for numeric fields (deal amounts, company sizes)
- Distribution analysis for categorical fields
- Handles various CRM export formats (Salesforce, HubSpot, Pipedrive, etc.)

### **Supported Column Types**
The system automatically detects and analyzes:
- **Industry/Sector**: Company industries and verticals
- **Location**: Countries, regions, cities
- **Job Titles/Functions**: Contact roles and positions
- **Departments**: Sales, Marketing, IT, Operations, etc.
- **Deal Stages**: Pipeline stages and statuses
- **Deal Amounts**: Revenue, deal values (with statistics)
- **Company Size**: Employee counts (with statistics)

### **Example Usage**

#### Upload CRM File
```bash
curl -X POST http://localhost:8000/api/v1/crm/parse \
  -F "file=@salesforce_export.csv"
```

#### Example Response
```json
{
  "success": true,
  "data": {
    "full_content": "company_name  company_industry  company_country...",
    "summary": {
      "total_rows": 300,
      "total_columns": 28,
      "columns": [
        "company_name",
        "company_industry",
        "company_country",
        "company_size",
        "contact_function",
        "deal_stage",
        "deal_amount"
      ],
      "preview": [
        {
          "company_name": "Acme Corp",
          "company_industry": "Technology",
          "company_country": "United States",
          "deal_amount": 50000
        }
      ],
      "industry_distribution": {
        "Technology": 120,
        "Finance": 90,
        "Healthcare": 60,
        "Real Estate": 30
      },
      "location_distribution": {
        "United States": 150,
        "Canada": 80,
        "United Kingdom": 70
      },
      "job_title_distribution": {
        "VP of Sales": 45,
        "Director of Marketing": 38,
        "CTO": 30
      },
      "deal_stage_distribution": {
        "Qualified To Buy": 82,
        "Decision Maker Brought-In": 80,
        "Presentation Scheduled": 73,
        "Appointment Scheduled": 65
      },
      "deal_amount_stats": {
        "mean": 65432.10,
        "median": 58000.00,
        "min": 25000.00,
        "max": 150000.00,
        "count": 300
      },
      "company_size_stats": {
        "mean": 487.50,
        "median": 420.00,
        "min": 150.00,
        "max": 920.00,
        "count": 300
      }
    }
  }
}
```

### **File Requirements**
- **Format**: CSV only
- **Max Size**: 20MB
- **Encoding**: UTF-8 (recommended)
- **Headers**: First row should contain column names

### **Common CRM Export Formats**

The system automatically recognizes columns from:

**Salesforce:**
```csv
Account Name,Industry,Employee Count,BillingCountry,Deal Amount,Stage
```

**HubSpot:**
```csv
Company,Company Industry,Number of Employees,Country,Deal Value,Deal Stage
```

**Pipedrive:**
```csv
Organization Name,Industry Sector,Size,Location,Value,Status
```

**Generic Format:**
```csv
company_name,company_industry,company_country,company_size,deal_amount,deal_stage
```

### **Use Cases**
1. **Persona Generation**: Analyze actual customer data to create evidence-based buyer personas
2. **Market Analysis**: Understand geographic distribution and industry concentration
3. **Sales Intelligence**: Identify patterns in deal sizes, stages, and buyer titles
4. **Segmentation**: Group customers by industry, size, or location

## Auto-Loading Features

The system automatically loads previously generated data to streamline the workflow:

### **Persona Generation**
- **Auto-loads products** if available
- Workflow:
  1. Generate products: `POST /api/v1/llm/products/generate`
  2. Generate personas: `POST /api/v1/llm/persona/generate` (products auto-loaded)

### **Mapping Generation**
- **Auto-loads products AND personas** (both required)
- Workflow:
  1. Generate products: `POST /api/v1/llm/products/generate`
  2. Generate personas: `POST /api/v1/llm/persona/generate`
  3. Generate mappings: `POST /api/v1/llm/mappings/generate` (both auto-loaded)

**Logs to watch for:**
```
✅ Auto-loaded 5 products from previous generation
📦 Loaded 5 products from: salesforce_products_2025-10-30.json
👥 Loaded 3 personas from: salesforce_personas_2025-10-30.json
```

## Baseline vs Multi-Stage Pipeline

The system provides two approaches to generate all 4 outputs (products, personas, mappings, sequences):

### **Multi-Stage Pipeline** (`/llm/pipeline/generate`)

**Architecture**: 4 sequential LLM calls with inter-stage data flow
- **Call 1**: Generate products from web content
- **Call 2**: Generate personas using products + web content
- **Call 3**: Generate mappings using personas + products
- **Call 4**: Generate sequences using personas_with_mappings

**Advantages**:
- ✅ Personas receive actual products JSON for context
- ✅ Mappings receive actual personas + products for context
- ✅ Each stage can be optimized independently
- ✅ Better quality through explicit information flow

**Use Case**: Production deployment, best quality output

### **Baseline** (`/llm/baseline/generate`)

**Architecture**: 1 consolidated LLM call with integrated prompt
- **Single Call**: Generate all 4 outputs simultaneously

**Advantages**:
- ✅ Faster execution (1 API call vs 4)
- ✅ Lower latency
- ✅ Simpler architecture

**Use Case**: Evaluation, comparison, testing, quick prototypes

**Comparison**:

| Aspect | Multi-Stage Pipeline | Baseline |
|--------|---------------------|----------|
| **API Calls** | 4 sequential calls | 1 call |
| **Prompts** | 4 separate detailed prompts | 1 consolidated prompt |
| **Information Flow** | Personas receive actual products JSON | Personas reference products in context |
| **Generation Time** | ~4x longer | Faster |
| **Quality** | Higher (explicit data flow) | Baseline |
| **Max Tokens** | 10K per stage | 20K total |

### **When to Use Each**

**Use Pipeline when**:
- Quality is priority
- Need explicit inter-stage information flow
- Production environment
- Resources allow for multiple calls

**Use Baseline when**:
- Testing or evaluating performance
- Speed is important
- Comparing approaches
- Developing prototypes
- Token cost is a concern

**Note**: Both endpoints accept identical input parameters and return the same output schema for fair comparison.

## 2-Stage Baseline Design

The **2-Stage Baseline** (`/llm/two-stage/generate`) is an experimental approach designed for fair architectural comparison with the multi-stage pipeline.

### **Architecture**

**2-Stage Process**:
- **Stage 1**: Generate products (same as pipeline)
- **Stage 2**: Generate personas + mappings + sequences in **ONE consolidated LLM call**

**Key Design Principle**: Complete prompt parity with the 3-stage pipeline
- ✅ **Same prompt content** as `persona_generator.py`, `mapping_generator.py`, and `outreach_generator.py`
- ✅ **Same examples, validation rules, and quality requirements**
- ✅ **Only architectural difference**: 3 outputs generated in 1 LLM call instead of 3 separate calls

This allows comparison of:
1. **Multi-stage with explicit data flow** (Pipeline)
2. **Consolidated generation with full guidance** (2-Stage)

### **Technical Details**

**Prompt Integration**:
- Consolidates all three prompts (personas, mappings, outreach) into a single comprehensive prompt
- Maintains all original instructions, examples, and validation rules
- Organized into three parts: "PART 1: PERSONA GENERATION", "PART 2: MAPPINGS GENERATION", "PART 3: SEQUENCES GENERATION"

**Output Format**:
- Same JSON schema as pipeline: `personas`, `personas_with_mappings`, `sequences`
- All outputs generated in a single response for consistency

### **Usage**

```bash
# Generate using 2-stage baseline
curl -X POST http://localhost:8000/api/v1/llm/two-stage/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 5,
    "use_llm_search": true
  }'
```

**Response Format**:
```json
{
  "personas": [...],
  "personas_with_mappings": [...],
  "sequences": [...],
  "generation_reasoning": "...",
  "data_sources": {...},
  "model": "gpt-5-mini-2025-08-07",
  "usage": {
    "prompt_tokens": 11330,
    "completion_tokens": 8896,
    "total_tokens": 20226
  },
  "generation_time_seconds": 141.45
}
```

### **Comparison with Pipeline**

| Aspect | Multi-Stage Pipeline | 2-Stage Baseline |
|--------|---------------------|------------------|
| **API Calls** | 4 calls | 2 calls |
| **Stage 2 Calls** | 3 separate calls | 1 consolidated call |
| **Prompt Content** | 4 separate prompts | Products + 1 consolidated prompt |
| **Information Flow** | Explicit JSON passing | Context-based (same prompt content) |
| **Generation Time** | ~4x longer | ~2x faster |
| **Quality** | Highest (explicit data flow) | High (full guidance parity) |
| **Consistency** | High (sequential refinement) | Very High (single response) |

**Advantages**:
- ✅ Faster than pipeline (2 calls vs 4)
- ✅ Better consistency (personas, mappings, sequences generated together)
- ✅ Full guidance parity (same prompt content as pipeline)
- ✅ Fair comparison baseline (isolates architectural impact)

**Limitations**:
- ⚠️ No explicit JSON passing between stages (relies on context)
- ⚠️ Larger token usage per call (15K vs 10K per stage)
- ⚠️ Less flexibility for stage-specific optimization

## Outreach Sequences

Generate multi-touch sales outreach sequences for each persona with pain point-value proposition mappings.

### **Features**

- **4-6 touch sequences** per persona
- **Multi-channel strategy**: Email → LinkedIn → Email → Phone → Follow-up
- **Personalized content**: References specific pain points and value propositions
- **Timing optimization**: 2-3 day intervals, 10-21 day total duration
- **Channel-specific guidelines**: Subject lines, content templates, execution hints

### **Touch Types**

- **Email**: Low commitment, high deliverability
- **LinkedIn**: Social proof and credibility building
- **Phone**: High-intent moments
- **Video**: High effort, high impact (used sparingly)

### **Example Usage**

#### Generate Outreach Sequences
```bash
curl -X POST http://localhost:8000/api/v1/outreach/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "personas_with_mappings": [
      {
        "persona_name": "US Enterprise B2B SaaS - Revenue Leaders",
        "target_decision_makers": ["VP Engineering", "Engineering Director"],
        "industry": "SaaS",
        "company_size_range": "200-800 employees",
        "tier": "tier_1",
        "mappings": [
          {
            "pain_point": "Regional sales leaders lack unified pipeline visibility",
            "value_proposition": "Sales Cloud centralizes opportunities and activity"
          }
        ]
      }
    ]
  }'
```

#### Expected Response Format
```json
{
  "sequences": [
    {
      "name": "US Enterprise B2B SaaS - Revenue Leaders Outreach Sequence",
      "persona_name": "US Enterprise B2B SaaS - Revenue Leaders",
      "objective": "Secure discovery meeting with revenue leaders",
      "total_touches": 5,
      "duration_days": 14,
      "touches": [
        {
          "sort_order": 1,
          "touch_type": "email",
          "timing_days": 0,
          "objective": "Introduce pipeline visibility challenge",
          "subject_line": "30% forecast accuracy boost for enterprise teams",
          "content_suggestion": "Hi {first_name}, noticed enterprise SaaS teams...",
          "hints": "Personalize with recent expansion news"
        },
        {
          "sort_order": 2,
          "touch_type": "linkedin",
          "timing_days": 2,
          "objective": "Share case study insight",
          "subject_line": "How Similar Co improved pipeline visibility",
          "content_suggestion": "Noticed your team is scaling operations...",
          "hints": null
        },
        {
          "sort_order": 3,
          "touch_type": "email",
          "timing_days": 5,
          "objective": "Deep dive on value proposition",
          "subject_line": "ROI: $500K saved through automation",
          "content_suggestion": "Following up on pipeline visibility...",
          "hints": "Include specific ROI data"
        },
        {
          "sort_order": 4,
          "touch_type": "phone",
          "timing_days": 9,
          "objective": "Direct meeting request",
          "subject_line": null,
          "content_suggestion": "Call to schedule 15-min discovery call...",
          "hints": "Leave voicemail with clear next steps"
        },
        {
          "sort_order": 5,
          "touch_type": "email",
          "timing_days": 14,
          "objective": "Breakup email with new angle",
          "subject_line": "Closing the loop on pipeline visibility",
          "content_suggestion": "Understand if timing isn't right...",
          "hints": "Keep door open for future"
        }
      ]
    }
  ]
}
```

### **Sequence Strategy by Tier**

**tier_1 (Enterprise)**: 5-6 touches, 14-21 days
- More nurture, build credibility slowly
- 2+ LinkedIn touches (social proof critical)
- Phone touch later (touch 5-6)

**tier_2 (Mid-market)**: 5 touches, 12-14 days
- Balanced approach
- 1-2 LinkedIn touches
- Phone touch at 4-5

**tier_3 (SMB)**: 4 touches, 10 days
- Faster, more direct
- 1 LinkedIn touch
- Phone touch at 4

### **Best Practices**

**Subject Lines (<60 chars):**
- ✅ "30% better forecasts for 500-rep teams"
- ✅ "How [Similar Co] cut CRM admin by 10hrs/week"
- ✅ "Quick question about your Q4 pipeline"
- ❌ "Important business opportunity"
- ❌ "I'd love to connect"

**Content Guidelines:**
- Reference specific pain points from mappings
- Provide value before asking
- Keep language professional but conversational
- Include social proof where relevant
- Make the ask clear but not aggressive

**Timing:**
- Space touches 2-3 days apart
- Avoid same-day follow-ups
- Complete sequence in 10-21 days
- Adjust based on role seniority (execs need more time)

### **Integration with Pipeline**

Outreach sequences are automatically generated in the full pipeline:

```bash
# Run full pipeline including sequences
curl -X POST http://localhost:8000/api/v1/llm/pipeline/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 5
  }'
# Response includes: products, personas, mappings, AND sequences
```

# Evaluate pipeline completeness
curl -X POST http://localhost:8000/api/v1/pipeline/evaluation/completeness \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "products": [...],
      "personas": [...],
      "personas_with_mappings": [...],
      "sequences": [...]
    }
  }'
# Returns completeness report with validation results, scores, and issues for all sections

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
| `/api/v1/crm/parse`      | POST   | Upload and parse CRM CSV file                  |

### LLM Service
| Endpoint                     | Method | Description                    |
| ---------------------------- | ------ | ------------------------------ |
| `/api/v1/llm/generate`      | POST   | Generate text with LLM         |
| `/api/v1/llm/products/generate` | POST | Generate product catalog (uses Perplexity web search) |
| `/api/v1/llm/persona/generate` | POST | Generate buyer personas        |
| `/api/v1/llm/mappings/generate` | POST | Generate pain-point to value-prop mappings |
| `/api/v1/llm/pipeline/generate` | POST   | Run full pipeline (products → personas → mappings → sequences) |
| `/api/v1/llm/baseline/generate` | POST   | Baseline single-shot generation (all 4 outputs in one call) |
| `/api/v1/llm/test`          | GET    | Test LLM connectivity          |
| `/api/v1/llm/config`        | GET    | Get LLM configuration          |
| `/api/v1/llm/config`        | PATCH  | Update LLM configuration       |

### Outreach Sequences
| Endpoint                     | Method | Description                    |
| ---------------------------- | ------ | ------------------------------ |
| `/api/v1/outreach/generate` | POST   | Generate multi-touch outreach sequences |

### Pipeline Evaluation
| Endpoint                              | Method | Description                                         |
| ------------------------------------- | ------ | --------------------------------------------------- |
| `/api/v1/pipeline/evaluation/completeness` | POST   | Evaluate pipeline completeness (products, personas, mappings, sequences) |

## Product Generation

The product generation endpoint uses Perplexity's web search capabilities to find and extract product information directly from the company's official website.

### Features

- **Web Search Integration**: Uses Perplexity Sonar model for real-time web search
- **Source URLs**: Each product includes the official product page URL (`source_url`)
- **Comprehensive Coverage**: Generates 15-25+ products for large companies
- **B2B Sales Focus**: Optimized for products that business decision-makers purchase
- **Universal Compatibility**: Works with any company type (SaaS, hardware, manufacturing, services, etc.)

### How It Works

1. **Web Search**: Perplexity searches the company's official website and product pages
2. **Product Extraction**: LLM extracts all major commercial products from search results
3. **URL Matching**: Each product is matched with its official product page URL
4. **Validation**: Products are validated for completeness and quality

### Example Response

```json
{
  "products": [
    {
      "product_name": "Sales Cloud",
      "description": "Complete CRM platform for managing sales pipelines, forecasting revenue, and automating sales processes. Helps sales teams close deals faster with AI-powered insights, workflow automation, and mobile access.",
      "source_url": "https://www.salesforce.com/products/sales-cloud"
    },
    {
      "product_name": "Service Cloud",
      "description": "Customer service platform that unifies support channels, automates case routing, and provides agents with complete customer context.",
      "source_url": "https://www.salesforce.com/products/service-cloud"
    }
  ],
  "model": "sonar"
}
```

### Requirements

- **PERPLEXITY_API_KEY**: Required for product generation
- Product generation does not use scraped context data (uses web search instead)
- Other generators (personas, mappings, outreach) continue to use OpenAI with scraped context

## Data Storage

### **Generated Content Storage**

All generated content is automatically saved to `data/generated/` with timestamped filenames:

- **Products**: `{company}_products_{timestamp}.json` (includes source_url for each product)
- **Personas**: `{company}_personas_{timestamp}.json`
- **Mappings**: `{company}_mappings_{timestamp}.json`
- **Outreach Sequences**: `{company}_outreach_{timestamp}.json`
- **Baseline**: `{company}_baseline_{timestamp}.json` (all 4 outputs in one file)

### **Scraped Data Storage**

Scraped data is saved to `data/scraped/` as JSON files when `save_to_file: true`.

## Testing

### Test CRM Service
```bash
# Run CRM service tests
pytest tests/test_crm_service.py -v

# Run with coverage
pytest tests/test_crm_service.py --cov=services.crm_service --cov-report=html
```

### Test LLM Service (Mock - No API Key Required)
```bash
python -m pytest tests/test_llm_mock.py -v
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

### Test Baseline Generation
```bash
# Run baseline tests
python -m pytest tests/test_baseline.py -v
```

### Test All Services
```bash
python -m pytest tests/ -v
```

### Test CRM Upload

#### Basic CRM Upload
```bash
# Upload a CRM CSV file
curl -X POST http://localhost:8000/api/v1/crm/parse \
  -F "file=@tests/fixtures/mock_crm_data.csv"
```

#### Test with Different Files
```bash
# Test with Salesforce export
curl -X POST http://localhost:8000/api/v1/crm/parse \
  -F "file=@salesforce_export.csv"

# Test with HubSpot export
curl -X POST http://localhost:8000/api/v1/crm/parse \
  -F "file=@hubspot_contacts.csv"

# Test with Pipedrive export
curl -X POST http://localhost:8000/api/v1/crm/parse \
  -F "file=@pipedrive_deals.csv"
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

### Test Outreach Generation

#### Basic Outreach Generation
```bash
# Generate outreach sequences
curl -X POST http://localhost:8000/api/v1/outreach/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "personas_with_mappings": [
      {
        "persona_name": "US Enterprise B2B SaaS - Revenue Leaders",
        "target_decision_makers": ["VP Engineering"],
        "industry": "SaaS",
        "company_size_range": "200-800 employees",
        "tier": "tier_1",
        "mappings": [
          {
            "pain_point": "Pipeline visibility issues",
            "value_proposition": "Centralized pipeline management"
          }
        ]
      }
    ]
  }'
```

#### Expected Response Format
```json
{
  "sequences": [
    {
      "name": "Revenue Leaders Outreach Sequence",
      "persona_name": "US Enterprise B2B SaaS - Revenue Leaders",
      "objective": "Secure discovery meeting with revenue leaders",
      "total_touches": 5,
      "duration_days": 14,
      "touches": [
        {
          "sort_order": 1,
          "touch_type": "email",
          "timing_days": 0,
          "objective": "Introduce pipeline visibility challenge",
          "subject_line": "30% forecast accuracy boost",
          "content_suggestion": "Hi {first_name}, noticed enterprise teams...",
          "hints": "Personalize with recent news"
        }
      ]
    }
  ]
}
```

### Test Baseline Generation

#### Basic Baseline Generation
```bash
# Generate all outputs in single call (baseline)
curl -X POST http://localhost:8000/api/v1/llm/baseline/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Salesforce",
    "generate_count": 5
  }'
```

#### Expected Response Format
```json
{
  "products": [...],
  "personas": [...],
  "personas_with_mappings": [...],
  "sequences": [...],
  "artifacts": {
    "products_file": null,
    "personas_file": null,
    "mappings_file": null,
    "sequences_file": "data/generated/salesforce_baseline_2025-10-30T12-00-00.json"
  }
}
```

**Note**: All 4 outputs are generated in ONE call and saved to a single file.

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

**CRM Upload Issues**:

- **File too large**: Maximum file size is 20MB. Filter your CRM export to include only recent data or essential columns
- **Invalid format**: Only CSV files are supported. Export from CRM as CSV
- **Empty results**: Check that CSV has proper headers and data rows
- **Column not detected**: Ensure column names contain keywords like "industry", "country", "amount", etc.
- **Special characters**: Use UTF-8 encoding when exporting from your CRM

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
│   │   ├── llm.py                  # LLM, persona, mapping & outreach generation endpoints
│   │   └── crm_routes.py           # CRM upload & parsing endpoints
│   ├── generators/                  # Content generators
│   │   ├── base_generator.py       # Base class for all generators
│   │   ├── product_generator.py    # Product catalog generation (uses Perplexity web search)
│   │   ├── persona_generator.py    # Buyer persona generation
│   │   ├── mapping_generator.py    # Pain-point to value-prop mapping generation
│   │   ├── outreach_generator.py   # Outreach sequence generation
│   │   └── baseline_generator.py   # Baseline single-shot generation
│   ├── services/                    # Business logic
│   │   ├── llm_web_search_service.py  # LLM-powered web search
│   │   ├── search_service.py       # Traditional search (Google/Perplexity)
│   │   ├── llm_service.py          # LLM text generation (supports OpenAI and Perplexity)
│   │   ├── generator_service.py    # Generator orchestration
│   │   └── crm_service.py          # CRM file parsing & analysis
│   └── schemas/                     # Data models
│       ├── search.py               # Search & LLM web search schemas
│       ├── product_schemas.py      # Product catalog schemas (includes source_url)
│       ├── persona_schemas.py      # Persona schemas
│       ├── mapping_schemas.py      # Mapping schemas
│       ├── outreach_schemas.py     # Outreach sequence schemas
│       ├── pipeline_schemas.py     # Full pipeline schemas
│       ├── baseline_schemas.py     # Baseline generation schemas
│       └── crm_schemas.py          # CRM data schemas
├── data/
│   ├── scraped/                     # Saved scraped data
│   └── generated/                   # Generated content (products, personas, mappings, sequences)
├── tests/                           # Tests
│   ├── fixtures/
│   │   └── mock_crm_data.csv       # Sample CRM data for testing
│   ├── test_crm_service.py         # CRM service tests
│   ├── test_llm_mock.py            # LLM mock tests
│   ├── test_outreach.py            # Outreach generation tests
│   ├── test_baseline.py            # Baseline generation tests
│   ├── test_product_generator_perplexity.py  # Product generator with Perplexity tests
│   └── conftest.py                 # Shared test fixtures
├── test_llm_web_search.py          # LLM web search test script
├── requirements.txt                 # Dependencies
└── .env                             # API keys (create this)
```

## Cost

- Smart Proxy: ~$0.01/10 searches
- Firecrawl: ~10 credits/10 URLs (500 free/month)
- OpenAI API: Variable based on usage (see https://openai.com/pricing)