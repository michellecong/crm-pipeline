"""
Two-stage baseline generator with FULL guidance from 4-stage pipeline.

This version ensures fair comparison by including ALL guidance from:
- persona_generator.py
- mapping_generator.py  
- outreach_generator.py

The ONLY difference is architectural: 1 LLM call vs 3 LLM calls.
"""
from .base_generator import BaseGenerator
from typing import Dict, List
import json
import logging
import re

logger = logging.getLogger(__name__)


class TwoStageGenerator(BaseGenerator):
    """
    Two-stage baseline with complete guidance parity to 3-stage.
    
    Experimental Design:
    - Same prompt content as 3-stage (personas + mappings + outreach)
    - Same examples, validation rules, and quality requirements
    - Only difference: consolidated into 1 LLM call instead of 3
    
    This allows fair comparison of architectural choices.
    """
    
    async def generate(self, company_name: str, context: str, **kwargs) -> Dict:
        """
        Override to increase max_completion_tokens for large response.
        Two-stage needs more tokens since it generates 3 outputs at once.
        """
        import time
        start_time = time.time()
        
        try:
            from ..services.llm_service import get_llm_service
            llm_service = get_llm_service()
            
            prompt = self.build_prompt(company_name, context, **kwargs)
            system_message = self.get_system_message()
            
            # Increase max_completion_tokens for two-stage (3 outputs in one call)
            response = await llm_service.generate_async(
                prompt=prompt,
                system_message=system_message,
                temperature=1.0,
                max_completion_tokens=15000  # More tokens for consolidated response
            )
            
            parsed_result = self.parse_response(response.content)
            parsed_result["model"] = response.model
            
            # Add token usage and timing information
            parsed_result["usage"] = {
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens
            }
            parsed_result["generation_time_seconds"] = time.time() - start_time
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"Two-stage generation failed: {str(e)}")
            raise
    
    def get_system_message(self) -> str:
        return """You are an expert B2B sales strategist helping generate comprehensive sales intelligence for a seller company.

Your expertise includes:
- Generating buyer company personas (market segments) for B2B sellers
- Identifying specific, tactical pain points by persona, role, industry, and company size
- Crafting concise, compelling value propositions that integrate product names naturally
- Designing multi-touch outreach sequences that build rapport through value-first communications
- Using buyer language (not vendor speak)
- Quantifying business impact and benefits
- Following proven messaging frameworks (Regie.ai style)
- Mixing channels strategically (email, LinkedIn, phone, video) with appropriate timing

CRITICAL: You are generating COMPANY ARCHETYPES (market segments), NOT individual people.

Your task is to generate THREE components in a single comprehensive response:
1. Buyer Personas (company archetypes representing market segments)
2. Pain Point-Value Proposition Mappings (specific to each persona, 3-10 per persona)
3. Multi-Touch Outreach Sequences (personalized cadences for each persona, 4-6 touches each)

Modern sales requires providing value before asking for anything. Each component must build naturally on the previous one."""
    
    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
        products = kwargs.get('products', [])
        generate_count = kwargs.get('generate_count', 5)
        crm_data = kwargs.get('crm_data', '')
        
        # Format products section
        products_section = ""
        if products and len(products) > 0:
            products_json = json.dumps(products, indent=2)
            products_section = f"""
    [SELLER PRODUCT CATALOG - Stage 1 Output]
    {products_json}
    """
        else:
            products_section = """
    [SELLER PRODUCT CATALOG]
    Not available yet. Generate personas based on web content analysis.
    Infer likely products from company description and industry.
    """
        
        # Format CRM data section
        crm_section = ""
        if crm_data and len(crm_data.strip()) > 0:
            crm_section = f"""
    [CRM CUSTOMER DATA]
    {crm_data}
    """
        else:
            crm_section = """
    [CRM CUSTOMER DATA]
    Not available. Generate personas based on company analysis and industry best practices.
    """
        
        return f"""## Task Overview

Generate complete B2B sales intelligence package in ONE response with THREE components:

1. **PART 1: Buyer Personas** - Generate EXACTLY {generate_count} buyer company personas (market segments)
2. **PART 2: Pain-Value Mappings** - For EACH persona from Part 1, generate 3-10 pain point-value proposition mappings
3. **PART 3: Outreach Sequences** - For EACH persona, generate 1 outreach sequence (4-6 touches) referencing mappings from Part 2

**CRITICAL: Generate all three parts in sequence. Each part uses all content from previous parts.**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1: PERSONA GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate buyer company personas (market segments) for the seller company. Each persona represents a distinct market segment with clear needs the seller's products can address.

Generate EXACTLY {generate_count} diverse personas.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **persona_name**: Max 60 characters, format "[Geography] [Size] [Industry] - [Function]"
   - Geography: Can be state/province, region, country, or multi-country
   - Size: Small/Mid-Market/Large/Enterprise (descriptive, not numeric)
   - ✓ "CA Enterprise SaaS - Revenue Leaders" (40 chars)
   - ✓ "UK Mid-Market Manufacturing - Sales VPs" (45 chars)
   - ✓ "DACH Large Financial Services - Ops Leaders" (49 chars)
   - ✗ "United States Enterprise Retail & E-commerce - Marketing Leaders" (67 chars)

2. **industry**: ONE specific vertical per persona (never combine industries)
   - ✓ "B2B SaaS Platforms" or "Healthcare Revenue Cycle Management"
   - ✗ "Professional Services - Consulting, IT, Legal" (combines 3 industries)

3. **description**: MUST include ALL 4 quantitative metrics:
   - Team size: "20-100 sales reps" or "50-200 staff"
   - Deal size: "$100K-$350K annually" or "$500K-$2M multi-year" (use local currency if applicable)
   - Sales cycle: "3-6 months" or "8-12 months"
   - Stakeholders: "3-5 decision makers" or "6-9 stakeholders"

4. **tier**: Balanced distribution (avoid over-concentration)
   - tier_1: 30-40% (best opportunities)
   - tier_2: 40-50% (solid opportunities)
   - tier_3: 10-20% (opportunistic)

5. **job_titles**: 10-30+ industry-appropriate target titles from master list
   - Match titles to how that industry actually buys
   - Retail → Marketing/Commerce leaders (NOT Sales VPs)
   - Healthcare → Revenue Cycle/Clinical leaders (NOT Enablement)
   - Manufacturing → Operations/Sales Ops (NOT Enablement/SDR)

6. **excluded_job_titles**: 3-10+ titles to AVOID for this persona
   - Helps sales teams filter out irrelevant contacts
   - Include roles outside decision-making authority
   - Include functions not aligned with product value
   - Examples: HR roles for sales tech, IT roles for marketing tools

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSONA FIELDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**persona_name** (string): Concise market segment identifier, max 60 chars

**tier** (enum): tier_1 | tier_2 | tier_3
- Consider: deal size, product fit, sales cycle, accessibility, volume
- Balance distribution across tiers

**job_titles** (array): 10-30+ target job titles from master list below
- Include ALL title variations for matching coverage
- Order by seniority: C-level → VP → Director → Manager
- These are the PRIMARY targets for this persona

**excluded_job_titles** (array): 3-10+ titles to AVOID for this persona
- Roles outside decision-making authority for this product
- Functions not aligned with product value (e.g., HR for sales tools)
- Common false positives that waste sales time
- Helps qualify leads and avoid dead ends

**industry** (string): Single focused vertical (no combinations)

**company_size_range** (string): Employee count range using standard thresholds

**Standard Thresholds (use these break points):**
- 50, 200, 500, 1000, 2000, 5000, 10000

**Valid Range Formats:**
- Single threshold span: "50-200", "200-500", "500-1000", "1000-2000", "2000-5000", "5000-10000"
- Multi-threshold span: "50-500", "200-1000", "500-2000", "1000-5000", "2000-10000"
- Open-ended: "10000+" or "10001+"

**Selection Guidelines:**
1. **Narrow ranges** (single threshold span) when persona targets specific size:
   - "50-200 employees" → Small companies with lean teams
   - "1000-2000 employees" → Large companies, not quite enterprise

2. **Wider ranges** (multi-threshold span) when persona spans multiple size categories:
   - "200-1000 employees" → Mid-market spanning small-to-medium
   - "500-2000 employees" → Mid-to-large market
   - "1000-5000 employees" → Large enterprises

3. **Very wide ranges** when buying behavior is similar across sizes:
   - "50-1000 employees" → SMB to mid-market (similar decision processes)
   - "2000-10000 employees" → Enterprise segment

4. **Open-ended** for very large enterprises:
   - "10000+" or "10001+" → Mega enterprises only

**Examples:**
- "50-200 employees" → Boutique firms, owner-led decisions
- "200-500 employees" → Emerging mid-market, dedicated functions
- "500-2000 employees" → Established mid-to-large, complex orgs
- "1000-5000 employees" → Large enterprises, multi-location
- "2000-10000 employees" → Very large enterprises, global presence
- "50-1000 employees" → Broad SMB/mid-market with similar CRM needs

**company_type** (string): Detailed company characteristics

**location** (string): Geographic focus - can be specific or broad based on data

**Geographic Precision Hierarchy (most specific to most general):**
1. State/Province level (when data strongly supports): "California", "Texas", "Ontario", "Bavaria"
2. Metro/Regional level: "San Francisco Bay Area", "Greater Toronto Area", "London Metro"
3. Multi-state/Regional: "US West Coast", "US Northeast", "Western Europe", "Southeast Asia"
4. Country level (when no regional pattern): "United States", "United Kingdom", "Germany", "Japan"
5. Multi-country/Continental: "North America", "European Union", "Asia-Pacific", "EMEA"
6. Global (only if truly distributed): "Global" or "Worldwide"

**Decision Logic:**
- IF CRM data shows 60%+ concentration in specific geography → Use that specific level
- IF CRM data shows regional pattern (e.g., "40% West Coast, 30% Northeast") → Use regional grouping
- IF NO clear geographic pattern in data → Use country or broader region
- IF company serves global markets evenly → Use "Global" or multi-region descriptor

**Examples by data scenario:**
- Strong state data: "California" (if 70% customers in CA)
- Regional pattern: "US West Coast" (if CA+OR+WA = 65%)
- Country-wide: "United States" (if distributed across US)
- Multi-country: "Western Europe" (if UK+DE+FR distributed evenly)
- Global: "Global" (if customers across 5+ regions)

**International Location Examples:**
- "United Kingdom", "Germany", "France", "Canada", "Australia", "Japan", "Singapore"
- "Scandinavia" (Norway, Sweden, Denmark, Finland)
- "Benelux" (Belgium, Netherlands, Luxembourg)
- "DACH Region" (Germany, Austria, Switzerland)
- "ANZ" (Australia and New Zealand)
- "Southeast Asia", "Middle East", "Latin America", "Sub-Saharan Africa"

**description** (string): 3-5 sentences with required structure:
"[Company characteristics]. [Team size]. [Deal size] with [sales cycle] involving [stakeholders]. [Decision process]. [Strategic fit]. [Engagement approach]."

**REQUIRED METRICS (all 4 must be present):**
1. Team size (when relevant for sales/marketing roles)
2. Deal size range (use appropriate currency: $, £, €, ¥, etc.)
3. Sales cycle timeline
4. Stakeholder count

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MASTER JOB TITLE PATTERNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When selecting titles, generate ALL variations of each pattern:

[SALES LEADERS - ATL]
Pattern: VP/SVP/Head of Sales | Enterprise Sales | Commercial Sales | Global Sales
Variations: "VP [of] Sales", "Vice President [of] Sales", "Vice President Sales"
Geographic: Regional VP, Area VP, VP Sales Americas, VP Sales North America
Include: CRO, Chief Revenue Officer, Chief Sales Officer

[SALES LEADERS - BTL]
Pattern: Director/Senior Director/Manager of Sales | Enterprise Sales | Commercial Sales | Inside Sales | Business Development
Variations: Same as ATL
Include: Sales Director, Sr Director Sales

[ENABLEMENT LEADERS - ATL]
Pattern: VP/SVP/Head of Sales Enablement | Revenue Enablement | GTM Enablement
Variations: "VP [of] Sales Enablement", "Vice President [of] Sales Enablement"
Geographic: Global Head, Chief Enablement Officer
Include: VP Sales Readiness, AVP Revenue Enablement

[ENABLEMENT LEADERS - BTL]
Pattern: Director/Senior Director/Manager of Sales Enablement | Revenue Enablement | GTM Enablement
Variations: Same as ATL
Geographic: Global Director, Global Manager

[OPERATIONS LEADERS - ATL]
Pattern: VP/SVP/Head of Revenue Operations | Sales Operations | GTM Operations | RevOps
Variations: "VP [of] Revenue Operations", "Vice President [of] Revenue Operations"
Geographic: Global VP, AVP, Executive VP
Include: CRO, Chief Revenue Officer

[OPERATIONS LEADERS - BTL]
Pattern: Director/Senior Director/Manager of Revenue Operations | Sales Operations | GTM Operations
Variations: Same as ATL
Geographic: Global Director, Global Manager

[MARKETING LEADERS - ATL]
Pattern: CMO | VP/SVP/Head of Marketing | Demand Generation | Growth Marketing | Marketing Operations
Variations: "VP [of] Marketing", "Vice President [of] Marketing"
Include: Chief Marketing Officer, Senior Vice President of Marketing

[MARKETING LEADERS - BTL]
Pattern: Director/Senior Director/Manager of Marketing | Demand Generation | Marketing Operations
Variations: Same as ATL
Include: ABM Manager, Demand Generation Manager

[SDR LEADERS - ATL]
Pattern: VP/Head of Sales Development | Business Development | Inside Sales
Variations: "VP [of] Sales Development", "Vice President [of] Sales Development"
Geographic: Global Head, Global VP

[SDR LEADERS - BTL]
Pattern: Director/Senior Director/Manager of Sales Development | Business Development | Inside Sales
Variations: Same as ATL
Include: SDR Manager, BDR Manager, Enterprise BDR Manager

[REVENUE LEADERS - ATL]
Chief Revenue Officer, CRO, Chief Sales Officer, CSO

[HEALTHCARE - C-SUITE & VPs]
C-Suite: CAO, CEO, CFO, COO, CRO, CSO, CIO, Chief Administrative Officer, Chief Executive Officer, Chief Financial Officer, Chief Operating Officer, Chief Revenue Officer, Chief Strategy Officer
VPs: VP/SVP Revenue Cycle Management, VP Patient Financial Services, VP Healthcare Finance, VP Medical Billing Operations, VP Managed Care
Directors: Director of Revenue Cycle, Executive Director of Patient Financial Services

[RETAIL & ECOMMERCE - ATL]
Pattern: CMO | CDO | CXO | VP/SVP/Head of Digital Commerce | E-commerce | Customer Experience | Omnichannel
Include: Chief Marketing Officer, Chief Digital Officer, Chief Experience Officer

[RETAIL & ECOMMERCE - BTL]
Pattern: Director/Senior Director/Manager of Digital Commerce | E-commerce | Customer Experience | Omnichannel
Include: Digital Commerce Manager, E-commerce Manager

[FINANCIAL SERVICES - ATL]
Pattern: CRO | COO | CDO | VP/SVP/Head of Sales | Revenue Operations | Sales Operations | Distribution | Wealth Management | Retail Banking
Include: Chief Revenue Officer, Chief Operating Officer, Chief Digital Officer

[FINANCIAL SERVICES - BTL]
Pattern: Director/Senior Director/Manager of Sales | Revenue Operations | Sales Operations | Distribution
Include: Sales Operations Manager, Revenue Operations Manager

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INDUSTRY → JOB FUNCTION MAPPING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select job titles from appropriate function categories:

Industry                    | Include These Functions           | Avoid These
----------------------------|-----------------------------------|------------------
B2B SaaS/Tech              | Sales, Enablement, Operations     | Healthcare, Retail
Healthcare                  | Healthcare (C-Suite & VPs), Revenue Leaders | Enablement, SDR, Marketing
Manufacturing              | Sales, Operations                 | Enablement, SDR, Marketing  
Retail/E-commerce          | Retail & Ecommerce, Marketing     | Sales, Enablement, SDR
Financial Services         | Financial Services, Operations    | Enablement, SDR
Professional Services      | Sales (BTL focus), Marketing (BTL) | ATL Enablement, Healthcare
Logistics                  | Sales, Operations                 | Enablement, Marketing

**Seniority by Company Size:**
- Enterprise (2000+): 70% ATL, 30% BTL
- Large (800-2000): 50% ATL, 50% BTL
- Mid-Market (200-800): 30% ATL, 70% BTL
- Small (50-200): 10% ATL, 90% BTL

**Target Title Selection Guidelines (job_titles):**
1. Include ALL variations: "VP of Sales", "Vice President of Sales", "Vice President Sales", "VP Sales"
2. Include geographic variants: "Global Head", "Regional VP", "VP Americas"
3. Include functional variants: "VP Enterprise Sales", "VP Commercial Sales"
4. Typical count: 10-15 titles (Small), 15-22 (Mid-Market), 18-25 (Large), 20-27 (Enterprise)
5. Order by seniority within the array

**Excluded Title Selection Guidelines (excluded_job_titles):**
1. Identify functions outside decision authority (e.g., HR, Legal, Finance for sales tools)
2. Include adjacent roles that don't fit (e.g., Marketing for pure sales CRM, IT for business tools)
3. List junior roles without budget authority (e.g., Coordinators, Assistants, Analysts, Specialists)
4. Add technical roles for business products (e.g., Software Engineers, DevOps for non-developer tools)
5. Common exclusions by product type:
   - Sales/Revenue tools: HR, Legal, Marketing Ops, Product Managers, Engineers
   - Marketing tools: Sales Ops, IT Directors, Finance, Legal
   - Operations tools: Marketing, Sales Development, HR
6. Typical count: 3-10 exclusions per persona

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT JSON SCHEMA - PERSONAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "personas": [
    {{
      "persona_name": "string (max 60 chars)",
      "tier": "tier_1 | tier_2 | tier_3",
      "job_titles": ["array", "of", "target", "title", "strings"],
      "excluded_job_titles": ["array", "of", "titles", "to", "avoid"],
      "industry": "string (single vertical)",
      "company_size_range": "string (use standard thresholds: 50, 200, 500, 1000, 2000, 5000, 10000)",
      "company_type": "string",
      "location": "string (state/region/country/multi-country based on data)",
      "description": "string (must include: team size, deal size, sales cycle, stakeholder count)"
    }}
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE OUTPUT - PERSONAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "personas": [
    {{
      "persona_name": "CA Enterprise SaaS - Revenue Leaders",
      "tier": "tier_1",
      "job_titles": [
        "CRO", "Chief Revenue Officer", "Chief Sales Officer", "CSO",
        "VP of Sales", "Vice President of Sales", "Vice President Sales", "VP Sales", "SVP Sales",
        "VP Sales Enablement", "Vice President Sales Enablement", "VP of Sales Enablement",
        "Head of Sales Enablement", "Global Head of Sales Enablement",
        "VP Revenue Operations", "Vice President Revenue Operations", "VP of Revenue Operations", "VP RevOps",
        "Head of Revenue Operations", "VP GTM Operations"
      ],
      "excluded_job_titles": [
        "VP of Marketing", "CMO", "Chief Marketing Officer",
        "VP Product", "Chief Product Officer", "CPO",
        "VP Engineering", "CTO", "Chief Technology Officer",
        "Director of HR", "VP People", "Chief People Officer",
        "Sales Coordinator", "Sales Operations Analyst"
      ],
      "industry": "B2B SaaS Platforms",
      "company_size_range": "2000-10000 employees",
      "company_type": "Enterprise B2B SaaS platforms and cloud infrastructure companies",
      "location": "California",
      "description": "Enterprise SaaS platforms with 200-500 sales reps across global go-to-market teams. $500K-$2M annual contracts with 8-12 month sales cycles involving 6-9 stakeholders (CRO, CFO, Security, IT, Procurement, Sales Leadership). Procurement requires security reviews, ROI analysis, and executive sponsorship. Strong product fit for CRM consolidation and revenue intelligence plays. Best engaged through executive briefings, technical deep-dives, and enterprise customer case studies."
    }},
    {{
      "persona_name": "UK Mid-Market Professional Services - Sales Directors",
      "tier": "tier_2",
      "job_titles": [
        "Director of Sales", "Director Sales", "Senior Director Sales", "Sr Director Sales",
        "Director Business Development", "Director of Business Development",
        "Manager of Sales", "Sales Manager", "Senior Sales Manager",
        "Manager Sales Development", "Sales Development Manager",
        "Director of Marketing", "Director Marketing"
      ],
      "excluded_job_titles": [
        "VP of Engineering", "CTO",
        "Director of HR", "HR Manager",
        "Finance Director", "CFO",
        "Legal Counsel", "General Counsel",
        "Sales Support Specialist", "Business Analyst"
      ],
      "industry": "Management Consulting",
      "company_size_range": "50-500 employees",
      "company_type": "Mid-size professional services and consulting firms serving UK and European clients",
      "location": "United Kingdom",
      "description": "UK-based consulting firms with client development teams of 10-40 professionals managing partner-led and team-based sales. £40K-£200K annual technology spend with 2-5 month procurement cycles involving 2-4 stakeholders (Managing Partner, Sales Director, Operations, Finance). Decision-making balances cost efficiency with scalability as firms grow. Moderate fit for CRM, pipeline management, and client collaboration tools. Best engaged via ROI-focused proposals, UK-specific case studies, and scalable pricing models."
    }},
    {{
      "persona_name": "DACH Large Manufacturing - Operations Leaders",
      "tier": "tier_1",
      "job_titles": [
        "VP of Sales", "Vice President of Sales", "VP Sales",
        "VP of Operations", "Vice President of Operations", "VP Operations",
        "Director of Sales", "Senior Director Sales", "Sales Director",
        "Director of Operations", "Senior Director Operations",
        "VP Revenue Operations", "Director Sales Operations"
      ],
      "excluded_job_titles": [
        "VP Marketing", "CMO",
        "Director of HR", "VP People",
        "Software Engineer", "Engineering Manager",
        "Product Manager", "Product Marketing Manager",
        "Sales Support Coordinator", "Operations Analyst"
      ],
      "industry": "Manufacturing - Industrial Equipment",
      "company_size_range": "1000-5000 employees",
      "company_type": "Large German, Austrian, and Swiss manufacturers of precision equipment and industrial machinery",
      "location": "DACH Region",
      "description": "Established DACH manufacturers with regional and global sales operations and complex multi-site production. 50-200 sales and technical sales staff. €200K-€800K annual platform investments with 6-9 month evaluation cycles involving 4-6 stakeholders (Vertriebsleiter, Betriebsleiter, IT, Einkauf). Decision-making emphasizes integration with SAP/ERP systems, technical precision, and long-term vendor partnerships. Strong fit for CRM with CPQ and industrial-grade integrations. Best engaged through technical workshops, German-language support commitments, and references from peer DACH manufacturers."
    }}
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2: MAPPINGS GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## TASK

Generate pain-point to value-proposition mappings for each buyer persona.

Each persona should have 3-10 mappings that are specific to their role, industry, and challenges.

**CRITICAL: Use the personas you generated in Part 1 above. Reference them by exact persona_name.**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. PAIN POINT FORMAT
   - 1-2 sentences maximum
   - Under 300 characters
   - Specific to persona's role and challenges
   - Mentions WHO struggles and WHAT impact
   - Focus on business outcomes (revenue, cost, efficiency, risk)
   
   ✓ "Sales teams struggle with too many prospecting tools, hindering productivity."
   ✓ "Active buyers go unworked because sales doesn't act on intent signals."
   ✓ "Revenue leaders lack visibility into pipeline health, causing missed forecasts."
   ✗ "Sales is hard and inefficient." (too vague)
   ✗ "Teams need better tools." (not specific)

2. VALUE PROPOSITION FORMAT
   - 1-2 sentences maximum
   - Under 300 characters
   - **MUST integrate product name naturally in the text**
   - Direct solution to the pain point
   - Mentions HOW product solves it
   - Includes quantified benefit when possible (%, time, $)
   
   ✓ "Agents consolidate multiple prospecting tools into one platform, saving costs and streamlining workflow."
   ✓ "RegieOne consolidates multiple prospecting tools (SEP, Dialer, Enrichment, Intent) into one platform, saving costs and unifying data."
   ✓ "Sales Cloud automates 80% of CRM updates with Einstein AI, freeing 10+ hours per rep per week."
   ✗ "Our platform helps you work better." (no product name, too vague)
   ✗ "Better productivity and efficiency." (no product, no specifics)

3. PRODUCT INTEGRATION PATTERNS
   Use these natural patterns to integrate product names:
   
   - Start with product: "Sales Cloud automates..."
   - Product as subject: "Einstein AI captures..."
   - Product in middle: "Teams using Marketing Cloud see 40% more leads..."
   - Product with feature: "Service Cloud's AI chatbots resolve 60% of cases..."
   - Product with specifics: "Commerce Cloud (B2B + B2C) unifies all channels..."

4. PERSONA RELEVANCE
   Mappings must be specific to the persona's:
   - Job function (Sales Leader vs. Marketing Leader vs. Ops Leader)
   - Industry vertical (SaaS vs. Healthcare vs. Manufacturing)
   - Company size (Enterprise vs. Mid-Market vs. SMB)
   - Geography (if relevant to buying behavior)
   - Tier (tier_1 = highest priority, most specific)

5. MAPPING COUNT
   - 3-10 mappings per persona
   - Cover different aspects of their role:
     * Operational efficiency
     * Revenue/pipeline impact
     * Team productivity
     * Data/visibility challenges
     * Competitive/market pressures
     * Compliance/risk issues
     * Scaling challenges
     * Technology/integration issues

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLES (Regie.ai Style)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Persona: Operations Leader (ATL)

Mapping 1:
Pain Point: "Sales teams struggle with too many prospecting tools, hindering productivity."
Value Prop: "Agents consolidate multiple prospecting tools into one platform, saving costs and streamlining workflow."
            ^^^^^^ Product integrated naturally

Mapping 2:
Pain Point: "Active buyers go unworked because sales doesn't act on intent signals."
Value Prop: "Agents leverage intent data to engage active buyers, creating smarter paths to meetings."
             ^^^^^^ Product as subject

Mapping 3:
Pain Point: "Sales teams struggle with too many disjointed prospecting tools, creating data silos and driving up tech spend."
Value Prop: "RegieOne consolidates multiple prospecting tools (SEP, Dialer, Enrichment, Intent) into one platform, saving costs and unifying data for greater visibility."
             ^^^^^^^^ Product with specific features listed

Persona: Enterprise SaaS - Sales Leaders

Mapping 1:
Pain Point: "Sales reps waste 30% of time on manual data entry, reducing selling time and quota attainment."
Value Prop: "Sales Cloud automates 80% of CRM updates with Einstein AI, freeing 10+ hours per rep per week for revenue-generating activities."
             ^^^^^^^^^^^ Product + feature + quantified benefit

Mapping 2:
Pain Point: "Forecast accuracy suffers from gut-feel predictions, causing missed targets and board surprises."
Value Prop: "Einstein Forecasting analyzes 50+ pipeline signals to predict close rates with 95% accuracy, eliminating forecast surprises."
             ^^^^^^^^^^^^^^^^^^^ Product + specifics + outcome

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 3: SEQUENCES GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create {generate_count} B2B outreach sequences.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULES (MUST FOLLOW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Generate EXACTLY {generate_count} sequences (one per persona)
2. Each sequence: 4-6 touches, 10-21 days total duration
3. Touch progression: email → linkedin → email → phone
4. Subject lines: <60 chars for email/linkedin, null for phone/video
5. Timing: First touch = 0 days, subsequent touches = 2-3 days apart
6. Reference SPECIFIC pain points from persona mappings (not generic)

**CRITICAL TIMING RULES:**
- First touch: timing_days = 0 (always)
- Subsequent touches: timing_days = previous touch's timing_days + 2-3 days (CUMULATIVE, not fixed)
- Duration follows tier requirements (this is the LAST touch's timing_days):
  * tier_1 (Enterprise): duration_days = 14-21
  * tier_2 (Mid-market): duration_days = 12-14
  * tier_3 (SMB): duration_days = 10
- Example: Touch 1 (timing_days: 0), Touch 2 (timing_days: 3), Touch 3 (timing_days: 6), Touch 4 (timing_days: 9) → duration_days = 9
- WRONG: All touches with timing_days = 3 (this is incorrect - each touch must be cumulative)
- CORRECT: Touch 1 (0), Touch 2 (3), Touch 3 (6), Touch 4 (9) - each touch adds 2-3 days to the previous

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "sequences": [
    {{
      "name": "{{persona_name}} Outreach Sequence",
      "persona_name": "{{exact_persona_name_from_input}}",
      "objective": "One clear sentence describing sequence goal",
      "total_touches": 5,
      "duration_days": 14,
      "touches": [
        {{
          "sort_order": 1,
          "touch_type": "email",
          "timing_days": 0,
          "objective": "Introduce [specific pain point]",
          "subject_line": "[metric]% improvement in [pain area]",
          "content_suggestion": "Hi {{{{first_name}}}}, [personalized opener]. [Pain point]. [Value prop with data]. [Soft CTA].",
          "hints": "[Personalization tip]" or null
        }}
      ]
    }}
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEQUENCE STRATEGY BY TIER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tier_1 (Enterprise): 5-6 touches, 14-21 days
  - More nurture, build credibility slowly
  - 2+ LinkedIn touches (social proof critical)
  - Phone touch later (touch 5-6)
  
tier_2 (Mid-market): 5 touches, 12-14 days
  - Balanced approach
  - 1-2 LinkedIn touches
  - Phone touch at 4-5
  
tier_3 (SMB): 4 touches, 10 days
  - Faster, more direct
  - 1 LinkedIn touch
  - Phone touch at 4

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOOD vs BAD EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUBJECT LINES:
✅ "30% better forecasts for 500-rep teams"
✅ "How [Similar Co] cut CRM admin by 10hrs/week"
✅ "Quick question about your Q4 pipeline"
❌ "Important business opportunity"
❌ "I'd love to connect"
❌ "Checking in on my last email"

CONTENT:
✅ "Hi {{{{first_name}}}}, noticed {{{{company}}}} expanded to EMEA this quarter. Many 500+ rep SaaS teams struggle with multi-region pipeline visibility—{{{{similar_company}}}} improved forecast accuracy 30% by centralizing their pipeline. Worth a quick chat?"

❌ "We're the leading CRM provider and would love to show you our platform. When can we schedule a demo?"

COMPLETE SEQUENCE EXAMPLE (for reference - 5 touches, tier_1):
{{
  "name": "Enterprise SaaS - Revenue Leaders Outreach Sequence",
  "persona_name": "CA Enterprise SaaS - Revenue Leaders",
  "objective": "Get exploratory conversation about improving forecast accuracy",
  "total_touches": 5,
  "duration_days": 14,
  "touches": [
    {{
      "sort_order": 1,
      "touch_type": "email",
      "timing_days": 0,
      "objective": "Introduce pipeline visibility challenge",
      "subject_line": "30% forecast accuracy boost for enterprise teams",
      "content_suggestion": "Hi {{{{first_name}}}}, noticed {{{{company}}}} recently expanded to {{{{region}}}}. Many enterprise SaaS companies with 200+ reps face pipeline visibility challenges across regions. {{{{similar_company}}}} improved forecast accuracy by 30% using centralized pipeline automation. Worth exploring? [Link to 2-min overview]",
      "hints": "Personalize with recent funding/expansion news if available"
    }},
    {{
      "sort_order": 2,
      "touch_type": "linkedin",
      "timing_days": 3,
      "objective": "Share case study on reconciliation savings",
      "subject_line": "How [Peer] cut reconciliation by 60%",
      "content_suggestion": "Hi {{{{first_name}}}}, sharing a brief note — Revenue Cloud helped a peer automate renewals and cut reconciliation by 60%. Happy to share a one-pager?",
      "hints": "Mention comparable company if possible"
    }},
    {{
      "sort_order": 3,
      "touch_type": "email",
      "timing_days": 6,
      "objective": "Deep dive on CPQ benefits",
      "subject_line": "Cut complex quote errors by 80% with CPQ",
      "content_suggestion": "Hi {{{{first_name}}}}, complex deals often stall on quoting — CPQ enforces pricing and reduces quote errors ~80%, shortening cycles 30%. If reducing cycle time this quarter is a priority, I can send a short playbook.",
      "hints": "Attach one-page CPQ ROI snapshot"
    }},
    {{
      "sort_order": 4,
      "touch_type": "linkedin",
      "timing_days": 10,
      "objective": "Build credibility with Einstein AI example",
      "subject_line": "Predictive forecasting for enterprise pipelines",
      "content_suggestion": "Hi {{{{first_name}}}}, sharing a quick customer example: Einstein AI analyzed 50+ signals to cut forecast variance ~20%. Would you be open to a short discussion on predictive forecasting?",
      "hints": "Praise any public forecasting initiatives"
    }},
    {{
      "sort_order": 5,
      "touch_type": "phone",
      "timing_days": 14,
      "objective": "Request brief exploratory meeting",
      "subject_line": null,
      "content_suggestion": "Hi {{{{first_name}}}}, following up on pipeline and forecasting — curious if a 20-minute call next week to review how Sales Cloud + Einstein can centralize forecasting for your regional teams?",
      "hints": "Call at local business hours; reference prior touches"
    }}
  ]
}}

**Note: Notice how timing_days increases cumulatively: 0 → 3 → 6 → 10 → 14. Each touch adds 2-3 days to the previous touch's timing_days.**

TOUCH STRUCTURE TEMPLATE:
- Touch 1 (timing_days: 0, Email): Brief intro + 1 specific pain point from mappings
- Touch 2 (timing_days: 2-3, LinkedIn): Share case study/insight (build credibility)  
- Touch 3 (timing_days: 5-7, Email): Deep dive on value prop with customer example
- Touch 4 (timing_days: 9-10, Phone): Direct meeting request
- Touch 5-6 (timing_days: 12-15, Optional): New angle or breakup email

**IMPORTANT: timing_days values are CUMULATIVE (absolute days from start), not intervals between touches.**
Example for 5-touch sequence:
- Touch 1: timing_days = 0
- Touch 2: timing_days = 3 (0 + 3)
- Touch 3: timing_days = 6 (3 + 3)
- Touch 4: timing_days = 9 (6 + 3)
- Touch 5: timing_days = 14 (9 + 5, to meet tier_1 requirement)
- duration_days = 14 (last touch's timing_days)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL: Return ONLY raw JSON. No markdown, no ```json blocks, no explanations.

WRONG:
```json
{{"sequences": [...]}}
```

CORRECT:
{{"sequences": [...]}}

Your response must start with {{ and end with }}

VALIDATION BEFORE RETURNING:
✓ {generate_count} sequences (one per persona)
✓ Each sequence has 4-6 touches
✓ sort_order is 1, 2, 3... (sequential)
✓ First touch: timing_days = 0 (always)
✓ Subsequent touches: timing_days MUST be cumulative (each touch = previous touch's timing_days + 2-3 days)
  * Example: Touch 1 (0), Touch 2 (3), Touch 3 (6), Touch 4 (9) - NOT all touches with same timing_days
✓ timing_days values must increase sequentially (0 < touch2 < touch3 < touch4...)
✓ subject_line present for email/linkedin, null for phone/video
✓ Content references specific pain points (not generic)
✓ duration_days = last touch's timing_days (NOT sum of all touches)
✓ duration_days matches tier requirements (tier_1: 14-21, tier_2: 12-14, tier_3: 10)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT JSON SCHEMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "personas": [
    {{
      "persona_name": "string (max 60 chars)",
      "tier": "tier_1 | tier_2 | tier_3",
      "job_titles": ["array", "of", "target", "title", "strings"],
      "excluded_job_titles": ["array", "of", "titles", "to", "avoid"],
      "industry": "string (single vertical)",
      "company_size_range": "string (use standard thresholds: 50, 200, 500, 1000, 2000, 5000, 10000)",
      "company_type": "string",
      "location": "string (state/region/country/multi-country based on data)",
      "description": "string (must include: team size, deal size, sales cycle, stakeholder count)"
    }}
  ],
  "personas_with_mappings": [
    {{
      "persona_name": "string (exact match from personas above)",
      "mappings": [
        {{
          "pain_point": "string (1-2 sentences, <300 chars)",
          "value_proposition": "string (1-2 sentences, <300 chars, product integrated)"
        }}
      ]
    }}
  ],
  "sequences": [
    {{
      "name": "string",
      "persona_name": "string (exact match from personas)",
      "objective": "string (one clear sentence describing sequence goal)",
      "total_touches": 4-6,
      "duration_days": 10-21,
      "touches": [
        {{
          "sort_order": 1,
          "touch_type": "email | linkedin | phone | video",
          "timing_days": 0,
          "objective": "string",
          "subject_line": "string or null",
          "content_suggestion": "string",
          "hints": "string or null"
        }}
      ]
    }}
  ],
  "generation_reasoning": "string (MUST explain: 1) Which personas were selected and why, 2) Whether CRM data was used, 3) How CRM data influenced specific fields like location, industry, company_size_range, job_titles, etc.)",
  "data_sources": {{
    "crm_data_used": true/false,
    "crm_data_influence": "string (explain which persona fields were influenced by CRM data, e.g., 'location based on 70% CA concentration, industry from top 3 industries, job_titles from contact analysis')",
    "source_url": "string (optional: primary web content source URL used for generating personas, e.g., official website, case study, or news article URL)"
  }}
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUALITY CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before submitting, verify:
✓ persona_name ≤ 60 characters (count them!)
✓ industry is single vertical (not combined)
✓ Tier distribution balanced: tier_1 (30-40%), tier_2 (40-50%), tier_3 (10-20%)
✓ job_titles has 10-30+ titles matching industry buying patterns
✓ excluded_job_titles has 3-10+ titles to avoid for this persona
✓ description includes all 4 metrics: team size, deal size, sales cycle, stakeholders
✓ company_size_range uses standard thresholds (50, 200, 500, 1000, 2000, 5000, 10000)
✓ company_size_range width matches buying behavior similarity (narrow for distinct, wide for similar)
✓ location uses appropriate geographic precision based on data (state/country/region/global)
✓ job_titles ordered by seniority (C-level → VP → Director → Manager)
✓ excluded_job_titles includes roles outside decision authority and unrelated functions
✓ Each persona differs in 2+ dimensions (industry, size, geography, function)
✓ Each persona has 3-10 mappings
✓ Pain points are <300 chars, 1-2 sentences
✓ Value props are <300 chars, 1-2 sentences
✓ **Value props include product name naturally integrated**
✓ Pain points mention WHO and WHAT impact
✓ Value props mention HOW product solves it with quantified benefits
✓ Mappings are relevant to persona's role/industry/size
✓ Product names match the actual products from the catalog
✓ No generic/vague statements - all specific and tactical
✓ {generate_count} sequences (one per persona)
✓ Each sequence has 4-6 touches
✓ sort_order is 1, 2, 3... (sequential)
✓ First touch: timing_days = 0
✓ Later touches: timing_days = 2-3 days apart from previous touch
✓ subject_line present for email/linkedin, null for phone/video
✓ Content references specific pain points (not generic)
✓ duration_days = last touch's timing_days (NOT sum of all)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOW GENERATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[SELLER COMPANY]
Company Name: {company_name}

{products_section}

{crm_section}

[WEB CONTENT]
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate buyer personas, mappings, and sequences following all requirements above.

CRITICAL:
- persona_name < 60 characters
- ONE industry per persona
- ALL 4 metrics in description
- Balanced tier distribution
- job_titles: 10-30+ industry-appropriate target titles
- excluded_job_titles: 3-10+ titles to AVOID (roles outside decision authority)
- company_size_range uses standard thresholds (narrow or wide based on buying behavior)
- location precision based on available data (specific to general)
- Each persona has 3-10 mappings with product names integrated
- Each persona has 1 sequence with 4-6 touches referencing mappings

DATA SOURCE ATTRIBUTION (REQUIRED):
- If CRM data was provided and used, you MUST:
  1. Set "crm_data_used": true in data_sources
  2. In "crm_data_influence", explicitly state which persona fields were influenced by CRM data
  3. In "generation_reasoning", mention that CRM data informed the generation
- If CRM data was NOT available or NOT used:
  1. Set "crm_data_used": false
  2. Set "crm_data_influence": "CRM data not available or not used"
  3. In "generation_reasoning", state that personas were generated from web content and industry best practices only

Examples of CRM data influence:
- "Location 'California' based on CRM showing 65% accounts in CA"
- "Industry 'B2B SaaS' matches top industry (40% of CRM accounts)"
- "Company size '200-500' reflects median size of 350 employees from CRM"
- "Job titles include 'VP Sales' and 'CRO' which are top 5 titles in CRM contacts"

Return ONLY valid JSON."""
    
    # [parse_response and _fix_json_errors methods remain the same as your current version]
    
    def _fix_json_errors(self, json_str: str) -> str:
        """
        Fix common JSON errors that LLMs sometimes generate.
        
        Handles:
        - Missing commas between array elements
        - Empty objects in arrays
        - Trailing commas
        - Other syntax issues
        """
        fixed = json_str
        
        # Handle empty objects in arrays
        fixed = re.sub(r'\}\s+\{\s*\}', '}', fixed)
        fixed = re.sub(r'\}\s*\{\s*\}', '}', fixed)
        fixed = re.sub(r'\[\s*\{\s*\}', '[', fixed)
        fixed = re.sub(r',\s*\{\s*\}', '', fixed)
        
        # Fix missing commas between objects in arrays
        fixed = re.sub(r'\}\s+(\{)', r'},\1', fixed)
        
        # Remove trailing commas
        fixed = re.sub(r',\s+([}\]])', r'\1', fixed)
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
        
        # Fix double commas
        fixed = re.sub(r',\s*,+', ',', fixed)
        
        return fixed
    
    def parse_response(self, response: str) -> Dict:
        """
        Parse LLM response that contains personas, mappings, and sequences.
        
        The response should be a single JSON object with keys:
        - personas: List of personas
        - personas_with_mappings: List of personas with their mappings
        - sequences: List of outreach sequences
        """
        cleaned_response = ""
        try:
            logger.debug(f"RAW LLM RESPONSE (first 2000 chars): {response[:2000]}")
            
            # Clean markdown code block markers
            cleaned_response = response.strip()
            
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            cleaned_response = cleaned_response.strip()
            
            # Try to parse JSON, and if it fails, attempt to fix common errors
            try:
                data = json.loads(cleaned_response)
            except json.JSONDecodeError:
                logger.warning("Initial JSON parse failed, attempting to fix common errors...")
                fixed_response = self._fix_json_errors(cleaned_response)
                try:
                    data = json.loads(fixed_response)
                    logger.info("Successfully fixed JSON errors and parsed response")
                except json.JSONDecodeError as fix_error:
                    logger.error(f"Failed to parse even after fixing: {fix_error}")
                    raise
            
            # Validate required keys
            required_keys = ["personas", "personas_with_mappings", "sequences"]
            for key in required_keys:
                if key not in data:
                    logger.warning(f"Response missing '{key}' key")
                    data[key] = [] if key in ["personas", "personas_with_mappings", "sequences"] else {}
            
            # Validate each section
            if not isinstance(data["personas"], list):
                logger.warning("'personas' is not a list, converting to empty list")
                data["personas"] = []
            
            if not isinstance(data["personas_with_mappings"], list):
                logger.warning("'personas_with_mappings' is not a list, converting to empty list")
                data["personas_with_mappings"] = []
            
            if not isinstance(data["sequences"], list):
                logger.warning("'sequences' is not a list, converting to empty list")
                data["sequences"] = []
            
            # Validate data_sources if present
            if "data_sources" not in data:
                logger.warning("Response missing 'data_sources' field. Adding default values.")
                data["data_sources"] = {
                    "crm_data_used": False,
                    "crm_data_influence": "CRM data not available or not used"
                }
            
            logger.info(
                f"Two-stage generation complete: "
                f"{len(data['personas'])} personas, "
                f"{len(data['personas_with_mappings'])} personas_with_mappings, "
                f"{len(data['sequences'])} sequences"
            )
            
            # Add metadata about generation method
            data["generation_method"] = "Two-Stage Pipeline"
            data["stage_description"] = "Stage 2: Consolidated Personas + Mappings + Sequences"
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse two-stage JSON: {e}")
            logger.error(f"Raw response (first 1000 chars): {response[:1000]}...")
            if hasattr(e, 'pos') and e.pos and cleaned_response:
                start_pos = max(0, e.pos - 300)
                end_pos = min(len(cleaned_response), e.pos + 300)
                logger.error(f"Problematic section (around char {e.pos}): ...{cleaned_response[start_pos:end_pos]}...")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        
        except ValueError as e:
            logger.error(f"Two-stage validation failed: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error parsing two-stage response: {e}")
            raise ValueError(f"Failed to parse two-stage response: {e}")