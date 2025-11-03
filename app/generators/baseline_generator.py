from .base_generator import BaseGenerator
from typing import Dict
import json
import logging
import re

logger = logging.getLogger(__name__)


class BaselineGenerator(BaseGenerator):
    """
    Single-shot baseline generator that generates all 4 outputs in ONE LLM call.
    
    This is used for baseline comparison against the multi-stage pipeline.
    All outputs are generated simultaneously without inter-stage information flow.
    """
    
    async def generate(self, company_name: str, context: str, **kwargs) -> Dict:
        """
        Override to increase max_completion_tokens for large response.
        Baseline needs more tokens since it generates all 4 outputs at once.
        """
        try:
            from ..services.llm_service import get_llm_service
            llm_service = get_llm_service()
            
            prompt = self.build_prompt(company_name, context, **kwargs)
            system_message = self.get_system_message()
            
            # Increase max_completion_tokens for baseline (all 4 outputs in one call)
            response = await llm_service.generate_async(
                prompt=prompt,
                system_message=system_message,
                temperature=1.0,
                max_completion_tokens=20000  # More tokens for consolidated response
            )
            
            parsed_result = self.parse_response(response.content)
            parsed_result["model"] = response.model
            return parsed_result
            
        except Exception as e:
            logger.error(f"Baseline generation failed: {str(e)}")
            raise
    
    def get_system_message(self) -> str:
        return """You are an expert B2B sales intelligence analyst. Generate a complete sales intelligence package for the seller company based on their web content.

Your task is to generate ALL four components in a single response:
1. Products (5-15 products)
2. Personas (3-8 buyer personas)
3. Pain Point-Value Proposition Mappings (5-7 per persona)
4. Outreach Sequences (1 per persona, 4-6 touches each)

CRITICAL: Generate all outputs in ONE response. Do not split into multiple responses."""
    
    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
        # Use the consolidate prompt from the original function
        return self._get_baseline_prompt(company_name, context)
    
    def _get_baseline_prompt(self, company_name: str, context: str) -> str:
        """Internal method containing the consolidated prompt"""
        return f"""You are an expert B2B sales intelligence analyst. Generate a complete sales intelligence package for the seller company based on their web content.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate ALL four components in a single response:
1. Products (5-15 products)
2. Personas (3-8 buyer personas)
3. Pain Point-Value Proposition Mappings (5-7 per persona)
4. Outreach Sequences (1 per persona, 4-6 touches each)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1: PRODUCTS GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Extract ALL products and services from the web content.

**Requirements:**
- Use official product names from website
- 2-4 sentence descriptions (150-300 characters)
- Focus on value propositions and use cases (not technical specs)
- Structure: What it does → Who it helps → Key benefits
- Include all distinct product lines and offerings

**Example Product:**
{{
  "product_name": "Sales Cloud",
  "description": "Complete CRM for managing sales pipelines, forecasting revenue, and automating sales processes. Helps sales teams close deals faster with AI-powered insights and workflow automation. Scales from small teams to global enterprises."
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2: PERSONAS GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate 3-8 buyer company personas (market segments) based on the products above.

**CRITICAL: Base personas on the products you generated in Part 1.**

**Requirements:**
- persona_name: Max 60 chars, format "[Geography] [Size] [Industry] - [Function]"
- tier: tier_1 (30-40%), tier_2 (40-50%), tier_3 (10-20%)
- target_decision_makers: 10-30 job titles from this list:
  * Sales: CRO, VP Sales, VP Revenue Operations, Director Sales
  * Enablement: VP Sales Enablement, Director Sales Enablement
  * Marketing: CMO, VP Marketing, Director Marketing
  * Healthcare: CAO, VP Revenue Cycle, Director Revenue Cycle
  * Retail: CMO, VP Digital Commerce, Director E-commerce
  * Financial: COO, VP Distribution, Director Sales Operations
- industry: Single specific vertical
- company_size_range: Use standard thresholds (50, 200, 500, 1000, 2000, 5000, 10000)
- location: State/region/country/multi-country based on market
- description: MUST include all 4 metrics:
  * Team size (e.g., "50-200 staff")
  * Deal size (e.g., "$200K-$800K annually")
  * Sales cycle (e.g., "4-8 months")
  * Stakeholders (e.g., "4-6 decision makers")

**Example Persona:**
{{
  "persona_name": "US Enterprise SaaS - Revenue Leaders",
  "tier": "tier_1",
  "target_decision_makers": ["CRO", "VP Sales", "VP Revenue Operations", "Director Sales"],
  "industry": "B2B SaaS Platforms",
  "company_size_range": "2000-10000 employees",
  "company_type": "Large enterprise SaaS vendors with global teams",
  "location": "United States",
  "description": "Enterprise SaaS platforms with 200-500 sales reps. $500K-$2M annual contracts with 8-12 month sales cycles involving 6-9 stakeholders. Strong fit for CRM and analytics."
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 3: MAPPINGS GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each persona generated in Part 2, create 5-7 pain point-value proposition mappings.

**Requirements:**
- Pain points: 1-2 sentences, <300 chars, specific to persona's role/industry
- Value propositions: 1-2 sentences, <300 chars
- **MUST integrate product name naturally** (from Part 1 products)
- Include quantified benefits (%, time, $)

**Example Mapping:**
{{
  "persona_name": "US Enterprise SaaS - Revenue Leaders",
  "mappings": [
    {{
      "pain_point": "Sales reps waste 30% of time on manual data entry, reducing selling time.",
      "value_proposition": "Sales Cloud automates 80% of CRM updates, freeing 10+ hours per rep per week."
    }}
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 4: SEQUENCES GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each persona, create one outreach sequence with 4-6 touches.

**Requirements:**
- Touch progression: email → linkedin → email → phone
- Timing: First touch = 0 days, then 2-3 days apart
- Duration: tier_1 (14-21 days), tier_2 (12-14 days), tier_3 (10 days)
- Subject lines: <60 chars for email/linkedin, null for phone
- Content: Reference specific pain points from Part 3 mappings
- Hints: Actionable personalization tips

**Example Sequence Touch:**
{{
  "sort_order": 1,
  "touch_type": "email",
  "timing_days": 0,
  "objective": "Introduce pipeline visibility challenge",
  "subject_line": "30% better forecasts for enterprise teams",
  "content_suggestion": "Hi {{{{first_name}}}}, many enterprise SaaS teams struggle with pipeline visibility. {{{{similar_company}}}} improved forecast accuracy 30% with centralized automation. Worth exploring?",
  "hints": "Personalize with recent expansion news"
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT JSON SCHEMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "products": [
    {{
      "product_name": "string",
      "description": "string (2-4 sentences, 150-300 chars)"
    }}
  ],
  "personas": [
    {{
      "persona_name": "string (max 60 chars)",
      "tier": "tier_1 | tier_2 | tier_3",
      "target_decision_makers": ["array of strings"],
      "industry": "string",
      "company_size_range": "string",
      "company_type": "string",
      "location": "string",
      "description": "string (must include 4 metrics)"
    }}
  ],
  "personas_with_mappings": [
    {{
      "persona_name": "string (exact match from personas)",
      "mappings": [
        {{
          "pain_point": "string (<300 chars)",
          "value_proposition": "string (<300 chars, product integrated)"
        }}
      ]
    }}
  ],
  "sequences": [
    {{
      "name": "string",
      "persona_name": "string (exact match)",
      "objective": "string",
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
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPANY DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Company Name: {company_name}

Web Content:
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL REMINDERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Generate all 4 parts in ONE response
2. Personas should be based on products from Part 1
3. Mappings should reference products by name
4. Sequences should reference mappings from Part 3
5. Follow all format requirements (lengths, required fields)
6. Return ONLY valid JSON (no markdown, no ```json blocks)

Generate now."""
    
    def _fix_json_errors(self, json_str: str) -> str:
        """
        Fix common JSON errors that LLMs sometimes generate.
        
        Handles:
        - Missing commas between array elements
        - Empty objects in arrays (e.g., } { } )
        - Trailing commas
        - Other syntax issues
        """
        fixed = json_str
        
        # Step 1: Handle the specific case: } followed by empty object { }
        # Pattern: } whitespace { whitespace }
        # Replace with just } (removing the empty object, comma will be added in step 3 if needed)
        fixed = re.sub(r'\}\s+\{\s*\}', '}', fixed)
        fixed = re.sub(r'\}\s*\{\s*\}', '}', fixed)
        
        # Step 2: Remove standalone empty objects in arrays (not preceded by })
        # Pattern: [ whitespace { whitespace } or , whitespace { whitespace }
        fixed = re.sub(r'\[\s*\{\s*\}', '[', fixed)
        fixed = re.sub(r',\s*\{\s*\}', '', fixed)
        
        # Step 3: Fix missing commas between objects in arrays
        # Pattern: } followed by whitespace then { (not preceded by comma)
        # This handles cases where objects are adjacent without comma separator
        fixed = re.sub(r'\}\s+(\{)', r'},\1', fixed)
        
        # Step 4: Remove trailing commas before } or ]
        fixed = re.sub(r',\s+([}\]])', r'\1', fixed)
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
        
        # Step 5: Fix double commas (can happen after our fixes)
        fixed = re.sub(r',\s*,+', ',', fixed)
        
        # Step 6: Fix commas that appear in wrong positions (edge cases)
        # Remove commas before opening braces in certain contexts
        fixed = re.sub(r',\s*\{(\s*"[^"]*":)', r'{\1', fixed)
        
        return fixed
    
    def parse_response(self, response: str) -> Dict:
        """
        Parse LLM response that contains all 4 outputs (products, personas, mappings, sequences).
        
        The response should be a single JSON object with keys:
        - products: List of products
        - personas: List of personas
        - personas_with_mappings: List of personas with their mappings
        - sequences: List of outreach sequences
        """
        cleaned_response = ""  # Initialize for error handling
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
                    # If fixing didn't work, log the error and re-raise
                    logger.error(f"Failed to parse even after fixing: {fix_error}")
                    raise
            
            # Validate required keys
            required_keys = ["products", "personas", "personas_with_mappings", "sequences"]
            for key in required_keys:
                if key not in data:
                    logger.warning(f"Response missing '{key}' key")
                    data[key] = [] if key in ["products", "personas", "personas_with_mappings", "sequences"] else {}
            
            # Validate each section
            if not isinstance(data["products"], list):
                logger.warning("'products' is not a list, converting to empty list")
                data["products"] = []
            
            if not isinstance(data["personas"], list):
                logger.warning("'personas' is not a list, converting to empty list")
                data["personas"] = []
            
            if not isinstance(data["personas_with_mappings"], list):
                logger.warning("'personas_with_mappings' is not a list, converting to empty list")
                data["personas_with_mappings"] = []
            
            if not isinstance(data["sequences"], list):
                logger.warning("'sequences' is not a list, converting to empty list")
                data["sequences"] = []
            
            logger.info(
                f"Baseline generation complete: "
                f"{len(data['products'])} products, "
                f"{len(data['personas'])} personas, "
                f"{len(data['personas_with_mappings'])} personas_with_mappings, "
                f"{len(data['sequences'])} sequences"
            )
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse baseline JSON: {e}")
            logger.error(f"Raw response (first 1000 chars): {response[:1000]}...")
            # Try to extract the problematic section
            if hasattr(e, 'pos') and e.pos and cleaned_response:
                start_pos = max(0, e.pos - 300)
                end_pos = min(len(cleaned_response), e.pos + 300)
                logger.error(f"Problematic section (around char {e.pos}): ...{cleaned_response[start_pos:end_pos]}...")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        
        except ValueError as e:
            logger.error(f"Baseline validation failed: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error parsing baseline response: {e}")
            raise ValueError(f"Failed to parse baseline response: {e}")
