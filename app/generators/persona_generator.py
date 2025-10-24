# generators/persona_generator.py
"""
Persona generator for creating detailed buyer personas
"""
from .base_generator import BaseGenerator
from typing import Dict
import json
import logging

logger = logging.getLogger(__name__)

class PersonaGenerator(BaseGenerator):
    """Persona generation with tier classification"""
    
    def get_system_message(self) -> str:
      return """You are a B2B sales intelligence expert specializing in enterprise buyer persona identification.

CRITICAL INSTRUCTIONS FOR FIELD HANDLING:

1. DIRECTLY INFERABLE FIELDS (from company data - MUST be filled):
   - name, tier, job_title, industry, department, location, company_size
   - These MUST match or derive from the provided company data
   - Never use null for these fields

2. ROLE-BASED INFERABLE FIELDS (from industry standards - MUST be filled):
   - description, decision_power, communication_preferences
   - Generate these based on the role's typical responsibilities in this industry and company size
   - Use industry best practices and common patterns for this role
   - Even if specific details aren't in the data, provide realistic role-appropriate content

3. EVIDENCE-BASED FIELDS (requires reference from data - nullable):
   - pain_points: Only include if you can infer from the provided company data
   - Must be based on actual information in the context (e.g., news about challenges, company initiatives, industry trends mentioned)
   - If the data doesn't provide evidence of specific pain points, use null or empty array
   - Do NOT fabricate pain points based on generic role assumptions

4. CONTACT FIELDS (specific to individual - nullable):
   - email, phone, linkedin_url
   - Only fill if explicitly found in the provided data
   - Use null if not found - do NOT fabricate contact information

PERSONA GENERATION APPROACH:
- For company-level fields: Extract from provided data
- For role-level fields: Use your knowledge of standard responsibilities for that role
- For pain_points: Only include if evidence exists in the provided data
- For contact fields: Only use if explicitly provided
"""

    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
      generate_count = kwargs.get('generate_count', 3)
        
      return f"""Based on the following company information about {company_name}:

COMPANY DATA:
{context}

Generate exactly {generate_count} buyer personas ranked by purchasing influence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL: FIELD NAMING AND AUTO-INCREMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. company_size field MUST equal company.size for ALL personas
   Example: If company.size = 70000, then EVERY persona's company_size = 70000


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELD REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GROUP 1: COMPANY-DERIVED FIELDS (MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

These MUST be extracted/derived from the company data above:

- name: Role title (e.g., "Chief Financial Officer")
- tier: "tier_1" | "tier_2" | "tier_3" (based on budget authority)
- job_title: Standard title for this role
- industry: Extract from company data (MUST match company.industry)
- department: Standard department for this role
- location: Use company headquarters (MUST match company.location)
- company_size: Company employee count (MUST match company.size EXACTLY)
  CRITICAL: If company.size = 70000, then company_size = 70000
  NEVER use null

RULE: These fields MUST be consistent across all personas and match the company object.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GROUP 2: ROLE-BASED FIELDS (MANDATORY - USE PROFESSIONAL KNOWLEDGE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate these based on typical responsibilities for this role at this company size/industry:

A. description (TEXT - 2-3 sentences):
   - Describe standard responsibilities for this role
   - Tailor to company size (e.g., 70k employees = enterprise-scale challenges)
   - Tailor to industry (e.g., SaaS = subscription management focus)

B. decision_power (ENUM - pick one):
   - "budget_owner": Final approver (typically tier_1)
   - "influencer": Strong voice, controls dept budget (typically tier_2)
   - "recommender": Evaluates and recommends (typically tier_2/3)
   - "implementer": Daily user, provides feedback (typically tier_3)


D. communication_preferences (JSONB OBJECT - MANDATORY - NEVER EMPTY):
   CRITICAL: This field MUST ALWAYS be filled with realistic, role-appropriate content
   DO NOT leave channels, content_format, or meeting_style empty
   Generate based on B2B sales best practices for this seniority level
   
   Structure (ALL sub-fields required and must have content):
   {{
     "channels": [
       {{"type": "email", "frequency": "bi-weekly", "note": "Specific preference"}},
       {{"type": "phone", "frequency": "monthly", "note": "Specific preference"}}
     ],
     "content_format": ["Format 1", "Format 2", "Format 3"],
     "meeting_style": ["Style 1", "Style 2"],
     "response_time": "Specific timeframe"
   }}
   
   GUIDELINES BY SENIORITY LEVEL:
   
   Tier 1 (C-Level Executives - CFO, CEO, CTO):
   {{
     "channels": [
       {{"type": "email", "frequency": "bi-weekly", "note": "Concise executive summaries with clear ROI focus"}},
       {{"type": "in-person", "frequency": "quarterly", "note": "Strategic planning sessions and board-level presentations"}},
       {{"type": "phone", "frequency": "monthly", "note": "Scheduled calls only, no cold calls"}}
     ],
     "content_format": [
       "One-page executive summaries with financial impact",
       "ROI models and TCO analysis",
       "Board-level presentations with strategic implications",
       "Peer references from other Fortune 500 C-suite executives"
     ],
     "meeting_style": [
       "30-minute scheduled video calls with pre-read materials sent 48 hours in advance",
       "In-person meetings for strategic decisions over $500K",
       "Quarterly business reviews with quantitative performance metrics"
     ],
     "response_time": "3-5 business days for standard inquiries, same-day for board-level strategic priorities"
   }}
   
   Tier 2 (VPs and Directors):
   {{
     "channels": [
       {{"type": "email", "frequency": "weekly", "note": "Detailed updates with technical depth welcome"}},
       {{"type": "video call", "frequency": "bi-weekly", "note": "Flexible scheduling for deep-dive sessions"}},
       {{"type": "linkedin", "frequency": "monthly", "note": "Industry insights and relevant case studies"}}
     ],
     "content_format": [
       "Detailed technical documentation and architecture diagrams",
       "Product demonstrations and hands-on trials",
       "Case studies from similar-sized companies in the same industry",
       "Implementation roadmaps and integration guides"
     ],
     "meeting_style": [
       "45-60 minute video calls for comprehensive product walkthroughs",
       "Working sessions with technical teams for proof-of-concept",
       "Quarterly roadmap alignment meetings"
     ],
     "response_time": "1-2 business days for inquiries, same-day for urgent technical issues"
   }}
   
   Tier 3 (Managers and Individual Contributors):
   {{
     "channels": [
       {{"type": "email", "frequency": "as-needed", "note": "Quick, actionable updates preferred"}},
       {{"type": "slack", "frequency": "daily", "note": "Best for quick questions and real-time support"}},
       {{"type": "video call", "frequency": "weekly", "note": "For detailed implementation discussions"}}
     ],
     "content_format": [
       "Step-by-step implementation guides and documentation",
       "Video tutorials and screen-sharing demos",
       "Technical specifications and API documentation",
       "Quick reference cards and troubleshooting guides"
     ],
     "meeting_style": [
       "30-minute hands-on working sessions",
       "Screen-sharing demonstrations with live Q&A",
       "Weekly sync-ups during implementation phases"
     ],
     "response_time": "Same day or within 24 hours for operational questions"
   }}
   
   RULE: Base communication preferences on B2B sales best practices for this role level.
   NEVER leave any sub-field empty - generate realistic, role-appropriate content.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GROUP 3: EVIDENCE-BASED FIELDS (NULLABLE - REQUIRES DATA REFERENCE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A. pain_points (ARRAY or NULL):
   - ONLY include if you can infer pain points from the provided company data
   - Valid sources of evidence:
     * News articles mentioning company challenges
     * Company statements about initiatives or transformations
     * Industry trends explicitly mentioned in the data
     * Specific company metrics or problems referenced
   - If no evidence in data: use null
   - Do NOT generate generic pain points based only on role/industry assumptions
   
   Examples of when to include pain_points:
   ✓ Data says: "Company is consolidating vendors" → pain_point: "Vendor sprawl management"
   ✓ Data says: "Facing compliance challenges" → pain_point: "Meeting regulatory requirements"
   ✓ Data says: "Rapid growth to 70k employees" → pain_point: "Scaling processes for enterprise size"
   
   Examples of when to use null:
   ✗ Data only says: "Salesforce, 70k employees, SaaS" → pain_points: null
   ✗ No specific challenges mentioned → pain_points: null

RULE: If you cannot point to specific evidence in the provided data, use null.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GROUP 4: CONTACT FIELDS (NULLABLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Only fill if explicitly found in provided data:

- email: null (unless found in data)
- phone: null (unless found in data)
- linkedin_url: null (unless found in data)

RULE: Do NOT generate or guess contact information. Use null if not provided.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT JSON STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "company": {{
    "name": "{company_name}",
    "size": 70000,
    "industry": "SaaS / CRM",
    "location": "San Francisco, CA, USA",
    "domain": "salesforce.com"
  }},
  "personas": [
    {{
      "name": "Chief Financial Officer",
      "tier": "tier_1",
      "job_title": "Chief Financial Officer (CFO)",
      "industry": "SaaS / CRM",
      "department": "Finance",
      "location": "San Francisco, CA, USA",
      "company_size": 70000,
      "description": "Senior executive responsible for financial strategy, capital allocation, and approval of major technology investments at enterprise scale.",
      "decision_power": "budget_owner",
      "communication_preferences": {{
        "channels": [
          {{"type": "email", "frequency": "bi-weekly", "note": "Concise executive summaries with ROI focus"}},
          {{"type": "in-person", "frequency": "quarterly", "note": "Strategic planning sessions"}},
          {{"type": "phone", "frequency": "monthly", "note": "Scheduled calls for high-priority items"}}
        ],
        "content_format": [
          "One-page executive summary with ROI projection",
          "Financial models showing 3-year TCO",
          "Peer references from Fortune 500 CFOs",
          "Board-level presentations"
        ],
        "meeting_style": [
          "30-minute scheduled video calls with pre-read materials",
          "In-person board-room presentations for deals >$1M",
          "Quarterly business reviews with quantitative metrics"
        ],
        "response_time": "3-5 business days for non-urgent, same-day for strategic priorities"
      }},
      "pain_points": null,
      "email": null,
      "phone": null,
      "linkedin_url": null
    }},
    {{
      "name": "VP of Information Technology",
      "tier": "tier_2",
      "job_title": "Vice President of Information Technology",
      "industry": "SaaS / CRM",
      "department": "Information Technology",
      "location": "San Francisco, CA, USA",
      "company_size": 70000,
      "description": "Senior technology leader responsible for IT strategy, infrastructure decisions, and vendor evaluation for enterprise-scale operations.",
      "decision_power": "influencer",
      "communication_preferences": {{
        "channels": [
          {{"type": "email", "frequency": "weekly", "note": "Detailed technical updates welcome"}},
          {{"type": "video call", "frequency": "bi-weekly", "note": "Flexible for technical deep-dives"}},
          {{"type": "linkedin", "frequency": "monthly", "note": "Industry best practices and case studies"}}
        ],
        "content_format": [
          "Technical documentation and architecture diagrams",
          "Product demonstrations and POC proposals",
          "Case studies from similar enterprise tech companies",
          "Integration roadmaps and security documentation"
        ],
        "meeting_style": [
          "45-60 minute technical walkthrough sessions",
          "Proof-of-concept working sessions with engineering team",
          "Quarterly technology strategy alignment meetings"
        ],
        "response_time": "1-2 business days"
      }},
      "pain_points": null,
      "email": null,
      "phone": null,
      "linkedin_url": null
    }},
    {{
      "name": "IT Manager, Infrastructure",
      "tier": "tier_3",
      "job_title": "IT Manager — Infrastructure & Operations",
      "industry": "SaaS / CRM",
      "department": "Information Technology",
      "location": "San Francisco, CA, USA",
      "company_size": 70000,
      "description": "Hands-on operational manager responsible for infrastructure deployment, vendor implementation, and day-to-day technical evaluation.",
      "decision_power": "implementer",
      "communication_preferences": {{
        "channels": [
          {{"type": "email", "frequency": "as-needed", "note": "Quick, actionable updates"}},
          {{"type": "slack", "frequency": "daily", "note": "Preferred for quick technical questions"}},
          {{"type": "video call", "frequency": "weekly", "note": "For implementation planning"}}
        ],
        "content_format": [
          "Step-by-step implementation guides",
          "Video tutorials and screen-share demos",
          "Technical specifications and API docs",
          "Troubleshooting guides and quick references"
        ],
        "meeting_style": [
          "30-minute hands-on working sessions",
          "Live demos with Q&A",
          "Weekly implementation sync-ups"
        ],
        "response_time": "Same day or within 24 hours"
      }},
      "pain_points": null,
      "email": null,
      "phone": null,
      "linkedin_url": null
    }}
  ],
  "tier_classification": {{
    "tier_1": ["0"],
    "tier_2": ["1"],
    "tier_3": ["2"]
  }}
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before returning, verify:
✓ company_size in ALL personas = company.size (e.g., all = 70000)
✓ communication_preferences has ALL 4 keys filled with content
✓ communication_preferences.channels has at least 2-3 items with type, frequency, and note
✓ communication_preferences.content_format has at least 3-4 items
✓ communication_preferences.meeting_style has at least 2-3 items
✓ communication_preferences.response_time is a specific timeframe (not just "2-3 business days")
✓ pain_points is null OR contains only evidence-based items from data
✓ All personas have matching industry/location from company data
✓ tier_classification contains correct persona indices

CRITICAL ERRORS TO AVOID:
company_size is null (MUST be a number matching company.size)
communication_preferences has empty arrays for channels/content_format/meeting_style
communication_preferences.channels missing type, frequency, or note fields
Fabricating pain_points without data evidence
Inconsistent size/location/industry across personas
"""
    
    def parse_response(self, response: str) -> Dict:
        try:
            logger.debug(f"RAW LLM RESPONSE: {response[:2000]}")
            data = json.loads(response)
            
            # Validate and clean the data
            personas = data.get("personas", [])
            for i, persona in enumerate(personas):
                logger.debug(f"BEFORE processing persona {i}: {persona}")
                
                # Ensure required fields
                if "name" not in persona:
                    persona["name"] = persona.get("job_title", f"Persona {i+1}")
                
                # Ensure tier is valid
                if persona.get("tier") not in ["tier_1", "tier_2", "tier_3"]:
                    persona["tier"] = "tier_3"
                
                # Only ensure pain_points and goals are lists, NOT communication_preferences
                for field in ["pain_points", "goals"]:
                    if field not in persona or not isinstance(persona[field], list):
                        persona[field] = []
                
                # Handle communication_preferences separately - preserve structure
                if "communication_preferences" not in persona:
                    persona["communication_preferences"] = {
                        "channels": [],
                        "content_format": [],
                        "meeting_style": [],
                        "response_time": "2-3 business days"
                    }
                elif isinstance(persona["communication_preferences"], list):
                    # Convert old list format to new structure
                    persona["communication_preferences"] = {
                        "channels": [],
                        "content_format": persona["communication_preferences"],
                        "meeting_style": [],
                        "response_time": "2-3 business days"
                    }
                
                logger.debug(f"AFTER processing persona {i}: {persona}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse persona JSON: {e}")
            return {
                "personas": [],
                "tier_classification": {"tier_1": [], "tier_2": [], "tier_3": []},
                "raw_response": response,
                "parse_error": str(e)
            }
