"""
Two-stage baseline generator that consolidates personas, mappings, and sequences.

Stage 1: Products (reused from ProductGenerator)
Stage 2: Personas + Mappings + Sequences (consolidated in this generator)
"""
from .base_generator import BaseGenerator
from typing import Dict, List
import json
import logging
import re

logger = logging.getLogger(__name__)


class TwoStageGenerator(BaseGenerator):
    """
    Two-stage baseline generator that consolidates personas, mappings, and sequences
    into a single LLM call.
    
    This is used for ablation study to validate optimal number of stages.
    Stage 1 (Products) is handled separately, then this generator handles
    Stage 2 (Personas + Mappings + Sequences) in one consolidated prompt.
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
        return """You are an expert B2B sales strategist and intelligence analyst specializing in buyer persona development, pain-point discovery, value proposition development, and multi-touch outreach sequence design.

Your expertise includes:
- Identifying buyer company archetypes (market segments) for B2B sellers
- Crafting specific, tactical pain points matched to buyer roles and industries
- Developing compelling value propositions that integrate product names naturally
- Designing multi-touch outreach sequences that build rapport through value-first communications
- Mixing channels strategically (email, LinkedIn, phone, video) with appropriate timing
- Using buyer language and quantifying business impact with metrics

Your task is to generate THREE components in a single comprehensive response:
1. Buyer Personas (company archetypes representing market segments)
2. Pain Point-Value Proposition Mappings (specific to each persona, 3-10 per persona)
3. Multi-Touch Outreach Sequences (personalized cadences for each persona, 4-6 touches each)

CRITICAL: You are generating COMPANY ARCHETYPES (market segments), NOT individual people. Generate all three outputs in ONE response, with each part building on the previous parts. Modern sales requires providing value before asking for anything."""
    
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
Not available. Generate personas based on web content analysis.
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
        
        return f"""Generate complete B2B sales intelligence package for the seller company based on their products and market data.

═══════════════════════════════════════════════════════════════
TASK OVERVIEW
═══════════════════════════════════════════════════════════════

Generate THREE components in ONE response:
1. PART 1: Buyer Personas (EXACTLY {generate_count} personas)
2. PART 2: Pain-Value Mappings (3-10 per persona) - **Use personas from Part 1**
3. PART 3: Outreach Sequences (1 per persona, 4-6 touches) - **Use mappings from Part 2**

═══════════════════════════════════════════════════════════════
PART 1: PERSONA GENERATION
═══════════════════════════════════════════════════════════════

Generate EXACTLY {generate_count} buyer company personas (market segments).

**CRITICAL: Base personas on the products from Stage 1 (shown below). Each persona should map to specific products from the catalog.**

**Required Fields:**
- persona_name: Max 60 chars, format "[Geography] [Size] [Industry] - [Function]"
  ✅ "US Enterprise SaaS - Revenue Leaders"
  ✅ "UK Mid-Market Manufacturing - Sales VPs"
  ❌ "United States Enterprise Retail & E-commerce - Marketing Leaders" (too long)

- tier: tier_1 | tier_2 | tier_3
  Balanced distribution: tier_1 (30-40%), tier_2 (40-50%), tier_3 (10-20%)

- job_titles: 10-30+ TARGET job titles with ALL title variations (30+ allowed for comprehensive coverage)
  Include: "VP Sales", "VP of Sales", "Vice President Sales", "Vice President of Sales"
  Order by seniority: C-level → VP → Director → Manager

- excluded_job_titles: 3-10+ titles to AVOID (roles outside decision authority)
  Examples: HR roles for sales tech, IT roles for marketing tools, junior roles without budget

- industry: ONE specific vertical (never combine industries)
  ✅ "B2B SaaS Platforms" or "Healthcare Revenue Cycle Management"
  ❌ "Professional Services - Consulting, IT, Legal"

- company_size_range: Use standard thresholds (50, 200, 500, 1000, 2000, 5000, 10000)
  Examples: "50-200", "500-2000", "2000-10000", "10000+"

- location: Geographic focus based on market data
  Examples: "California", "United States", "Western Europe", "APAC", "Global"

- description: MUST include ALL 4 quantitative metrics:
  1. Team size: "20-100 sales reps" or "50-200 staff"
  2. Deal size: "$100K-$350K annually" or "€200K-€800K multi-year"
  3. Sales cycle: "3-6 months" or "8-12 months"
  4. Stakeholders: "3-5 decision makers" or "6-9 stakeholders"

