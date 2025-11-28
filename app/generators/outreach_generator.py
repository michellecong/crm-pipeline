"""
Outreach sequence generator for creating multi-touch sales cadences
"""
from .base_generator import BaseGenerator
from typing import Dict, List
import json
import logging

logger = logging.getLogger(__name__)

class OutreachGenerator(BaseGenerator):
    """Generates multi-touch sales outreach sequences for personas"""
    
    def get_system_message(self) -> str:
        return """You are an expert B2B sales strategist specializing in enterprise outbound sequences.

Your task is to design multi-touch outreach sequences that:
- Build rapport through value-first communications
- Reference specific pain points and solutions
- Progress naturally from awareness to conversation
- Mix channels strategically (email, LinkedIn, phone, video)
- Respect prospect time with clear, concise messaging

You understand that modern sales requires providing value before asking for anything."""

    def _build_compact_personas(self, personas_with_mappings: List[Dict]) -> str:
        """
        Format personas data in a compact, token-efficient format.
        
        Optimizations:
        - Shows only top 3 pain points (most relevant)
        - Truncates long text to 100 chars
        - Shows only first 5 target roles
        - Removes excessive formatting
        """
        sections = []
        
        for i, persona in enumerate(personas_with_mappings, 1):
            # Get top 3 mappings
            mappings = persona.get('mappings', [])[:3]
            
            # Format mappings compactly
            if mappings:
                mappings_text = "\n".join([
                    f"  {j}. {m.get('pain_point', '')[:100]}...\n     → {m.get('value_proposition', '')[:100]}..."
                    for j, m in enumerate(mappings, 1)
                ])
            else:
                mappings_text = "  No mappings available"
            
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
    
    Top Pain Points & Solutions:
{mappings_text}
"""
            sections.append(section)
        
        return "\n".join(sections)

    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
        personas_with_mappings = kwargs.get('personas_with_mappings', [])
        
        if not personas_with_mappings:
            return "Error: No personas with mappings provided"
        
        # Build compact personas section
        personas_section = self._build_compact_personas(personas_with_mappings)
        
        return f"""Create {len(personas_with_mappings)} B2B outreach sequences.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULES (MUST FOLLOW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Generate EXACTLY {len(personas_with_mappings)} sequences (one per persona)
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSONAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{personas_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL: Return ONLY raw JSON. No markdown, no ```json blocks, no explanations.

WRONG:
```json
{{"sequences": [...]}}
```

CORRECT:
{{"sequences": [...]}}

Your response must start with {{ and end with }}

VALIDATION BEFORE RETURNING:
✓ {len(personas_with_mappings)} sequences (one per persona)
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

Generate sequences now."""

    def parse_response(self, response: str) -> Dict:
        """
        Parse LLM response into structured sequence data.
        
        Enhancements:
        - Strip markdown code blocks if present
        - Validate sequence count
        - Log warnings for missing fields
        """
        try:
            # Strip markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith('```'):
                # Remove ```json or ``` prefix and suffix
                lines = cleaned_response.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned_response = '\n'.join(lines)
            
            logger.debug(f"RAW LLM RESPONSE: {cleaned_response[:500]}...")
            
            # Parse JSON
            data = json.loads(cleaned_response)
            
            sequences = data.get("sequences", [])
            logger.info(f"✓ Parsed {len(sequences)} outreach sequences")
            
            # Validation and logging
            for i, seq in enumerate(sequences, 1):
                seq_name = seq.get('name', 'Unknown')
                touches = seq.get('touches', [])
                duration = seq.get('duration_days', 0)
                
                logger.debug(f"  [{i}] {seq_name}: {len(touches)} touches, {duration} days")
                
                # Validate touches
                if not touches:
                    logger.warning(f"  ⚠️  Sequence '{seq_name}' has no touches")
                elif len(touches) < 4 or len(touches) > 6:
                    logger.warning(f"  ⚠️  Sequence '{seq_name}' has {len(touches)} touches (expected 4-6)")
                
                # Check for missing subject lines in email/linkedin
                for touch in touches:
                    touch_type = touch.get('touch_type')
                    subject_line = touch.get('subject_line')
                    sort_order = touch.get('sort_order', '?')
                    
                    if touch_type in ['email', 'linkedin'] and not subject_line:
                        logger.warning(f"  ⚠️  Touch {sort_order} ({touch_type}) missing subject_line in '{seq_name}'")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse outreach JSON: {e}")
            logger.debug(f"Response preview: {response[:1000]}")
            return {
                "sequences": [],
                "raw_response": response,
                "parse_error": str(e)
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing outreach response: {e}")
            logger.error(f"Response preview: {response[:500]}")
            return {
                "sequences": [],
                "error": str(e)
            }