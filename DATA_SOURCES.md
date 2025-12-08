# Data Sources Integration Guide

## Overview

The system now supports **three data sources** for generating personas, mappings, and outreach sequences:

1. **Web Scraped Content** (Required) - Automatically scraped from company websites
2. **CRM Customer Data** (Optional) - CSV files from your CRM system
3. **PDF Documents** (Optional) - Product guides, case studies, company materials

All three sources are **automatically integrated** through the `DataAggregator` service.

---

## 📁 Folder Structure

```
crm-pipeline/
├── crm-data/          # Create this folder and put your CRM CSV files here
│   ├── accounts.csv
│   ├── contacts.csv
│   └── opportunities.csv
│
├── pdf-data/          # Create this folder and put your PDF documents here
│   ├── product_guide.pdf
│   ├── case_studies.pdf
│   └── company_overview.pdf
│
└── data/              # Auto-created by the system
    ├── scraped/       # Auto-generated web scraping results
    └── generated/     # Auto-generated personas, mappings, sequences
```

**Note**: The `crm-data/` and `pdf-data/` folders are NOT included in git (they're in `.gitignore`). 
You need to create them manually when you want to use these features:

```bash
# Create folders when needed
mkdir crm-data  # For CRM CSV files
mkdir pdf-data  # For PDF documents
```

---

## 🚀 How to Use

### Option 1: Use All Data Sources (Recommended)

**Step 1: Create folders and add your data files**
```bash
# Create data folders (if not already exist)
mkdir -p crm-data
mkdir -p pdf-data

# Add CRM data
cp your_crm_export.csv crm-data/

# Add PDF documents
cp your_product_guide.pdf pdf-data/
cp your_case_studies.pdf pdf-data/
```

**Step 2: Generate personas (automatically uses all available data)**
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

### Option 2: Web Content Only

Simply don't put any files in `crm-data/` or `pdf-data/` folders.

The system will:
- ✅ Scrape web content
- ℹ️  Log: "No CRM data available"
- ℹ️  Log: "No PDF data available"
- ✅ Generate personas using web content only

---

## 📊 CRM Data Format

### Supported CRM Systems
- ✅ Salesforce
- ✅ HubSpot
- ✅ Pipedrive
- ✅ Generic CSV formats

### Supported File Types
- **Accounts/Companies** (company information)
- **Contacts** (people, job titles, departments)
- **Opportunities/Deals** (sales pipeline, deal stages, amounts)

### Example Files

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

The system will **automatically**:
- Identify file types
- Detect CRM system (Salesforce/HubSpot/Pipedrive)
- Normalize column names
- Generate statistics (industry distribution, location, job titles, deal stages)
- Create a text summary for LLM consumption

---

## 📄 PDF Documents

### Supported Content
- Product guides
- Case studies
- Company overview documents
- Technical documentation
- Sales materials

### Limits
- **Maximum PDFs**: 5 files (to avoid context overflow)
- **Maximum per PDF**: 5,000 characters (automatically truncated)

### Example
```bash
# Add PDFs
cp product_catalog_2024.pdf pdf-data/
cp customer_success_stories.pdf pdf-data/
cp company_overview.pdf pdf-data/

# Generate personas (PDFs automatically included)
curl -X POST http://localhost:8000/api/v1/llm/persona/generate \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Salesforce", "generate_count": 5}'
```

---

## 🔍 How It Works

### Data Flow

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

### Log Output Example

When you generate personas, you'll see:
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

---

## 📝 Context Structure

The combined context looks like this:

```
================================================================================
WEB SCRAPED CONTENT
================================================================================

OFFICIAL WEBSITE:
[Company website content...]

--- NEWS ---
URL: https://...
[News article content...]

--- CASE_STUDY ---
URL: https://...
[Case study content...]

================================================================================
CRM CUSTOMER DATA
================================================================================

=== CRM CUSTOMER DATA SUMMARY ===
Total Accounts: 150
Total Contacts: 450
Total Opportunities: 280

--- Industry Distribution ---
  Technology: 65
  Finance: 40
  Healthcare: 25
  ...

--- Top Job Titles ---
  VP of Sales: 45
  Director of Marketing: 38
  CTO: 30
  ...

================================================================================
PDF DOCUMENTS
================================================================================

--- PDF: product_catalog_2024.pdf (15 pages) ---
[PDF text content...]

--- PDF: case_studies.pdf (8 pages) ---
[PDF text content...]
```

---

## 🎯 Benefits

### Before (Web Only)
- Limited to publicly available information
- May miss internal company details
- No customer demographic insights

### After (Web + CRM + PDF)
- ✅ **Richer personas** - Based on actual customer data
- ✅ **Better targeting** - Job titles from real contacts
- ✅ **Accurate geography** - Customer location distribution
- ✅ **Precise pain points** - From case studies and sales materials
- ✅ **Product alignment** - From internal product documents

---

## 🔧 Advanced Configuration

### Disable CRM or PDF (Programmatically)

If you need to explicitly disable CRM or PDF loading:

```python
# In your code
context, tokens = await data_aggregator.prepare_context(
    company_name="Salesforce",
    max_chars=15000,
    include_crm=False,   # Disable CRM
    include_pdf=False,   # Disable PDF
)
```

### Custom Folders

```python
context, tokens = await data_aggregator.prepare_context(
    company_name="Salesforce",
    crm_folder="custom-crm-folder",
    pdf_folder="custom-pdf-folder"
)
```

---

## 🐛 Troubleshooting

### CRM data not loading
```bash
# Check if files exist
ls -la crm-data/

# Check file format
head crm-data/accounts.csv

# Check logs
# Look for: "✅ CRM data loaded" or "ℹ️  No CRM data available"
```

### PDF data not loading
```bash
# Check if files exist
ls -la pdf-data/

# Check file format
file pdf-data/*.pdf

# Check logs
# Look for: "✅ PDF data loaded" or "ℹ️  No PDF data available"
```

### Context too large
If you get context overflow errors:
- Reduce `max_chars` parameter (default: 15000)
- Limit number of PDFs (system limits to 5 automatically)
- Use fewer/smaller CRM files

---

## 📚 API Endpoints That Use This

All these endpoints **automatically use all three data sources**:

- `POST /api/v1/llm/persona/generate` - Generate personas
- `POST /api/v1/llm/mappings/generate` - Generate pain-point mappings
- `POST /api/v1/llm/pipeline/generate` - Full 4-stage pipeline
- `POST /api/v1/llm/baseline/generate` - Baseline single-shot
- `POST /api/v1/llm/two-stage/generate` - 2-stage pipeline
- `POST /api/v1/llm/three-stage/generate` - 3-stage pipeline
- `POST /api/v1/outreach/generate` - Outreach sequences

**Note**: Product generation (`/llm/products/generate`) uses Perplexity web search and doesn't need these data sources.

---

## ✅ Summary

**Simple Usage**:
1. Put CRM CSV files in `crm-data/`
2. Put PDF files in `pdf-data/`
3. Call any generation API
4. System automatically uses all available data

**Optional Data**: If folders are empty, system falls back to web content only.

**No API changes needed**: Existing API calls work as before, now with richer context!