**Description Structure (5-7 sentences):**
[Company characteristics]. [Team size]. [Deal size] with [sales cycle] involving [stakeholders]. [Decision process]. [Strategic fit with products]. [Engagement approach].

**Job Titles - Key Patterns (include ALL variations):**

Sales Leaders (C-level & VP):
- CRO, Chief Revenue Officer, CSO, Chief Sales Officer
- VP Sales, VP of Sales, Vice President Sales, Vice President of Sales, SVP Sales
- VP Enterprise Sales, VP Commercial Sales, Regional VP Sales, VP Sales Americas
- Head of Sales, Global Head of Sales

Sales Leaders (Director & Manager):
- Director Sales, Director of Sales, Sr Director Sales, Senior Director Sales
- Sales Manager, Senior Sales Manager, Sales Operations Manager

Revenue Operations:
- VP Revenue Operations, VP of Revenue Operations, VP RevOps, Vice President Revenue Operations
- Director Revenue Operations, Director Sales Operations, RevOps Manager

Sales Enablement:
- VP Sales Enablement, VP of Sales Enablement, Vice President Sales Enablement
- Director Sales Enablement, Sales Enablement Manager

Marketing:
- CMO, Chief Marketing Officer
- VP Marketing, VP of Marketing, Vice President Marketing
- Director Marketing, Marketing Operations Manager

Healthcare:
- CAO, Chief Administrative Officer, CFO, Chief Financial Officer
- VP Revenue Cycle Management, Director of Revenue Cycle

Retail/E-commerce:
- CMO, Chief Digital Officer, CDO
- VP Digital Commerce, VP E-commerce, Director E-commerce

Financial Services:
- COO, Chief Operating Officer, CRO
- VP Distribution, Director Sales Operations

**Example Persona 1:**
{{
  "persona_name": "US Enterprise SaaS - Revenue Leaders",
  "tier": "tier_1",
  "job_titles": ["CRO", "Chief Revenue Officer", "VP Sales", "Vice President of Sales", "VP Revenue Operations", "Director Sales", "Sales Operations Manager"],
  "excluded_job_titles": ["VP Marketing", "CMO", "VP Engineering", "CTO", "VP HR", "Director of Product"],
  "industry": "B2B SaaS Platforms",
  "company_size_range": "2000-10000 employees",
  "company_type": "Large enterprise SaaS vendors with global commercial teams",
  "location": "United States",
  "description": "Enterprise SaaS platforms with 200-500 sales reps across global go-to-market teams. $500K-$2M annual contracts with 8-12 month sales cycles involving 6-9 stakeholders. Procurement requires security reviews, ROI analysis, and executive sponsorship. Strong fit for Sales Cloud, Revenue Cloud, and Data Cloud. Best engaged through executive briefings, pilot programs, and enterprise customer case studies."
}}

**Example Persona 2:**
{{
  "persona_name": "UK Mid-Market Services - Sales Directors",
  "tier": "tier_2",
  "job_titles": ["Director of Sales", "Sales Director", "Sr Director Sales", "Director Business Development", "Sales Manager", "Senior Sales Manager"],
  "excluded_job_titles": ["VP Engineering", "CTO", "HR Director", "CFO", "Legal Counsel"],
  "industry": "Professional Services",
  "company_size_range": "50-500 employees",
  "company_type": "Mid-size professional services and consulting firms",
  "location": "United Kingdom",
  "description": "UK consulting firms with 10-40 sales professionals managing partner-led sales. £40K-£200K annual technology spend with 2-5 month procurement cycles involving 2-4 stakeholders. Decision-making balances cost efficiency with scalability. Moderate fit for CRM and pipeline management tools. Best engaged via ROI-focused proposals and UK-specific case studies."
}}

═══════════════════════════════════════════════════════════════
PART 2: MAPPINGS GENERATION
═══════════════════════════════════════════════════════════════

For EACH persona generated in Part 1, create 3-10 pain point-value proposition mappings.

**CRITICAL: Use the personas you generated in Part 1 above. Reference them by exact persona_name.**

**Requirements:**
- 3-10 mappings per persona (not 5-7, full range is 3-10)
- Pain points: 1-2 sentences, <300 chars, specific to persona's role/industry/size
  Must mention WHO struggles and WHAT impact (revenue, cost, efficiency, risk)

- Value propositions: 1-2 sentences, <300 chars
  **MUST integrate product name naturally** (from Stage 1 products)
  Include quantified benefits (%, time, $)
  Mention HOW product solves the pain

