from .base_generator import BaseGenerator
from typing import Dict, List
import json
import logging

logger = logging.getLogger(__name__)

class PersonaGenerator(BaseGenerator):
    """
    Generates buyer company personas (market segments) for a seller company.
    
    This is NOT for generating individual contacts at a specific company.
    This generates buyer COMPANY ARCHETYPES representing market segments.
    """
    
    def get_system_message(self) -> str:
      return """You are an expert B2B sales strategist helping generate buyer company personas for a seller company. 

Your task is to analyze the seller's business and identify buyer company archetypes that would be ideal customers for the seller's products and services.

CRITICAL: You are generating COMPANY ARCHETYPES (market segments), NOT individual people.

Examples:
✓ CORRECT: "CA Mid-Market SaaS - Sales Leaders" (a type of company)
✗ WRONG: "John Smith, CFO at Acme Corp" (a specific person)
"""

    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
        
        generate_count = kwargs.get('generate_count', 5)
        
        products = kwargs.get('products', [])
        crm_data = kwargs.get('crm_data', '')
        
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
        
        return f"""## Task

Generate buyer company personas (market segments) for the seller company. Each persona represents a distinct market segment with clear needs the seller's products can address.

Generate 3-8 personas depending on market diversity.

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

5. **target_decision_makers**: 10-30+ industry-appropriate titles from master list
   - Match titles to how that industry actually buys
   - Retail → Marketing/Commerce leaders (NOT Sales VPs)
   - Healthcare → Revenue Cycle/Clinical leaders (NOT Enablement)
   - Manufacturing → Operations/Sales Ops (NOT Enablement/SDR)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSONA FIELDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**persona_name** (string): Concise market segment identifier, max 60 chars

**tier** (enum): tier_1 | tier_2 | tier_3
- Consider: deal size, product fit, sales cycle, accessibility, volume
- Balance distribution across tiers

**target_decision_makers** (array): 10-30+ job titles from master list below
- Include ALL title variations for matching coverage
- Order by seniority: C-level → VP → Director → Manager

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

**Title Selection Guidelines:**
1. Include ALL variations: "VP of Sales", "Vice President of Sales", "Vice President Sales", "VP Sales"
2. Include geographic variants: "Global Head", "Regional VP", "VP Americas"
3. Include functional variants: "VP Enterprise Sales", "VP Commercial Sales"
4. Typical count: 10-15 titles (Small), 15-22 (Mid-Market), 18-25 (Large), 20-27 (Enterprise)
5. Order by seniority within the array

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT JSON SCHEMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "personas": [
    {{
      "persona_name": "string (max 60 chars)",
      "tier": "tier_1 | tier_2 | tier_3",
      "target_decision_makers": ["array", "of", "title", "strings"],
      "industry": "string (single vertical)",
      "company_size_range": "string (use standard thresholds: 50, 200, 500, 1000, 2000, 5000, 10000)",
      "company_type": "string",
      "location": "string (state/region/country/multi-country based on data)",
      "description": "string (must include: team size, deal size, sales cycle, stakeholder count)"
    }}
  ],
  "generation_reasoning": "string"
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "personas": [
    {{
      "persona_name": "CA Enterprise SaaS - Revenue Leaders",
      "tier": "tier_1",
      "target_decision_makers": [
        "CRO", "Chief Revenue Officer", "Chief Sales Officer", "CSO",
        "VP of Sales", "Vice President of Sales", "Vice President Sales", "VP Sales", "SVP Sales",
        "VP Sales Enablement", "Vice President Sales Enablement", "VP of Sales Enablement",
        "Head of Sales Enablement", "Global Head of Sales Enablement",
        "VP Revenue Operations", "Vice President Revenue Operations", "VP of Revenue Operations", "VP RevOps",
        "Head of Revenue Operations", "VP GTM Operations"
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
      "target_decision_makers": [
        "Director of Sales", "Director Sales", "Senior Director Sales", "Sr Director Sales",
        "Director Business Development", "Director of Business Development",
        "Manager of Sales", "Sales Manager", "Senior Sales Manager",
        "Manager Sales Development", "Sales Development Manager",
        "Director of Marketing", "Director Marketing"
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
      "target_decision_makers": [
        "VP of Sales", "Vice President of Sales", "VP Sales",
        "VP of Operations", "Vice President of Operations", "VP Operations",
        "Director of Sales", "Senior Director Sales", "Sales Director",
        "Director of Operations", "Senior Director Operations",
        "VP Revenue Operations", "Director Sales Operations"
      ],
      "industry": "Manufacturing - Industrial Equipment",
      "company_size_range": "1000-5000 employees",
      "company_type": "Large German, Austrian, and Swiss manufacturers of precision equipment and industrial machinery",
      "location": "DACH Region",
      "description": "Established DACH manufacturers with regional and global sales operations and complex multi-site production. 50-200 sales and technical sales staff. €200K-€800K annual platform investments with 6-9 month evaluation cycles involving 4-6 stakeholders (Vertriebsleiter, Betriebsleiter, IT, Einkauf). Decision-making emphasizes integration with SAP/ERP systems, technical precision, and long-term vendor partnerships. Strong fit for CRM with CPQ and industrial-grade integrations. Best engaged through technical workshops, German-language support commitments, and references from peer DACH manufacturers."
    }}
  ],
  "generation_reasoning": "Selected diverse personas spanning geographies (California, UK, DACH), company sizes (50-500, 1000-5000, 2000-10000), and industries. Used specific geographies where industry concentration exists (CA for SaaS, DACH for manufacturing) and country-level for distributed markets (UK services). Company size ranges span multiple thresholds to reflect similar buying behaviors within each segment. Tier distribution balanced across strategic value."
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUALITY CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before submitting, verify:
✓ persona_name ≤ 60 characters (count them!)
✓ industry is single vertical (not combined)
✓ Tier distribution balanced: tier_1 (30-40%), tier_2 (40-50%), tier_3 (10-20%)
✓ target_decision_makers has 10-30+ titles matching industry
✓ description includes all 4 metrics: team size, deal size, sales cycle, stakeholders
✓ company_size_range uses standard thresholds (50, 200, 500, 1000, 2000, 5000, 10000)
✓ company_size_range width matches buying behavior similarity (narrow for distinct, wide for similar)
✓ location uses appropriate geographic precision based on data (state/country/region/global)
✓ Titles ordered by seniority (C-level → VP → Director → Manager)
✓ Each persona differs in 2+ dimensions (industry, size, geography, function)

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

Generate buyer personas following all requirements above.

CRITICAL:
- persona_name < 60 characters
- ONE industry per persona
- ALL 4 metrics in description
- Balanced tier distribution
- Industry-appropriate job titles
- company_size_range uses standard thresholds (narrow or wide based on buying behavior)
- location precision based on available data (specific to general)

Return ONLY valid JSON.
"""
    
    def parse_response(self, response_text: str) -> Dict:
        """
        Parse and validate LLM response
        """
        try:
            result = json.loads(response_text)
            
            if "personas" not in result:
                raise ValueError("Response missing 'personas' key")
            
            personas = result["personas"]
            
            if not isinstance(personas, list) or len(personas) == 0:
                raise ValueError("'personas' must be a non-empty array")
            
            for idx, persona in enumerate(personas):
                self._validate_persona(persona, idx)
            
            logger.info(f"Successfully parsed {len(personas)} buyer personas")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
    
    def _validate_persona(self, persona: Dict, index: int):
        """Validate individual persona structure"""
        required_fields = [
            "persona_name",
            "tier", 
            "target_decision_makers",
            "industry",
            "company_size_range",
            "company_type",
            "location",
            "description"
        ]
        
        for field in required_fields:
            if field not in persona:
                raise ValueError(f"Persona {index} missing required field: {field}")
        
        if persona["tier"] not in ["tier_1", "tier_2", "tier_3"]:
            raise ValueError(f"Persona {index} has invalid tier: {persona['tier']}")
        
        if not isinstance(persona["target_decision_makers"], list):
            raise ValueError(
                f"Persona {index}: target_decision_makers must be an array, "
                f"got {type(persona['target_decision_makers'])}"
            )
        
        if len(persona["target_decision_makers"]) == 0:
            raise ValueError(f"Persona {index}: target_decision_makers cannot be empty")
        
        for title in persona["target_decision_makers"]:
            if not isinstance(title, str):
                raise ValueError(
                    f"Persona {index}: all titles must be strings, got {type(title)}"
                )
        
        if len(persona["target_decision_makers"]) < 10:
            logger.warning(
                f"Persona {index} '{persona['persona_name']}' has only "
                f"{len(persona['target_decision_makers'])} titles. "
                f"Recommend 10-30+ for better matching coverage."
            )
        
        if not persona["persona_name"] or len(persona["persona_name"]) < 10:
            raise ValueError(f"Persona {index}: persona_name too short or empty")
        
        logger.debug(
            f"Persona {index} validated: '{persona['persona_name']}' "
            f"with {len(persona['target_decision_makers'])} titles"
        )
    
    def parse_response(self, response: str) -> Dict:
        """
        Parse and validate LLM response for buyer persona generation.
        """
        try:
            logger.debug(f"RAW LLM RESPONSE: {response[:2000]}")
            
            # Clean markdown code block markers
            cleaned_response = response.strip()
            
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON
            data = json.loads(cleaned_response)
            
            # Validate structure
            if "personas" not in data:
                raise ValueError("Response missing 'personas' key")
            
            personas = data["personas"]
            
            if not isinstance(personas, list) or len(personas) == 0:
                raise ValueError("'personas' must be a non-empty array")
            
            # Validate each persona
            for i, persona in enumerate(personas):
                logger.debug(f"Validating persona {i}: {persona.get('persona_name', 'Unknown')}")
                
                # Validate required fields
                required_fields = [
                    "persona_name", "tier", "target_decision_makers",
                    "industry", "company_size_range", "company_type",
                    "location", "description"
                ]
                
                for field in required_fields:
                    if field not in persona or persona[field] is None:
                        raise ValueError(f"Persona {i} missing required field: {field}")
                
                # Validate tier
                if persona["tier"] not in ["tier_1", "tier_2", "tier_3"]:
                    raise ValueError(f"Persona {i} invalid tier: {persona['tier']}")
                
                # Validate target_decision_makers is array
                if not isinstance(persona["target_decision_makers"], list):
                    raise ValueError(f"Persona {i}: target_decision_makers must be an array, got {type(persona['target_decision_makers'])}")
                
                if len(persona["target_decision_makers"]) == 0:
                    raise ValueError(f"Persona {i}: target_decision_makers array is empty")
                
                # Validate all titles are strings
                for title in persona["target_decision_makers"]:
                    if not isinstance(title, str):
                        raise ValueError(f"Persona {i}: all titles must be strings, got {type(title)}")
                
                # Warning if too few titles
                if len(persona["target_decision_makers"]) < 10:
                    logger.warning(
                        f"Persona {i} '{persona['persona_name']}' has only "
                        f"{len(persona['target_decision_makers'])} titles. "
                        f"Recommend 10-30+ for better matching coverage."
                    )
                
                # Validate description length
                if len(persona["description"]) < 50:
                    logger.warning(f"Persona {i} description is very short: {len(persona['description'])} chars")
                
                logger.info(
                    f"Persona {i} validated: '{persona['persona_name']}' "
                    f"({persona['tier']}, {len(persona['target_decision_makers'])} titles)"
                )
            
            logger.info(f"Successfully validated {len(personas)} buyer personas")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse persona JSON: {e}")
            logger.error(f"Raw response: {response[:500]}...")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        
        except ValueError as e:
            logger.error(f"Persona validation failed: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error parsing persona response: {e}")
            raise ValueError(f"Failed to parse persona response: {e}")
