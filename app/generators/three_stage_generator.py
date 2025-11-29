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
        
        persona_count = len(personas)
        
        # Build compact personas section for outreach part (token-efficient)
        compact_personas_section = self._build_compact_personas_for_outreach(personas)
        
        return f"""## Task Overview

Generate complete sales intelligence for Stage 3 with TWO components:

1. **PART 1: Pain-Value Mappings** - For EACH persona, generate 3-10 pain point-value proposition mappings
2. **PART 2: Outreach Sequences** - For EACH persona, generate 1 outreach sequence (4-6 touches) referencing mappings from Part 1

**CRITICAL: Use the personas provided from Stage 2. Generate mappings and sequences for ALL {persona_count} personas.**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{products_section}

{personas_section}

[COMPANY RESEARCH CONTEXT]
{context[:3000]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1: PAIN-VALUE MAPPINGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
MAPPING EXAMPLES (Regie.ai Style)
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
MAPPING QUALITY CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before moving to Part 2, verify:
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
PART 2: OUTREACH SEQUENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For EACH persona, generate ONE outreach sequence with 4-6 touches.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULES (MUST FOLLOW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Generate EXACTLY {persona_count} sequences (one per persona)
2. Each sequence: 4-6 touches, 10-21 days total duration
3. Touch progression: email → linkedin → email → phone
4. Subject lines: <60 chars for email/linkedin, null for phone/video
5. Timing: First touch = 0 days, subsequent touches = 2-3 days apart
6. Reference SPECIFIC pain points from persona mappings in Part 1 (not generic)

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEQUENCE STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each sequence must have:
- name: "{{persona_name}} Outreach Sequence"
- persona_name: {{exact_persona_name_from_input}}
- objective: One clear sentence describing sequence goal
- total_touches: 4-6
- duration_days: 10-21 (last touch's timing_days)
- touches: Array of touchpoint objects

Each touch must have:
- sort_order: Sequential number (1, 2, 3...)
- touch_type: "email" | "linkedin" | "phone" | "video"
- timing_days: Days after sequence start (CUMULATIVE: 0, 3, 6, 9, 14...)
- objective: Touch goal (1 sentence)
- subject_line: For email/linkedin (5-8 words), null for phone/video
- content_suggestion: Message body (3-5 sentences, 100-200 words)
- hints: Personalization tips (1-2 sentences) or null

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEQUENCE STRATEGY BY TIER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOOD vs BAD EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLETE SEQUENCE EXAMPLE (5 touches, tier_1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOUCH STRUCTURE TEMPLATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Touch 1 (timing_days: 0, Email): Brief intro + 1 specific pain point from Part 1 mappings
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSONAS FOR OUTREACH CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{compact_personas_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
          "pain_point": "string (1-2 sentences, <300 chars)",
          "value_proposition": "string (1-2 sentences, <300 chars, product integrated)"
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before returning, verify:

PART 1 (Mappings):
✓ Each persona has 3-10 mappings
✓ Pain points are <300 chars, 1-2 sentences
✓ Value props are <300 chars, 1-2 sentences
✓ Value props include product name naturally integrated
✓ Mappings are relevant to persona's role/industry/size

PART 2 (Sequences):
✓ {persona_count} sequences (one per persona)
✓ Each sequence has 4-6 touches
✓ sort_order is 1, 2, 3... (sequential)
✓ First touch: timing_days = 0 (always)
✓ Subsequent touches: timing_days MUST be cumulative (each touch = previous + 2-3 days)
  * Example: Touch 1 (0), Touch 2 (3), Touch 3 (6), Touch 4 (9) - NOT all touches with same timing_days
✓ timing_days values must increase sequentially (0 < touch2 < touch3 < touch4...)
✓ subject_line present for email/linkedin, null for phone/video
✓ Content references specific pain points from Part 1 mappings (not generic)
✓ duration_days = last touch's timing_days (NOT sum of all touches)
✓ duration_days matches tier requirements (tier_1: 14-21, tier_2: 12-14, tier_3: 10)

**CRITICAL:** Generate mappings and sequences for ALL {persona_count} personas provided."""
    
    def _build_compact_personas_for_outreach(self, personas: List[Dict]) -> str:
        """
        Format personas data in a compact format for outreach section.
        This helps reduce token usage while maintaining necessary context.
        """
        sections = []
        
        for i, persona in enumerate(personas, 1):
            # Get first 5 roles
            roles = persona.get('job_titles', [])[:5]
            roles_count = len(persona.get('job_titles', []))
            roles_text = ', '.join(roles)
            if roles_count > 5:
                roles_text += f' (+{roles_count - 5} more)'
            
            # Build compact section
            section = f"""
[{i}] {persona.get('persona_name', 'Unknown')}
    Roles: {roles_text}
    Profile: {persona.get('industry', 'N/A')} | {persona.get('company_size_range', 'N/A')} | Tier {persona.get('tier', 'N/A')}
"""
            sections.append(section)
        
        return "\n".join(sections)
    
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