**Product Integration Patterns:**
- Start with product: "Sales Cloud automates..."
- Product as subject: "Einstein AI captures..."
- Product in middle: "Teams using Marketing Cloud see 40% more leads..."
- Product with feature: "Service Cloud's AI chatbots resolve 60% of cases..."
- Product with specifics: "Commerce Cloud (B2B + B2C) unifies all channels..."

**Mapping Count per Persona:**
Generate 3-10 mappings covering different aspects:
- Operational efficiency
- Revenue/pipeline impact
- Team productivity
- Data/visibility challenges
- Compliance/risk issues
- Scaling challenges
- Technology/integration issues

**Example Mapping 1:**
{{
  "pain_point": "Sales reps waste 30% of time on manual data entry, reducing selling time and quota attainment.",
  "value_proposition": "Sales Cloud automates 80% of CRM updates with Einstein AI, freeing 10+ hours per rep per week for revenue-generating activities."
}}

**Example Mapping 2:**
{{
  "pain_point": "Forecast accuracy suffers from gut-feel predictions, causing missed targets and board surprises.",
  "value_proposition": "Einstein Forecasting analyzes 50+ pipeline signals to predict close rates with 95% accuracy, eliminating forecast surprises."
}}

**Example Mapping 3:**
{{
  "pain_point": "Sales teams struggle with too many disjointed prospecting tools, creating data silos and driving up tech spend.",
  "value_proposition": "RegieOne consolidates multiple prospecting tools (SEP, Dialer, Enrichment, Intent) into one platform, saving costs and unifying data for greater visibility."
}}

✅ GOOD Value Propositions:
- "Sales Cloud automates updates, freeing 10hrs/week per rep"
- "Tableau dashboards cut reporting time by 60%"
- "MuleSoft integration reduces project time by 40%"
- "Agents consolidate multiple prospecting tools into one platform, saving costs and streamlining workflow"

❌ BAD Value Propositions:
- "Our platform improves efficiency" (no product name, no metric)
- "Helps teams work better" (vague, no specifics)
- "Better productivity and efficiency" (no product, no quantification)

═══════════════════════════════════════════════════════════════
PART 3: SEQUENCES GENERATION
═══════════════════════════════════════════════════════════════

For EACH persona, create ONE outreach sequence with 4-6 touches.

**CRITICAL: Use the personas and mappings you generated in Parts 1-2 above.**

**CRITICAL TIMING RULES:**
- First touch: timing_days = 0 (always)
- Subsequent touches: timing_days = 2-3 days apart from previous touch
- Duration follows tier requirements (this is the LAST touch's timing_days):
  * tier_1 (Enterprise): duration_days = 14-21
  * tier_2 (Mid-market): duration_days = 12-14
  * tier_3 (SMB): duration_days = 10
- Example: Touch 1 (day 0), Touch 2 (day 3), Touch 3 (day 6), Touch 4 (day 9) → duration_days = 9

**Requirements:**
- 4-6 touches per sequence (tier-specific)
- Touch progression: email → linkedin → email → phone
- Subject lines: <60 chars for email/linkedin, null for phone/video
- Content: Reference SPECIFIC pain points from Part 2 mappings (not generic)
- Hints: Actionable, specific personalization guidance or null

**Sequence Strategy by Tier:**
- tier_1 (Enterprise): 5-6 touches, 14-21 days duration
  * More nurture, build credibility slowly
  * 2+ LinkedIn touches (social proof critical)
  * Phone touch later (touch 5-6)

- tier_2 (Mid-market): 5 touches, 12-14 days duration
  * Balanced approach
  * 1-2 LinkedIn touches
  * Phone touch at position 4-5

- tier_3 (SMB): 4 touches, 10 days duration
  * Faster, more direct approach
  * 1 LinkedIn touch
  * Phone touch at position 4

**Touch Structure Template:**
- Touch 1 (Day 0, Email): Brief intro + 1 specific pain point from mappings
- Touch 2 (Day 2-3, LinkedIn): Share case study/insight (build credibility)
- Touch 3 (Day 5-7, Email): Deep dive on value prop with customer example
- Touch 4 (Day 9-10, Phone): Direct meeting request
- Touch 5-6 (Optional): New angle or breakup email

**Example Touch:**
{{
  "sort_order": 1,
  "touch_type": "email",
  "timing_days": 0,
  "objective": "Introduce pipeline visibility challenge",
  "subject_line": "30% better forecasts for enterprise teams",
  "content_suggestion": "Hi {{{{first_name}}}}, noticed {{{{company}}}} recently expanded to {{{{region}}}}. Many enterprise SaaS companies with 200+ reps face pipeline visibility challenges across regions. {{{{similar_company}}}} improved forecast accuracy by 30% using centralized pipeline automation. Worth exploring? [Link to 2-min overview]",
  "hints": "Personalize with recent funding/expansion news if available"
}}

✅ GOOD Subject Lines:
- "30% better forecasts for 500-rep teams"
- "How [Similar Co] cut CRM admin by 10hrs/week"
- "Quick question about your Q4 pipeline"

❌ BAD Subject Lines:
- "Important business opportunity" (generic)
- "I'd love to connect" (salesy)
- "Checking in on my last email" (pushy)

✅ GOOD Content:
- "Hi {{{{first_name}}}}, noticed {{{{company}}}} expanded to EMEA. Many 500+ rep teams struggle with multi-region pipeline visibility—{{{{similar_company}}}} improved forecast accuracy 30% by centralizing their pipeline. Worth a quick chat?"

❌ BAD Content:
- "We're the leading CRM provider and would love to show you our platform. When can we schedule a demo?"

═══════════════════════════════════════════════════════════════
OUTPUT JSON SCHEMA
═══════════════════════════════════════════════════════════════

Return a JSON object with this structure:

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
  "generation_reasoning": "string (explain persona selection and whether CRM data was used)",
  "data_sources": {{
    "crm_data_used": true/false,
    "crm_data_influence": "string (explain which fields were influenced by CRM data)",
    "source_url": "string (optional: primary web content source URL)"
  }}
}}

