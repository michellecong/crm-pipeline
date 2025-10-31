# generators/mapping_generator.py
"""
Pain point to value proposition mapping generator (Regie.ai style)
"""
from .base_generator import BaseGenerator
from typing import Dict
import json
import logging

logger = logging.getLogger(__name__)


class MappingGenerator(BaseGenerator):
    """
    Generates pain-point to value-proposition mappings for buyer personas.
    
    Creates persona-centric mappings where each persona has 3-5 specific
    pain points matched with product-integrated value propositions.
    
    Style: Regie.ai format - concise, tactical, product-integrated
    """
    
    def get_system_message(self) -> str:
        return """You are an elite B2B sales strategist and messaging expert specializing in pain-point discovery and value proposition development.

Your expertise:
- Identifying specific, tactical pain points by persona, role, industry, and company size
- Crafting concise, compelling value propositions that integrate product names naturally
- Using buyer language (not vendor speak)
- Quantifying business impact and benefits
- Following Regie.ai's proven messaging framework

Your task is to generate pain-point to value-proposition mappings that sales teams can use to create personalized, resonant pitches for each buyer persona."""

    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
        
        products = kwargs.get('products', [])
        personas = kwargs.get('personas', [])
        
        # Format products for context
        products_section = ""
        if products and len(products) > 0:
            products_json = json.dumps(products, indent=2)
            products_section = f"""
[SELLER PRODUCTS]
{products_json}
"""
        else:
            products_section = """
[SELLER PRODUCTS]
Not available. Infer products from company description.
"""
        
        # Format personas for context
        personas_section = ""
        if personas and len(personas) > 0:
            # Extract just the essential persona info
            persona_list = []
            for p in personas:
                persona_list.append({
                    "persona_name": p.get("persona_name"),
                    "tier": p.get("tier"),
                    "industry": p.get("industry"),
                    "description": p.get("description", "")[:200]  # Truncate for context
                })
            personas_json = json.dumps(persona_list, indent=2)
            personas_section = f"""
[BUYER PERSONAS]
{personas_json}
"""
        else:
            personas_section = """
[BUYER PERSONAS]
Not available. Generate mappings based on company analysis.
"""
        
        persona_count = len(personas) if personas else 3
        
        return f"""## TASK

Generate pain-point to value-proposition mappings for each buyer persona.

Each persona should have 3-10 mappings that are specific to their role, industry, and challenges.

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
CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[SELLER COMPANY]
Company Name: {company_name}

{products_section}

{personas_section}

[COMPANY WEB CONTENT]
{context[:3000]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT JSON SCHEMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "personas_with_mappings": [
    {{
      "persona_name": "string (exact match from personas)",
      "mappings": [
        {{
          "pain_point": "string (1-2 sentences, <300 chars)",
          "value_proposition": "string (1-2 sentences, <300 chars, product integrated)"
        }}
      ]
    }}
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUALITY CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before submitting, verify:
✓ Each persona has 3-10 mappings
✓ Pain points are <300 chars, 1-2 sentences
✓ Value props are <300 chars, 1-2 sentences
✓ **Value props include product name naturally integrated**
✓ Pain points mention WHO and WHAT impact
✓ Value props mention HOW product solves it with quantified benefits
✓ Mappings are relevant to persona's role/industry/size
✓ Product names match the actual products from the catalog
✓ No generic/vague statements - all specific and tactical

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOW GENERATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate mappings for all {persona_count} personas.
Return ONLY valid JSON following the schema above.
"""

    def parse_response(self, response_text: str) -> Dict:
        """
        Parse and validate LLM response for mapping generation.
        """
        try:
            logger.debug(f"RAW LLM RESPONSE: {response_text[:2000]}")
            
            # Clean markdown code block markers
            cleaned_response = response_text.strip()
            
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
            if "personas_with_mappings" not in data:
                raise ValueError("Response missing 'personas_with_mappings' key")
            
            personas_with_mappings = data["personas_with_mappings"]
            
            if not isinstance(personas_with_mappings, list) or len(personas_with_mappings) == 0:
                raise ValueError("'personas_with_mappings' must be a non-empty array")
            
            # Validate each persona and its mappings
            for i, persona_data in enumerate(personas_with_mappings):
                persona_name = persona_data.get('persona_name', f'Unknown {i}')
                logger.debug(f"Validating persona {i}: {persona_name}")
                
                # Validate required fields
                if "persona_name" not in persona_data:
                    raise ValueError(f"Persona {i} missing 'persona_name'")
                
                if "mappings" not in persona_data:
                    raise ValueError(f"Persona '{persona_name}' missing 'mappings'")
                
                mappings = persona_data["mappings"]
                
                if not isinstance(mappings, list):
                    raise ValueError(f"Persona '{persona_name}' mappings must be an array")
                
                if len(mappings) < 3:
                    logger.warning(f"Persona '{persona_name}' has only {len(mappings)} mappings (minimum: 3)")
                
                if len(mappings) > 10:
                    logger.warning(f"Persona '{persona_name}' has {len(mappings)} mappings (maximum: 10)")
                
                # Validate each mapping
                for j, mapping in enumerate(mappings):
                    # Check required fields
                    if "pain_point" not in mapping:
                        raise ValueError(f"Persona '{persona_name}' mapping {j} missing 'pain_point'")
                    
                    if "value_proposition" not in mapping:
                        raise ValueError(f"Persona '{persona_name}' mapping {j} missing 'value_proposition'")
                    
                    # Validate length
                    pain_len = len(mapping["pain_point"])
                    value_len = len(mapping["value_proposition"])
                    
                    if pain_len > 300:
                        logger.warning(
                            f"Persona '{persona_name}' mapping {j} pain_point too long "
                            f"({pain_len} chars, max 300)"
                        )
                    
                    if value_len > 300:
                        logger.warning(
                            f"Persona '{persona_name}' mapping {j} value_proposition too long "
                            f"({value_len} chars, max 300)"
                        )
                    
                    if pain_len < 20:
                        logger.warning(
                            f"Persona '{persona_name}' mapping {j} pain_point too short "
                            f"({pain_len} chars, min 20)"
                        )
                    
                    if value_len < 20:
                        logger.warning(
                            f"Persona '{persona_name}' mapping {j} value_proposition too short "
                            f"({value_len} chars, min 20)"
                        )
                
                logger.info(
                    f"Persona '{persona_name}' validated: {len(mappings)} mappings"
                )
            
            total_mappings = sum(len(p["mappings"]) for p in personas_with_mappings)
            logger.info(
                f"Successfully validated {len(personas_with_mappings)} personas "
                f"with {total_mappings} total mappings"
            )
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse mapping JSON: {e}")
            logger.error(f"Raw response: {response_text[:500]}...")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        
        except ValueError as e:
            logger.error(f"Mapping validation failed: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error parsing mapping response: {e}")
            raise ValueError(f"Failed to parse mapping response: {e}")

