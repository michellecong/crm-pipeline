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
        return """You are a B2B sales expert specializing in buyer persona identification and classification. 
Your task is to identify key decision-makers and stakeholders, classifying each into three tiers:
- tier_1: C-level executives with direct budget control (CEO, CTO, CFO, etc.)
- tier_2: VPs and directors who influence decisions (VP Sales, Director of Marketing, etc.)
- tier_3: Managers and individual contributors (Sales Manager, Marketing Manager, etc.)

Prioritize personas by proximity to budget decisions. Return structured JSON format."""
    
    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
        generate_count = kwargs.get('generate_count', 3)
        
        return f"""Based on the following company information about {company_name}:

COMPANY DATA:
{context}

Generate {generate_count} detailed buyer personas. For each persona, include:

1. **Basic Information:**
   - name: Person's name (if inferable) or descriptive role title
   - tier: Classification as "tier_1", "tier_2", or "tier_3"
   - job_title: Specific job title
   - industry: Company's industry
   - department: Department/function
   - location: Geographic location (if inferable)
   - company_size: Company size (number of employees)

2. **AI-Generated Insights:**
   - description: Detailed description of the persona's role and responsibilities
   - decision_power: Level of decision-making authority
   - pain_points: Key challenges they face
   - goals: Their primary objectives
   - communication_preferences: How they prefer to be contacted

Return as JSON with this structure:
{{
    "personas": [
        {{
            "name": "VP of Sales",
            "tier": "tier_2",
            "job_title": "Vice President of Sales",
            "industry": "Technology",
            "department": "Sales",
            "location": "San Francisco, CA",
            "company_size": 1000,
            "description": "Senior sales executive responsible for driving revenue growth and managing the sales team. Has significant influence over purchasing decisions and works closely with C-level executives.",
            "decision_power": "influencer",
            "pain_points": ["Lead quality", "Sales efficiency", "Team performance"],
            "goals": ["Increase revenue", "Improve team performance", "Streamline processes"],
            "communication_preferences": ["Email", "LinkedIn", "Phone"]
        }}
    ],
    "tier_classification": {{
        "tier_1": ["persona_1"],
        "tier_2": ["persona_2", "persona_3"],
        "tier_3": ["persona_4", "persona_5"]
    }}
}}"""
    
    def parse_response(self, response: str) -> Dict:
        try:
            # Clean response content, remove markdown code block markers
            cleaned_response = response.strip()
            
            # Remove ```json and ``` markers
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]   # Remove ```
            
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            
            cleaned_response = cleaned_response.strip()
            
            # Try to parse JSON
            data = json.loads(cleaned_response)
            
            # Validate and clean the data
            personas = data.get("personas", [])
            for i, persona in enumerate(personas):
                # Ensure required fields
                if "name" not in persona:
                    persona["name"] = persona.get("job_title", f"Persona {i+1}")
                
                # Ensure tier is valid
                if persona.get("tier") not in ["tier_1", "tier_2", "tier_3"]:
                    persona["tier"] = "tier_3"
                
                # Ensure arrays are lists
                for field in ["pain_points", "goals", "communication_preferences"]:
                    if field not in persona or not isinstance(persona[field], list):
                        persona[field] = []
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse persona JSON: {e}")
            logger.error(f"Raw response: {response[:500]}...")
            return {
                "personas": [],
                "tier_classification": {"tier_1": [], "tier_2": [], "tier_3": []},
                "raw_response": response,
                "parse_error": str(e)
            }