═══════════════════════════════════════════════════════════════
COMPANY DATA
═══════════════════════════════════════════════════════════════

Company Name: {company_name}

{products_section}

{crm_section}

[WEB CONTENT]
{context[:3000]}

═══════════════════════════════════════════════════════════════
CRITICAL REMINDERS
═══════════════════════════════════════════════════════════════

Generation Requirements:
1. PART 1: Generate EXACTLY {generate_count} personas based on products from Stage 1
2. PART 2: For EACH persona, generate 3-10 mappings integrating product names from catalog
3. PART 3: For EACH persona, generate 1 sequence (4-6 touches) referencing Part 2 mappings

Cross-Part Instructions:
✓ Part 1: Base personas on products from Stage 1 catalog
✓ Part 2: Use exact persona_name from Part 1, integrate products from catalog
✓ Part 3: Reference specific pain points from Part 2 mappings in sequence content

Format Requirements:
✓ Return ONLY raw JSON (no markdown, no ```json blocks, no explanations)
✓ Your response must start with {{ and end with }}
✓ All personas must have 4 metrics in description
✓ All value propositions must include product names
✓ All sequences must have 4-6 touches with correct progression
✓ Subject lines <60 chars for email/linkedin, null for phone/video

Validation Checklist:
✓ {generate_count} personas generated
✓ Each persona has 3-10 mappings (full range, not restricted to 5-7)
✓ Each persona has 1 sequence with 4-6 touches
✓ All sequences: sort_order is 1, 2, 3, 4... (sequential integers)
✓ All sequences: first touch timing_days = 0
✓ All sequences: subsequent touches timing_days = 2-3 days apart from previous touch
✓ All sequences: duration_days matches tier requirements (tier_1: 14-21, tier_2: 12-14, tier_3: 10)
✓ All sequences: duration_days = last touch's timing_days (NOT sum of all)
✓ All sequences: subject_line present for email/linkedin, null for phone/video
✓ All sequences reference specific pain points from Part 2 mappings (not generic statements)
✓ All descriptions include 4 metrics (team, deal, cycle, stakeholders)
✓ All value props integrate product names naturally
✓ All sequences progress logically (email → linkedin → email → phone)
✓ Tier distribution balanced: tier_1 (30-40%), tier_2 (40-50%), tier_3 (10-20%)

DATA SOURCE ATTRIBUTION:
- If CRM data was provided and used:
  * Set "crm_data_used": true
  * In "crm_data_influence", state which persona fields were influenced
  * Example: "Location 'California' based on 70% CRM accounts in CA"
- If CRM data not available:
  * Set "crm_data_used": false
  * Set "crm_data_influence": "CRM data not available or not used"

Generate all three components now."""
    
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