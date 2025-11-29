"""
Three-stage generator for mappings + sequences consolidated (Stage 3).

This generator combines mapping and outreach generation into one LLM call,
taking personas from Stage 2 as input.
"""
from .base_generator import BaseGenerator
from typing import Dict, List
import json
import logging
import re

logger = logging.getLogger(__name__)


class ThreeStageGenerator(BaseGenerator):
    """
    Three-stage generator - Stage 3: Mappings + Sequences consolidated.
    
    Input: Personas from Stage 2, Products from Stage 1
    Output: Mappings + Sequences for each persona
    """
    
    async def generate(self, company_name: str, context: str, **kwargs) -> Dict:
        """
        Generate mappings and sequences in one call.
        """
        import time
        start_time = time.time()
        
        try:
            from ..services.llm_service import get_llm_service
            llm_service = get_llm_service()
            
            prompt = self.build_prompt(company_name, context, **kwargs)
            system_message = self.get_system_message()
            
            # Increase max_completion_tokens for consolidated response
            response = await llm_service.generate_async(
                prompt=prompt,
                system_message=system_message,
                temperature=1.0,
                max_completion_tokens=12000
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
            logger.error(f"Three-stage generation failed: {str(e)}")
            raise
    
    def get_system_message(self) -> str:
        return """You are an expert B2B sales strategist helping generate comprehensive sales intelligence.

Your expertise includes:
- Identifying specific, tactical pain points by persona, role, industry, and company size
- Crafting concise, compelling value propositions that integrate product names naturally
- Designing multi-touch outreach sequences that build rapport through value-first communications
- Using buyer language (not vendor speak)
- Quantifying business impact and benefits
- Following proven messaging frameworks (Regie.ai style)
- Mixing channels strategically (email, LinkedIn, phone, video) with appropriate timing

Your task is to generate TWO components for pre-defined personas:
1. Pain Point-Value Proposition Mappings (3-10 per persona)
2. Multi-Touch Outreach Sequences (4-6 touches per persona)

Modern sales requires providing value before asking for anything."""
    
    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
        products = kwargs.get('products', [])
        personas = kwargs.get('personas', [])
        
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
Not available. Infer products from company description.
"""
        
        # Format personas section
        personas_section = ""
        if personas and len(personas) > 0:
            personas_json = json.dumps(personas, indent=2)
            personas_section = f"""
[BUYER PERSONAS - Stage 2 Output]
{personas_json}
"""
        else:
            raise ValueError("Personas are required for three-stage Stage 3 generation")
        
        return f"""## Task Overview

Generate complete sales intelligence for Stage 3 with TWO components:

1. **PART 1: Pain-Value Mappings** - For EACH persona, generate 3-10 pain point-value proposition mappings
2. **PART 2: Outreach Sequences** - For EACH persona, generate 1 outreach sequence (4-6 touches) referencing mappings from Part 1

**CRITICAL: Use the personas provided from Stage 2. Generate mappings and sequences for ALL personas.**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{products_section}

{personas_section}

[COMPANY RESEARCH CONTEXT]
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1: PAIN-VALUE MAPPINGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For EACH persona, generate 3-10 pain point-value proposition mappings.

**CRITICAL REQUIREMENTS:**

1. **pain_point**: Specific challenge (1-2 sentences, <300 chars)
   - Role-specific, tactical, observable
   - Include quantified impact (time, money, resources)
   - Use buyer language, not vendor speak
   - Example: "Sales reps waste 30% of time on manual data entry, reducing selling time."

2. **value_proposition**: How product solves it (1-2 sentences, <300 chars)
   - Integrate product name naturally
   - Quantify benefit (time saved, revenue increase, cost reduction)
   - Use active voice and specific numbers
   - Example: "Sales Cloud automates 80% of CRM updates with Einstein AI, freeing 10+ hours per rep per week."

**STYLE:** Regie.ai format - concise, tactical, quantified, buyer-focused

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2: OUTREACH SEQUENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For EACH persona, generate ONE outreach sequence with 4-6 touches.

**SEQUENCE STRUCTURE:**

1. **name**: Descriptive sequence name
2. **persona_name**: Must match persona from input
3. **objective**: Clear campaign goal (1 sentence)
4. **total_touches**: Number of touchpoints (4-6)
5. **duration_days**: Campaign length (10-21 days)
6. **touches**: Array of touchpoint objects

**TOUCH STRUCTURE:**

Each touch must have:
- sort_order: Sequential number (1, 2, 3...)
- touch_type: "email" | "linkedin" | "phone" | "video"
- timing_days: Days after sequence start (0, 3, 7, 10, 14...)
- objective: Touch goal (1 sentence)
- subject_line: For email/linkedin (5-8 words, curiosity or value)
- content_suggestion: Message body (3-5 sentences, 100-200 words)
- hints: Personalization tips (1-2 sentences)

**BEST PRACTICES:**

1. **Touch 1 (Day 0)**: Email - Problem awareness
   - Reference pain point from mappings
   - Ask thought-provoking question
   - No product mention, no ask

2. **Touch 2 (Day 3)**: LinkedIn connection
   - Brief, personalized note
   - Reference shared context

3. **Touch 3 (Day 7)**: Email - Value introduction
   - Reference product + benefit
   - Share relevant resource
   - Still no hard ask

4. **Touch 4 (Day 10)**: Phone call
   - Reference previous touches
   - Offer 15-min chat

5. **Touch 5 (Day 14)**: Video email
   - Personalized video
   - Specific value prop for their role

6. **Touch 6 (Day 18)**: LinkedIn message - soft close
   - Break-up or next step

**CONTENT STYLE:**
- Conversational, not corporate
- Value-first, not sales-first
- Reference specific pain points and value props from Part 1
- Personalize by role, industry, company size

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON in this exact structure:

{{
  "personas_with_mappings": [
    {{
      "persona_name": "US Enterprise SaaS - Revenue Leaders",
      "mappings": [
        {{
          "pain_point": "Sales reps waste 30% of time on manual data entry, reducing selling time.",
          "value_proposition": "Sales Cloud automates 80% of CRM updates with Einstein AI, freeing 10+ hours per rep per week."
        }}
      ]
    }}
  ],
  "sequences": [
    {{
      "name": "US Enterprise SaaS - Revenue Leaders Outreach Sequence",
      "persona_name": "US Enterprise SaaS - Revenue Leaders",
      "objective": "Introduce pipeline visibility solution for enterprise sales teams",
      "total_touches": 5,
      "duration_days": 14,
      "touches": [
        {{
          "sort_order": 1,
          "touch_type": "email",
          "timing_days": 0,
          "objective": "Introduce pipeline visibility challenge",
          "subject_line": "30% better forecasts for enterprise teams",
          "content_suggestion": "Hi {{{{first_name}}}}, many enterprise SaaS teams struggle with pipeline visibility...",
          "hints": "Personalize with recent expansion news"
        }}
      ]
    }}
  ]
}}

**CRITICAL:** Generate mappings and sequences for ALL {len(personas)} personas provided."""
    
    def parse_response(self, response: str) -> Dict:
        """Parse JSON response from LLM"""
        try:
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.strip()
            
            data = json.loads(json_str)
            
            # Validate required fields
            if "personas_with_mappings" not in data:
                raise ValueError("Missing 'personas_with_mappings' field")
            if "sequences" not in data:
                raise ValueError("Missing 'sequences' field")
            
            # Add metadata about generation method
            data["generation_method"] = "Three-Stage Pipeline"
            data["stage_description"] = "Stage 3: Consolidated Mappings + Outreach Sequences"
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            logger.error(f"Response content: {response[:500]}...")
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")

