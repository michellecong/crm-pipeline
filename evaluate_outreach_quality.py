#!/usr/bin/env python3
"""
Outreach Quality Evaluation Script

Evaluates the quality of Outreach Sequences, including:
1. Sequence structure quality (number of touches, duration, timing correctness)
2. Touch type diversity (distribution of email, linkedin, phone)
3. Content quality (subject line length, content personalization, pain point references)
4. Match with Persona/Mappings
5. Sequence coherence and progression

Supports two evaluation modes:
- Traditional mode (default): Based on rules and pattern matching
- LLM mode (--use-llm): Uses LLM for semantic understanding and intelligent evaluation
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except (ImportError, ValueError):
    HAS_PANDAS = False
    pd = None

# Try to import LLM service
try:
    import sys
    current_file = Path(__file__).absolute()
    project_root = current_file.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from app.services.llm_service import LLMService
    HAS_LLM = True
except (ImportError, Exception):
    HAS_LLM = False


class OutreachQualityEvaluator:
    """Class for evaluating Outreach Sequence quality"""
    
    def __init__(self, evaluation_dir: Path, use_llm: bool = False):
        self.evaluation_dir = evaluation_dir
        self.use_llm = use_llm and HAS_LLM
        
        # Initialize LLM service (if enabled)
        if self.use_llm:
            try:
                self.llm_service = LLMService()
                print("✅ LLM evaluation mode enabled")
            except Exception as e:
                print(f"⚠️  LLM service initialization failed: {e}, will use traditional evaluation mode")
                self.use_llm = False
    
    def load_outreach_and_mappings(self, company_name: str, architecture: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Load outreach sequences, mappings, and personas for a company under a specific architecture"""
        company_base_dir = self.evaluation_dir / company_name
        
        # First try exact match
        company_dir = company_base_dir / architecture
        if not company_dir.exists():
            # If exact match fails, try case-insensitive match
            if company_base_dir.exists():
                for subdir in company_base_dir.iterdir():
                    if subdir.is_dir() and subdir.name.lower() == architecture.lower():
                        company_dir = subdir
                        break
                else:
                    return [], [], []
            else:
                return [], [], []
        
        sequences_data = []
        mappings_data = []
        personas_data = []
        
        # Load all JSON files
        for json_file in company_dir.glob("*.json"):
            filename = json_file.stem.lower()
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                if "outreach" in filename or "sequence" in filename:
                    # Outreach file
                    if "result" in content and "sequences" in content["result"]:
                        sequences_data = content["result"]["sequences"]
                elif "mapping" in filename:
                    # Mappings file
                    if "result" in content and "personas_with_mappings" in content["result"]:
                        mappings_data = content["result"]["personas_with_mappings"]
                elif "persona" in filename and "mapping" not in filename:
                    # Standalone personas file
                    if "result" in content and "personas" in content["result"]:
                        personas_data = content["result"]["personas"]
                elif "two_stage" in filename or "three_stage" in filename:
                    # Consolidated file
                    if "result" in content:
                        if "sequences" in content["result"]:
                            sequences_data = content["result"]["sequences"]
                        if "personas_with_mappings" in content["result"]:
                            mappings_data = content["result"]["personas_with_mappings"]
                        if "personas" in content["result"]:
                            personas_data = content["result"]["personas"]
                            
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
        
        return sequences_data, mappings_data, personas_data
    
    def evaluate_sequence_structure(self, sequence: Dict) -> Dict:
        """Evaluate sequence structure quality"""
        total_touches = sequence.get("total_touches", 0)
        duration_days = sequence.get("duration_days", 0)
        touches = sequence.get("touches", [])
        
        # 1. Touches count check (4-6 is ideal)
        touches_count_valid = 4 <= total_touches <= 6
        touches_count_score = 1.0 if touches_count_valid else (0.5 if 3 <= total_touches <= 7 else 0.0)
        
        # 2. Duration check (10-21 days is ideal)
        duration_valid = 10 <= duration_days <= 21
        duration_score = 1.0 if duration_valid else (0.5 if 7 <= duration_days <= 25 else 0.0)
        
        # 3. Timing check
        timing_valid = True
        timing_issues = []
        prev_timing = -1
        
        for i, touch in enumerate(touches):
            timing = touch.get("timing_days", -1)
            sort_order = touch.get("sort_order", i + 1)
            
            # First touch must be 0
            if i == 0 and timing != 0:
                timing_valid = False
                timing_issues.append(f"Touch {sort_order}: First touch timing_days should be 0, but is {timing}")
            
            # Timing should be increasing
            if i > 0 and timing <= prev_timing:
                timing_valid = False
                timing_issues.append(f"Touch {sort_order}: timing_days ({timing}) should be greater than previous ({prev_timing})")
            
            # Timing interval should be 2-3 days (except first)
            if i > 0:
                interval = timing - prev_timing
                if not (2 <= interval <= 3):
                    timing_issues.append(f"Touch {sort_order}: Interval {interval} days, ideal is 2-3 days")
            
            prev_timing = timing
        
        timing_score = 1.0 if timing_valid and not timing_issues else max(0.0, 1.0 - len(timing_issues) * 0.2)
        
        # 4. Sort order check
        sort_order_valid = True
        for i, touch in enumerate(touches):
            expected_order = i + 1
            actual_order = touch.get("sort_order", 0)
            if actual_order != expected_order:
                sort_order_valid = False
                break
        
        sort_order_score = 1.0 if sort_order_valid else 0.5
        
        # 5. Last touch timing should equal duration_days
        last_timing_match = False
        if touches:
            last_touch = touches[-1]
            last_timing = last_touch.get("timing_days", 0)
            if last_timing == duration_days:
                last_timing_match = True
        
        duration_match_score = 1.0 if last_timing_match else 0.5
        
        overall_structure_score = (
            touches_count_score * 0.2 +
            duration_score * 0.2 +
            timing_score * 0.3 +
            sort_order_score * 0.15 +
            duration_match_score * 0.15
        )
        
        return {
            "touches_count": total_touches,
            "touches_count_valid": touches_count_valid,
            "touches_count_score": touches_count_score,
            "duration_days": duration_days,
            "duration_valid": duration_valid,
            "duration_score": duration_score,
            "timing_valid": timing_valid,
            "timing_issues": timing_issues,
            "timing_score": timing_score,
            "sort_order_valid": sort_order_valid,
            "sort_order_score": sort_order_score,
            "last_timing_match": last_timing_match,
            "duration_match_score": duration_match_score,
            "overall_structure_score": overall_structure_score
        }
    
    def evaluate_touch_diversity(self, sequence: Dict) -> Dict:
        """Evaluate touch type diversity"""
        touches = sequence.get("touches", [])
        touch_types = [touch.get("touch_type", "").lower() for touch in touches]
        
        # Count each type
        type_counts = {}
        for touch_type in touch_types:
            type_counts[touch_type] = type_counts.get(touch_type, 0) + 1
        
        # Ideal distribution: should have email, linkedin, phone
        has_email = "email" in touch_types
        has_linkedin = "linkedin" in touch_types
        has_phone = "phone" in touch_types or "video" in touch_types
        
        # Diversity score
        diversity_score = 0.0
        if has_email:
            diversity_score += 0.3
        if has_linkedin:
            diversity_score += 0.3
        if has_phone:
            diversity_score += 0.4
        
        # Check for reasonable type distribution
        # Ideal: email most, linkedin second, phone least
        email_count = touch_types.count("email")
        linkedin_count = touch_types.count("linkedin")
        phone_count = touch_types.count("phone") + touch_types.count("video")
        
        distribution_score = 1.0
        if email_count < linkedin_count:
            distribution_score -= 0.2  # Email should be most
        if phone_count > email_count:
            distribution_score -= 0.3  # Phone should not be more than email
        
        # Check if phone/video is at the end
        last_touch_type = touch_types[-1] if touch_types else ""
        phone_at_end = last_touch_type in ["phone", "video"]
        phone_placement_score = 1.0 if phone_at_end else 0.7
        
        overall_diversity_score = (
            diversity_score * 0.5 +
            distribution_score * 0.3 +
            phone_placement_score * 0.2
        )
        
        return {
            "touch_types": touch_types,
            "type_counts": type_counts,
            "has_email": has_email,
            "has_linkedin": has_linkedin,
            "has_phone": has_phone,
            "diversity_score": diversity_score,
            "distribution_score": distribution_score,
            "phone_placement_score": phone_placement_score,
            "overall_diversity_score": overall_diversity_score
        }
    
    def evaluate_content_quality(self, sequence: Dict, mappings: List[Dict] = None) -> Dict:
        """Evaluate content quality"""
        touches = sequence.get("touches", [])
        persona_name = sequence.get("persona_name", "")
        
        # Create pain points set (for checking references)
        pain_points = set()
        if mappings:
            for mapping_group in mappings:
                if mapping_group.get("persona_name") == persona_name:
                    for mapping in mapping_group.get("mappings", []):
                        pain_point = mapping.get("pain_point", "")
                        if pain_point:
                            pain_points.add(pain_point.lower())
        
        touch_scores = []
        subject_line_issues = []
        content_issues = []
        pain_point_references = 0
        
        for touch in touches:
            touch_type = touch.get("touch_type", "").lower()
            subject_line = touch.get("subject_line", "")
            content = touch.get("content_suggestion", "")
            
            touch_score = 1.0
            
            # 1. Subject line check
            if touch_type in ["email", "linkedin"]:
                if not subject_line:
                    subject_line_issues.append(f"Touch {touch.get('sort_order')}: {touch_type} missing subject_line")
                    touch_score -= 0.2
                elif len(subject_line) > 60:
                    subject_line_issues.append(f"Touch {touch.get('sort_order')}: subject_line too long ({len(subject_line)} chars)")
                    touch_score -= 0.1
                elif len(subject_line) < 10:
                    subject_line_issues.append(f"Touch {touch.get('sort_order')}: subject_line too short ({len(subject_line)} chars)")
                    touch_score -= 0.1
            elif touch_type in ["phone", "video"]:
                if subject_line is not None:
                    subject_line_issues.append(f"Touch {touch.get('sort_order')}: {touch_type} should not have subject_line")
                    touch_score -= 0.1
            
            # 2. Content check
            if not content:
                content_issues.append(f"Touch {touch.get('sort_order')}: missing content_suggestion")
                touch_score -= 0.3
            else:
                # Check for personalization markers
                has_personalization = "{{first_name}}" in content or "{{company}}" in content
                if not has_personalization:
                    content_issues.append(f"Touch {touch.get('sort_order')}: missing personalization markers")
                    touch_score -= 0.1
                
                # Check for pain point references
                content_lower = content.lower()
                for pain_point in pain_points:
                    # Simple keyword matching
                    pain_keywords = set(pain_point.split()[:5])  # Take first 5 words
                    content_words = set(content_lower.split())
                    if len(pain_keywords & content_words) >= 2:  # At least 2 keywords match
                        pain_point_references += 1
                        break
                
                # Check content length
                if len(content) < 50:
                    content_issues.append(f"Touch {touch.get('sort_order')}: content too short")
                    touch_score -= 0.1
                elif len(content) > 500:
                    content_issues.append(f"Touch {touch.get('sort_order')}: content too long")
                    touch_score -= 0.05
            
            # 3. Objective check
            objective = touch.get("objective", "")
            if not objective:
                content_issues.append(f"Touch {touch.get('sort_order')}: missing objective")
                touch_score -= 0.1
            
            touch_scores.append(max(0.0, touch_score))
        
        avg_touch_score = sum(touch_scores) / len(touch_scores) if touch_scores else 0.0
        
        # Pain point reference rate
        pain_point_reference_rate = pain_point_references / len(touches) if touches else 0.0
        
        overall_content_score = (
            avg_touch_score * 0.7 +
            pain_point_reference_rate * 0.3
        )
        
        return {
            "avg_touch_score": avg_touch_score,
            "touch_scores": touch_scores,
            "subject_line_issues": subject_line_issues,
            "content_issues": content_issues,
            "pain_point_references": pain_point_references,
            "pain_point_reference_rate": pain_point_reference_rate,
            "overall_content_score": overall_content_score
        }
    
    def evaluate_sequence_coherence(self, sequence: Dict) -> Dict:
        """Evaluate sequence coherence and progression"""
        touches = sequence.get("touches", [])
        objective = sequence.get("objective", "")
        
        if len(touches) < 2:
            return {
                "coherence_score": 0.0,
                "progression_score": 0.0,
                "overall_coherence_score": 0.0,
                "issues": ["Sequence too short, cannot evaluate coherence"]
            }
        
        # 1. Check if each touch's objective is relevant
        objectives = [touch.get("objective", "") for touch in touches]
        sequence_objective_words = set(objective.lower().split())
        
        objective_relevance = []
        for i, touch_obj in enumerate(objectives):
            if touch_obj:
                touch_obj_words = set(touch_obj.lower().split())
                # Check for common keywords
                common_words = sequence_objective_words & touch_obj_words
                relevance = len(common_words) / max(len(sequence_objective_words), 1)
                objective_relevance.append(relevance)
            else:
                objective_relevance.append(0.0)
        
        coherence_score = sum(objective_relevance) / len(objective_relevance) if objective_relevance else 0.0
        
        # 2. Check progression (later touches should be deeper or more specific)
        progression_score = 0.5  # Default medium score
        # Simple heuristic: check if later touches contain more detail words
        detail_words = ["case", "example", "specific", "deep", "dive", "detailed", "approach"]
        progression_indicators = 0
        
        for i in range(1, len(touches)):
            prev_content = touches[i-1].get("content_suggestion", "").lower()
            curr_content = touches[i].get("content_suggestion", "").lower()
            
            prev_detail_count = sum(1 for word in detail_words if word in prev_content)
            curr_detail_count = sum(1 for word in detail_words if word in curr_content)
            
            if curr_detail_count > prev_detail_count:
                progression_indicators += 1
        
        if len(touches) > 1:
            progression_score = 0.5 + (progression_indicators / (len(touches) - 1)) * 0.5
        
        overall_coherence_score = (
            coherence_score * 0.6 +
            progression_score * 0.4
        )
        
        return {
            "coherence_score": coherence_score,
            "progression_score": progression_score,
            "overall_coherence_score": overall_coherence_score,
            "objective_relevance": objective_relevance
        }
    
    def llm_evaluate_sequence(
        self, 
        sequence: Dict, 
        persona: Dict, 
        mappings: List[Dict]
    ) -> Dict:
        """
        Deep evaluation using LLM
        
        Evaluation dimensions:
        1. Pain resonance: Does content truly address the core pain points of the target audience
        2. Value clarity: Can recipients quickly understand "what's in it for me"
        3. Sequence flow: Logical flow from touch 1 to the last touch
        4. Personalization: Is content customized for specific company/role
        5. Action drive: Is each touch's CTA clear and low-friction
        """
        if not self.use_llm:
            return {
                "error": "LLM evaluation not enabled",
                "scores": {},
                "strengths": [],
                "improvements": [],
                "overall_grade": "N/A",
                "reasoning": ""
            }
        
        try:
            # Build prompt
            prompt = self._build_llm_evaluation_prompt(sequence, persona, mappings)
            
            # Call LLM
            response = self.llm_service.generate(
                prompt=prompt,
                system_message=self._get_llm_system_message(),
                temperature=None,  # Use default value
                max_completion_tokens=2000
            )
            
            # Parse response
            evaluation_result = self._parse_llm_response(response.content)
            
            # Add metadata
            evaluation_result["llm_metadata"] = {
                "model": response.model,
                "tokens_used": response.total_tokens,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens
            }
            
            return evaluation_result
            
        except Exception as e:
            print(f"⚠️  LLM evaluation failed: {e}")
            return {
                "error": str(e),
                "scores": {},
                "strengths": [],
                "improvements": [],
                "overall_grade": "N/A",
                "reasoning": ""
            }
    
    def _get_llm_system_message(self) -> str:
        """Get system message for LLM evaluation"""
        return """You are a senior B2B sales coach and content evaluation expert. Your task is to evaluate the quality of outreach sequences and provide professional, objective, and actionable feedback from a sales effectiveness perspective.

Please carefully analyze the sequence content and evaluate its effectiveness in real sales scenarios. Your evaluation should:
1. Be based on B2B sales best practices
2. Consider the actual decision-making scenarios of target roles
3. Provide specific, actionable improvement suggestions
4. Be objective in scoring, avoiding being too lenient or strict

Always return results in JSON format."""
    
    def _build_llm_evaluation_prompt(
        self, 
        sequence: Dict, 
        persona: Dict, 
        mappings: List[Dict]
    ) -> str:
        """Build prompt for LLM evaluation"""
        # Extract pain points
        pain_points = []
        if mappings:
            for mapping_group in mappings:
                if mapping_group.get("persona_name") == sequence.get("persona_name", ""):
                    for mapping in mapping_group.get("mappings", []):
                        pain_point = mapping.get("pain_point", "")
                        if pain_point:
                            pain_points.append(pain_point)
        
        # Build touches information
        touches_info = []
        for touch in sequence.get("touches", []):
            touch_info = {
                "sort_order": touch.get("sort_order", 0),
                "touch_type": touch.get("touch_type", ""),
                "timing_days": touch.get("timing_days", 0),
                "subject_line": touch.get("subject_line", ""),
                "objective": touch.get("objective", ""),
                "content_suggestion": touch.get("content_suggestion", "")
            }
            touches_info.append(touch_info)
        
        prompt = f"""Evaluate the quality of the following outreach sequence.

## Target Audience Information
- Role Name: {persona.get('persona_name', 'N/A')}
- Role Description: {persona.get('description', 'N/A')}
- Industry: {persona.get('industry', 'N/A')}
- Company Size: {persona.get('company_size_range', 'N/A')}

## Core Pain Points
{chr(10).join(f"- {pp}" for pp in pain_points) if pain_points else "- No pain point information provided"}

## Sequence Information
- Sequence Name: {sequence.get('name', 'N/A')}
- Sequence Objective: {sequence.get('objective', 'N/A')}
- Total Touches: {sequence.get('total_touches', 0)}
- Duration: {sequence.get('duration_days', 0)} days

## Sequence Content
{json.dumps(touches_info, indent=2, ensure_ascii=False)}

---

Please score from the following 5 dimensions (0-10 points) and provide specific suggestions:

### 1. Pain Resonance (pain_resonance)
Does the content truly address the core pain points of the target audience?
- Does it demonstrate deep understanding of their challenges?
- Is the solution specific and credible?
- Does it avoid generic statements?

### 2. Value Clarity (value_clarity)
Can recipients quickly understand "what's in it for me"?
- Is value quantified (time, cost, efficiency)?
- Is there social proof (cases, customers)?
- Does the value proposition directly correspond to pain points?

### 3. Sequence Flow (sequence_flow)
Is the logical flow from touch 1 to the last touch natural?
- Is it building trust relationships?
- Does each touch have clear incremental value?
- Does the tone progress from light to heavy, from educational to sales?
- Are there any repetitive or contradictory information?

### 4. Personalization (personalization)
Is the content customized for specific company/role?
- Does it reference specific industry trends/challenges?
- Or is it just a generic template with names changed?
- Does it demonstrate real understanding of the customer's business?

### 5. Action Drive (cta_effectiveness)
Is each touch's CTA clear and low-friction?
- Does it fit decision-makers' time constraints?
- Is the next step clear and easy to execute?
- Does the CTA match the sequence stage?

---

Please return evaluation results in JSON format:

{{
  "scores": {{
    "pain_resonance": <0-10>,
    "value_clarity": <0-10>,
    "sequence_flow": <0-10>,
    "personalization": <0-10>,
    "cta_effectiveness": <0-10>
  }},
  "strengths": ["Specific strength 1", "Specific strength 2", ...],
  "improvements": ["Specific suggestion 1", "Specific suggestion 2", ...],
  "overall_grade": "<A+/A/A-/B+/B/B-/C+/C/C-/D/F>",
  "reasoning": "Overall evaluation reasoning (2-3 sentences)"
}}

Note:
- Scoring should be objective, 7-8 points indicates good, 9-10 points indicates excellent
- Strengths and improvement suggestions should be specific, avoid generic statements
- Overall grade should reflect comprehensive quality"""
        
        return prompt
    
    def _parse_llm_response(self, response_content: str) -> Dict:
        """Parse LLM response"""
        try:
            content = response_content.strip()
            
            # Try to extract JSON (may contain markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1].strip()
                    if content.startswith("json"):
                        content = content[4:].strip()
                    elif content.startswith("JSON"):
                        content = content[4:].strip()
            
            # Parse JSON
            result = json.loads(content)
            
            # Validate structure
            if "scores" not in result:
                raise ValueError("Response missing 'scores' field")
            
            # Ensure all required fields exist
            default_scores = {
                "pain_resonance": 0,
                "value_clarity": 0,
                "sequence_flow": 0,
                "personalization": 0,
                "cta_effectiveness": 0
            }
            
            for key in default_scores:
                if key not in result["scores"]:
                    result["scores"][key] = default_scores[key]
            
            # Ensure other fields exist
            if "strengths" not in result:
                result["strengths"] = []
            if "improvements" not in result:
                result["improvements"] = []
            if "overall_grade" not in result:
                result["overall_grade"] = "N/A"
            if "reasoning" not in result:
                result["reasoning"] = ""
            
            # Calculate composite score (0-1.0)
            scores = result["scores"]
            avg_score = sum(scores.values()) / len(scores) if scores else 0.0
            result["overall_score"] = avg_score / 10.0  # Convert to 0-1.0
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing failed: {e}")
            print(f"Response content: {response_content[:500]}")
            return {
                "error": f"JSON parsing failed: {str(e)}",
                "scores": {},
                "strengths": [],
                "improvements": [],
                "overall_grade": "N/A",
                "reasoning": "",
                "overall_score": 0.0
            }
        except Exception as e:
            print(f"⚠️  Error parsing response: {e}")
            return {
                "error": str(e),
                "scores": {},
                "strengths": [],
                "improvements": [],
                "overall_grade": "N/A",
                "reasoning": "",
                "overall_score": 0.0
            }
    
    def evaluate_all_sequences(self, company_name: str, architecture: str) -> Dict:
        """Evaluate all sequences for a company under a specific architecture"""
        sequences_data, mappings_data, personas_data = self.load_outreach_and_mappings(
            company_name, architecture
        )
        
        if not sequences_data:
            return {
                "company_name": company_name,
                "architecture": architecture,
                "error": "No sequences data found"
            }
        
        results = {
            "company_name": company_name,
            "architecture": architecture,
            "total_sequences": len(sequences_data),
            "evaluation_mode": "hybrid" if self.use_llm else "rule_based",
            "sequence_details": []
        }
        
        for sequence in sequences_data:
            persona_name = sequence.get("persona_name", "")
            
            # Find corresponding mappings and persona
            persona_mappings = None
            persona_data = None
            for mapping_group in mappings_data:
                if mapping_group.get("persona_name") == persona_name:
                    persona_mappings = [mapping_group]
                    break
            
            for persona in personas_data:
                if persona.get("persona_name") == persona_name:
                    persona_data = persona
                    break
            
            # First layer: Rule-based evaluation (fast, cheap)
            structure = self.evaluate_sequence_structure(sequence)
            diversity = self.evaluate_touch_diversity(sequence)
            content = self.evaluate_content_quality(sequence, persona_mappings)
            coherence = self.evaluate_sequence_coherence(sequence)
            
            # Calculate overall rule-based score
            rule_based_score = (
                structure["overall_structure_score"] * 0.25 +
                diversity["overall_diversity_score"] * 0.25 +
                content["overall_content_score"] * 0.25 +
                coherence["overall_coherence_score"] * 0.25
            )
            
            sequence_result = {
                "persona_name": persona_name,
                "sequence_name": sequence.get("name", ""),
                "rule_based_evaluation": {
                    "structure": structure,
                    "diversity": diversity,
                    "content": content,
                    "coherence": coherence,
                    "overall_score": rule_based_score
                }
            }
            
            # Second layer: LLM intelligent evaluation (deep, accurate)
            if self.use_llm and persona_data:
                llm_evaluation = self.llm_evaluate_sequence(
                    sequence, 
                    persona_data, 
                    persona_mappings if persona_mappings else []
                )
                sequence_result["llm_evaluation"] = llm_evaluation
                
                # Calculate hybrid score (rule-based 40% + LLM 60%)
                llm_score = llm_evaluation.get("overall_score", 0.0)
                combined_score = rule_based_score * 0.4 + llm_score * 0.6
                sequence_result["combined_score"] = combined_score
            else:
                sequence_result["combined_score"] = rule_based_score
            
            results["sequence_details"].append(sequence_result)
        
        # Calculate summary statistics
        if results["sequence_details"]:
            rule_scores = [s["rule_based_evaluation"]["overall_score"] for s in results["sequence_details"]]
            combined_scores = [s["combined_score"] for s in results["sequence_details"]]
            
            summary = {
                "avg_rule_based_score": sum(rule_scores) / len(rule_scores) if rule_scores else 0.0,
                "avg_combined_score": sum(combined_scores) / len(combined_scores) if combined_scores else 0.0
            }
            
            # Detailed statistics for rule-based evaluation
            structure_scores = [
                s["rule_based_evaluation"]["structure"]["overall_structure_score"]
                for s in results["sequence_details"]
            ]
            diversity_scores = [
                s["rule_based_evaluation"]["diversity"]["overall_diversity_score"]
                for s in results["sequence_details"]
            ]
            content_scores = [
                s["rule_based_evaluation"]["content"]["overall_content_score"]
                for s in results["sequence_details"]
            ]
            coherence_scores = [
                s["rule_based_evaluation"]["coherence"]["overall_coherence_score"]
                for s in results["sequence_details"]
            ]
            
            summary.update({
                "avg_structure_score": sum(structure_scores) / len(structure_scores) if structure_scores else 0.0,
                "avg_diversity_score": sum(diversity_scores) / len(diversity_scores) if diversity_scores else 0.0,
                "avg_content_score": sum(content_scores) / len(content_scores) if content_scores else 0.0,
                "avg_coherence_score": sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0
            })
            
            # LLM evaluation statistics (if enabled)
            if self.use_llm:
                llm_scores_list = []
                llm_pain_scores = []
                llm_value_scores = []
                llm_flow_scores = []
                llm_personalization_scores = []
                llm_cta_scores = []
                
                for s in results["sequence_details"]:
                    if "llm_evaluation" in s and "scores" in s["llm_evaluation"]:
                        scores = s["llm_evaluation"]["scores"]
                        llm_scores_list.append(s["llm_evaluation"].get("overall_score", 0.0))
                        llm_pain_scores.append(scores.get("pain_resonance", 0) / 10.0)
                        llm_value_scores.append(scores.get("value_clarity", 0) / 10.0)
                        llm_flow_scores.append(scores.get("sequence_flow", 0) / 10.0)
                        llm_personalization_scores.append(scores.get("personalization", 0) / 10.0)
                        llm_cta_scores.append(scores.get("cta_effectiveness", 0) / 10.0)
                
                if llm_scores_list:
                    summary["llm_evaluation"] = {
                        "avg_overall_score": sum(llm_scores_list) / len(llm_scores_list),
                        "avg_pain_resonance": sum(llm_pain_scores) / len(llm_pain_scores) if llm_pain_scores else 0.0,
                        "avg_value_clarity": sum(llm_value_scores) / len(llm_value_scores) if llm_value_scores else 0.0,
                        "avg_sequence_flow": sum(llm_flow_scores) / len(llm_flow_scores) if llm_flow_scores else 0.0,
                        "avg_personalization": sum(llm_personalization_scores) / len(llm_personalization_scores) if llm_personalization_scores else 0.0,
                        "avg_cta_effectiveness": sum(llm_cta_scores) / len(llm_cta_scores) if llm_cta_scores else 0.0
                    }
            
            results["summary"] = summary
        
        return results
    
    def compare_architectures(self, two_stage_results: Dict, three_stage_results: Dict = None, four_stage_results: Dict = None) -> Dict:
        """Compare outreach quality between two or three architectures"""
        comparison = {
            "company_name": two_stage_results.get("company_name", ""),
            "evaluation_mode": two_stage_results.get("evaluation_mode", "rule_based"),
            "comparison": {}
        }
        
        two_summary = two_stage_results.get("summary", {})
        three_summary = three_stage_results.get("summary", {}) if three_stage_results else {}
        four_summary = four_stage_results.get("summary", {}) if four_stage_results else {}
        
        has_two = bool(two_summary)
        has_three = bool(three_summary)
        has_four = bool(four_summary)
        
        if not has_two:
            comparison["comparison"]["error"] = "Missing 2-stage summary data"
            return comparison
        
        # 规则评估指标
        rule_metrics = {
            "structure_score": "avg_structure_score",
            "diversity_score": "avg_diversity_score",
            "content_score": "avg_content_score",
            "coherence_score": "avg_coherence_score",
            "rule_based_score": "avg_rule_based_score"
        }
        
        comparison_details = {}
        for metric_name, summary_key in rule_metrics.items():
            two_value = two_summary.get(summary_key, 0)
            three_value = three_summary.get(summary_key, 0) if has_three else None
            four_value = four_summary.get(summary_key, 0) if has_four else None
            
            values = {"two_stage": two_value}
            if three_value is not None:
                values["three_stage"] = three_value
            if four_value is not None:
                values["four_stage"] = four_value
            
            best_stage = max(values.items(), key=lambda x: x[1])[0] if values else "two_stage"
            
            comparison_details[metric_name] = {
                "two_stage": two_value,
                "three_stage": three_value,
                "four_stage": four_value,
                "best": best_stage
            }
        
        # 混合评分（如果启用 LLM）
        if two_summary.get("avg_combined_score") is not None:
            two_combined = two_summary.get("avg_combined_score", 0)
            three_combined = three_summary.get("avg_combined_score", 0) if has_three else None
            four_combined = four_summary.get("avg_combined_score", 0) if has_four else None
            
            values = {"two_stage": two_combined}
            if three_combined is not None:
                values["three_stage"] = three_combined
            if four_combined is not None:
                values["four_stage"] = four_combined
            
            best_stage = max(values.items(), key=lambda x: x[1])[0] if values else "two_stage"
            
            comparison_details["combined_score"] = {
                "two_stage": two_combined,
                "three_stage": three_combined,
                "four_stage": four_combined,
                "best": best_stage
            }
        
        # LLM 评估指标（如果启用）
        if two_summary.get("llm_evaluation"):
            llm_metrics = {
                "llm_pain_resonance": "avg_pain_resonance",
                "llm_value_clarity": "avg_value_clarity",
                "llm_sequence_flow": "avg_sequence_flow",
                "llm_personalization": "avg_personalization",
                "llm_cta_effectiveness": "avg_cta_effectiveness",
                "llm_overall_score": "avg_overall_score"
            }
            
            for metric_name, llm_key in llm_metrics.items():
                two_llm = two_summary.get("llm_evaluation", {}).get(llm_key, 0)
                three_llm = three_summary.get("llm_evaluation", {}).get(llm_key, 0) if has_three else None
                four_llm = four_summary.get("llm_evaluation", {}).get(llm_key, 0) if has_four else None
                
                values = {"two_stage": two_llm}
                if three_llm is not None:
                    values["three_stage"] = three_llm
                if four_llm is not None:
                    values["four_stage"] = four_llm
                
                best_stage = max(values.items(), key=lambda x: x[1])[0] if values else "two_stage"
                
                comparison_details[metric_name] = {
                    "two_stage": two_llm,
                    "three_stage": three_llm,
                    "four_stage": four_llm,
                    "best": best_stage
                }
        
        comparison["comparison"] = comparison_details
        return comparison


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate Outreach Sequences quality")
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM for intelligent evaluation (more flexible, but requires API calls)"
    )
    args = parser.parse_args()
    
    evaluation_dir = Path("data/Evaluation")
    
    if not evaluation_dir.exists():
        print(f"❌ Evaluation directory does not exist: {evaluation_dir}")
        return
    
    evaluator = OutreachQualityEvaluator(evaluation_dir, use_llm=args.use_llm)
    
    # Get all companies
    companies = [d.name for d in evaluation_dir.iterdir() if d.is_dir()]
    
    if not companies:
        print("❌ No company data found")
        return
    
    print(f"🚀 Starting Outreach Sequences quality evaluation...")
    print(f"📁 Evaluation directory: {evaluation_dir}")
    print(f"📊 Found {len(companies)} companies\n")
    
    all_results = []
    all_comparisons = []
    
    for company_name in companies:
        print(f"Evaluating {company_name}...")
        
        # Evaluate each architecture
        two_stage_results = evaluator.evaluate_all_sequences(company_name, "2 Stage")
        if "error" in two_stage_results:
            two_stage_results = evaluator.evaluate_all_sequences(company_name, "Two-Stage")
        if "error" in two_stage_results:
            two_stage_results = evaluator.evaluate_all_sequences(company_name, "2 stage")
        
        three_stage_results = evaluator.evaluate_all_sequences(company_name, "3 Stage")
        if "error" in three_stage_results:
            three_stage_results = evaluator.evaluate_all_sequences(company_name, "Three-Stage")
        if "error" in three_stage_results:
            three_stage_results = evaluator.evaluate_all_sequences(company_name, "3 stage")
        
        four_stage_results = evaluator.evaluate_all_sequences(company_name, "4 Stage")
        if "error" in four_stage_results:
            four_stage_results = evaluator.evaluate_all_sequences(company_name, "Four-Stage")
        if "error" in four_stage_results:
            four_stage_results = evaluator.evaluate_all_sequences(company_name, "4 stage")
        
        # Perform three-way comparison
        if "error" not in two_stage_results:
            comparison = evaluator.compare_architectures(
                two_stage_results,
                three_stage_results if "error" not in three_stage_results else None,
                four_stage_results if "error" not in four_stage_results else None
            )
            if "error" not in comparison.get("comparison", {}):
                all_comparisons.append(comparison)
        
        all_results.append({
            "company_name": company_name,
            "two_stage": two_stage_results,
            "three_stage": three_stage_results if "error" not in three_stage_results else None,
            "four_stage": four_stage_results if "error" not in four_stage_results else None
        })
    
    # Save results
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed results
    results_file = output_dir / f"outreach_quality_evaluation_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Detailed evaluation results saved to: {results_file}")
    
    # Save comparison results
    comparison_file = output_dir / f"outreach_quality_comparison_{timestamp}.json"
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(all_comparisons, f, indent=2, ensure_ascii=False)
    print(f"✅ Comparison results saved to: {comparison_file}")
    
    # Print summary
    print("\n" + "=" * 80)
    mode_text = "Hybrid evaluation (Rule + LLM)" if evaluator.use_llm else "Rule-based evaluation"
    print("Outreach Quality Evaluation Summary (2 Stage vs 3 Stage vs 4 Stage)")
    print(f"Evaluation mode: {mode_text}")
    print("=" * 80)
    
    for comparison in all_comparisons:
        company_name = comparison["company_name"]
        comp = comparison.get("comparison", {})
        eval_mode = comparison.get("evaluation_mode", "rule_based")
        
        if "error" in comp:
            print(f"\n⚠️  {company_name}: {comp['error']}")
            continue
        
        print(f"\n📊 {company_name}:")
        print("-" * 80)
        
        # Rule-based evaluation metrics
        print("\n【Rule-based Evaluation Metrics】")
        rule_metrics = ["structure_score", "diversity_score", "content_score", "coherence_score", "rule_based_score"]
        for metric_name in rule_metrics:
            if metric_name in comp:
                metric_data = comp[metric_name]
                if isinstance(metric_data, dict) and "two_stage" in metric_data:
                    two_val = metric_data["two_stage"]
                    three_val = metric_data.get("three_stage")
                    four_val = metric_data.get("four_stage")
                    best = metric_data.get("best", "two_stage")
                    
                    metric_display = {
                        "structure_score": "Structure Quality",
                        "diversity_score": "Diversity",
                        "content_score": "Content Quality",
                        "coherence_score": "Coherence",
                        "rule_based_score": "Rule-based Total Score"
                    }.get(metric_name, metric_name)
                    
                    print(f"\n  {metric_display}:")
                    print(f"    2 Stage: {two_val:.3f}")
                    if three_val is not None:
                        marker_3 = " ⭐" if best == "three_stage" else ""
                        print(f"    3 Stage: {three_val:.3f}{marker_3}")
                    if four_val is not None:
                        marker_4 = " ⭐" if best == "four_stage" else ""
                        print(f"    4 Stage: {four_val:.3f}{marker_4}")
                    print(f"    Best: {best.replace('_', ' ').title()}")
        
        # LLM evaluation metrics (if enabled)
        if "llm_overall_score" in comp:
            print("\n【LLM Intelligent Evaluation Metrics】")
            llm_metrics = [
                ("llm_pain_resonance", "Pain Resonance"),
                ("llm_value_clarity", "Value Clarity"),
                ("llm_sequence_flow", "Sequence Flow"),
                ("llm_personalization", "Personalization"),
                ("llm_cta_effectiveness", "CTA Effectiveness"),
                ("llm_overall_score", "LLM Total Score")
            ]
            
            for metric_name, metric_display in llm_metrics:
                if metric_name in comp:
                    metric_data = comp[metric_name]
                    if isinstance(metric_data, dict) and "two_stage" in metric_data:
                        two_val = metric_data["two_stage"]
                        three_val = metric_data.get("three_stage")
                        four_val = metric_data.get("four_stage")
                        best = metric_data.get("best", "two_stage")
                        
                        print(f"\n  {metric_display}:")
                        print(f"    2 Stage: {two_val:.3f}")
                        if three_val is not None:
                            marker_3 = " ⭐" if best == "three_stage" else ""
                            print(f"    3 Stage: {three_val:.3f}{marker_3}")
                        if four_val is not None:
                            marker_4 = " ⭐" if best == "four_stage" else ""
                            print(f"    4 Stage: {four_val:.3f}{marker_4}")
                        print(f"    Best: {best.replace('_', ' ').title()}")
        
        # Combined score (if enabled)
        if "combined_score" in comp:
            print("\n【Combined Score (Rule 40% + LLM 60%)】")
            metric_data = comp["combined_score"]
            if isinstance(metric_data, dict) and "two_stage" in metric_data:
                two_val = metric_data["two_stage"]
                three_val = metric_data.get("three_stage")
                four_val = metric_data.get("four_stage")
                best = metric_data.get("best", "two_stage")
                
                print(f"\n  Combined Score:")
                print(f"    2 Stage: {two_val:.3f}")
                if three_val is not None:
                    marker_3 = " ⭐" if best == "three_stage" else ""
                    print(f"    3 Stage: {three_val:.3f}{marker_3}")
                if four_val is not None:
                    marker_4 = " ⭐" if best == "four_stage" else ""
                    print(f"    4 Stage: {four_val:.3f}{marker_4}")
                print(f"    Best: {best.replace('_', ' ').title()}")


if __name__ == "__main__":
    main()

