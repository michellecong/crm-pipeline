#!/usr/bin/env python3
"""
Persona Quality Evaluation Script

从多个角度评估和对比 2 Stage vs 4 Stage 的 Persona 质量：
1. 产品关联度（Product Alignment）
2. 描述完整性（Description Completeness）
3. Job Titles 相关性和数量
4. 字段完整性（Field Completeness）
5. 行业和地理多样性（Diversity）
6. Generation Reasoning 质量
7. 一致性和准确性
"""
import json
import re
import csv
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter
from datetime import datetime

# Optional pandas import
try:
    import pandas as pd
    HAS_PANDAS = True
except (ImportError, ValueError):
    HAS_PANDAS = False
    pd = None


class PersonaQualityEvaluator:
    """评估 Persona 质量的类"""
    
    def __init__(self, evaluation_dir: Path):
        self.evaluation_dir = evaluation_dir
        
    def load_personas(self, company_name: str, architecture: str) -> tuple[List[Dict], Optional[Dict]]:
        """加载某个公司在某个架构下的 personas 和 products"""
        company_dir = self.evaluation_dir / company_name / architecture
        
        if not company_dir.exists():
            return [], None
        
        personas_data = []
        products_data = None
        
        # 加载所有JSON文件
        for json_file in company_dir.glob("*.json"):
            filename = json_file.stem.lower()
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                if "persona" in filename and "mapping" not in filename:
                    # 独立的 personas 文件（4 Stage）
                    if "result" in content and "personas" in content["result"]:
                        personas_data = content["result"]["personas"]
                    elif "personas" in content:
                        personas_data = content["personas"]
                elif "product" in filename:
                    # Products 文件
                    if "result" in content and "products" in content["result"]:
                        products_data = content["result"]["products"]
                    elif "products" in content:
                        products_data = content["products"]
                elif "two_stage" in filename:
                    # Two-Stage consolidated 文件
                    if "result" in content:
                        if "personas" in content["result"]:
                            personas_data = content["result"]["personas"]
                        if "products" in content.get("result", {}):
                            products_data = content["result"]["products"]
                elif "three_stage" in filename:
                    # Three-Stage consolidated 文件
                    if "result" in content:
                        # Three-Stage 可能有独立的 personas 文件，但 consolidated 文件中也有
                        # 优先使用独立的 personas 文件（如果已加载）
                        if not personas_data and "personas" in content["result"]:
                            personas_data = content["result"]["personas"]
                        # 也可以从 personas_with_mappings 中提取
                        if not personas_data and "personas_with_mappings" in content["result"]:
                            for pwm in content["result"]["personas_with_mappings"]:
                                persona = {
                                    "persona_name": pwm.get("persona_name"),
                                    "tier": pwm.get("tier"),
                                    "industry": pwm.get("industry"),
                                    "location": pwm.get("location"),
                                    "company_size_range": pwm.get("company_size_range"),
                                    "company_type": pwm.get("company_type"),
                                    "description": pwm.get("description"),
                                    "job_titles": pwm.get("job_titles", []),
                                }
                                if persona.get("persona_name"):
                                    personas_data.append(persona)
                        if "products" in content.get("result", {}):
                            products_data = content["result"]["products"]
                            
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
        
        return personas_data, products_data
    
    def evaluate_product_alignment(self, personas: List[Dict], products: Optional[List[Dict]]) -> Dict:
        """评估产品关联度"""
        if not products or len(products) == 0:
            return {
                "score": 0.0,
                "details": "No products data available",
                "personas_with_product_mentions": 0,
                "total_personas": len(personas)
            }
        
        # 提取产品名称和关键词
        product_names = [p.get("product_name", "") for p in products]
        product_keywords = set()
        for p in products:
            name = p.get("product_name", "").lower()
            description = p.get("description", "").lower()
            product_keywords.update(name.split())
            product_keywords.update(re.findall(r'\b\w+\b', description))
        
        # 检查每个 persona 的 description 中是否提及产品
        personas_with_mentions = 0
        mention_details = []
        
        for persona in personas:
            description = persona.get("description", "").lower()
            job_titles = [jt.lower() for jt in persona.get("job_titles", [])]
            
            # 检查是否提及产品名称或关键词
            mentions_product = False
            mentioned_products = []
            
            for product_name in product_names:
                if product_name.lower() in description:
                    mentions_product = True
                    mentioned_products.append(product_name)
            
            # 检查是否提及产品关键词
            for keyword in product_keywords:
                if len(keyword) > 4 and keyword in description:
                    mentions_product = True
                    break
            
            if mentions_product:
                personas_with_mentions += 1
            
            mention_details.append({
                "persona_name": persona.get("persona_name", ""),
                "mentions_product": mentions_product,
                "mentioned_products": mentioned_products
            })
        
        score = personas_with_mentions / len(personas) if personas else 0.0
        
        return {
            "score": score,
            "personas_with_product_mentions": personas_with_mentions,
            "total_personas": len(personas),
            "details": mention_details
        }
    
    def evaluate_description_completeness(self, personas: List[Dict]) -> Dict:
        """评估描述完整性 - 检查是否包含4个必需指标"""
        required_metrics = {
            "team_size": False,
            "deal_size": False,
            "sales_cycle": False,
            "stakeholders": False
        }
        
        completeness_scores = []
        metric_details = []
        
        for persona in personas:
            description = persona.get("description", "")
            metrics_found = {
                "team_size": bool(re.search(r'\d+[-–]\d+\s*(?:sales\s*)?(?:reps?|staff|people|employees|team)', description, re.I)),
                "deal_size": bool(re.search(r'\$[€£¥]?\s*\d+[KMB]?[-–]\$?[€£¥]?\s*\d+[KMB]?', description, re.I)),
                "sales_cycle": bool(re.search(r'\d+[-–]\d+\s*(?:month|week)', description, re.I)),
                "stakeholders": bool(re.search(r'\d+[-–]\d+\s*(?:stakeholder|decision\s*maker|buyer)', description, re.I))
            }
            
            score = sum(metrics_found.values()) / 4.0
            completeness_scores.append(score)
            
            metric_details.append({
                "persona_name": persona.get("persona_name", ""),
                "metrics_found": metrics_found,
                "score": score
            })
        
        avg_score = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0
        
        return {
            "average_score": avg_score,
            "personas_with_all_metrics": sum(1 for s in completeness_scores if s == 1.0),
            "total_personas": len(personas),
            "details": metric_details
        }
    
    def evaluate_job_titles_quality(self, personas: List[Dict]) -> Dict:
        """评估 Job Titles 的质量"""
        job_title_counts = []
        excluded_title_counts = []
        job_title_lengths = []
        
        for persona in personas:
            job_titles = persona.get("job_titles", [])
            excluded_titles = persona.get("excluded_job_titles", [])
            
            job_title_counts.append(len(job_titles))
            excluded_title_counts.append(len(excluded_titles))
            
            # 计算平均 job title 长度
            if job_titles:
                avg_length = sum(len(jt) for jt in job_titles) / len(job_titles)
                job_title_lengths.append(avg_length)
        
        return {
            "avg_job_titles_per_persona": sum(job_title_counts) / len(job_title_counts) if job_title_counts else 0.0,
            "avg_excluded_titles_per_persona": sum(excluded_title_counts) / len(excluded_title_counts) if excluded_title_counts else 0.0,
            "min_job_titles": min(job_title_counts) if job_title_counts else 0,
            "max_job_titles": max(job_title_counts) if job_title_counts else 0,
            "avg_job_title_length": sum(job_title_lengths) / len(job_title_lengths) if job_title_lengths else 0.0
        }
    
    def evaluate_field_completeness(self, personas: List[Dict]) -> Dict:
        """评估字段完整性"""
        required_fields = [
            'persona_name', 'tier', 'job_titles', 'excluded_job_titles',
            'industry', 'company_size_range', 'company_type',
            'location', 'description'
        ]
        
        completeness_scores = []
        field_presence = {field: 0 for field in required_fields}
        
        for persona in personas:
            present_fields = 0
            for field in required_fields:
                value = persona.get(field)
                if value is not None and value != "" and value != []:
                    present_fields += 1
                    field_presence[field] += 1
            
            score = present_fields / len(required_fields)
            completeness_scores.append(score)
        
        avg_score = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0
        
        # 计算每个字段的存在率
        field_presence_rate = {
            field: count / len(personas) if personas else 0.0
            for field, count in field_presence.items()
        }
        
        return {
            "average_completeness": avg_score,
            "personas_with_all_fields": sum(1 for s in completeness_scores if s == 1.0),
            "total_personas": len(personas),
            "field_presence_rate": field_presence_rate
        }
    
    def evaluate_diversity(self, personas: List[Dict]) -> Dict:
        """评估多样性"""
        industries = [p.get("industry", "Unknown") for p in personas]
        locations = [p.get("location", "Unknown") for p in personas]
        tiers = [p.get("tier", "Unknown") for p in personas]
        company_sizes = [p.get("company_size_range", "Unknown") for p in personas]
        
        return {
            "unique_industries": len(set(industries)),
            "unique_locations": len(set(locations)),
            "unique_company_sizes": len(set(company_sizes)),
            "industry_diversity_score": len(set(industries)) / len(personas) if personas else 0.0,
            "location_diversity_score": len(set(locations)) / len(personas) if personas else 0.0,
            "size_diversity_score": len(set(company_sizes)) / len(personas) if personas else 0.0,
            "tier_distribution": dict(Counter(tiers)),
            "industry_distribution": dict(Counter(industries)),
            "location_distribution": dict(Counter(locations))
        }
    
    def evaluate_generation_reasoning(self, company_name: str, architecture: str) -> Dict:
        """评估 Generation Reasoning 质量（仅适用于有 reasoning 的架构）"""
        company_dir = self.evaluation_dir / company_name / architecture
        
        if not company_dir.exists():
            return {"has_reasoning": False, "reasoning_length": 0}
        
        reasoning_text = None
        reasoning_length = 0
        
        # 查找包含 reasoning 的文件
        for json_file in company_dir.glob("*.json"):
            filename = json_file.stem.lower()
            
            if "persona" in filename and "mapping" not in filename:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    
                    if "result" in content and "generation_reasoning" in content["result"]:
                        reasoning_text = content["result"]["generation_reasoning"]
                        reasoning_length = len(reasoning_text) if reasoning_text else 0
                        break
                except Exception as e:
                    continue
        
        return {
            "has_reasoning": reasoning_text is not None,
            "reasoning_length": reasoning_length,
            "reasoning_mentions_products": "product" in reasoning_text.lower() if reasoning_text else False,
            "reasoning_mentions_crm": "crm" in reasoning_text.lower() if reasoning_text else False
        }
    
    def evaluate_persona_name_quality(self, personas: List[Dict]) -> Dict:
        """评估 Persona Name 质量"""
        name_lengths = []
        valid_format_count = 0
        
        # Persona name 格式: "[Geography] [Size] [Industry] - [Function]"
        format_pattern = re.compile(r'^.+?\s+.+?\s+.+?\s*-\s*.+$')
        
        for persona in personas:
            name = persona.get("persona_name", "")
            name_lengths.append(len(name))
            
            if format_pattern.match(name):
                valid_format_count += 1
        
        return {
            "avg_name_length": sum(name_lengths) / len(name_lengths) if name_lengths else 0.0,
            "names_within_limit": sum(1 for l in name_lengths if l <= 60),
            "names_over_limit": sum(1 for l in name_lengths if l > 60),
            "valid_format_count": valid_format_count,
            "total_personas": len(personas)
        }
    
    def evaluate_all(self, company_name: str) -> Dict:
        """评估某个公司的 2 Stage 和 4 Stage personas"""
        results = {
            "company_name": company_name,
            "two_stage": {},
            "four_stage": {}
        }
        
        # 评估 2 Stage
        two_stage_personas, two_stage_products = self.load_personas(company_name, "2 Stage")
        if not two_stage_personas:
            two_stage_personas, two_stage_products = self.load_personas(company_name, "Two-Stage")
        
        if two_stage_personas:
            results["two_stage"] = {
                "persona_count": len(two_stage_personas),
                "product_alignment": self.evaluate_product_alignment(two_stage_personas, two_stage_products),
                "description_completeness": self.evaluate_description_completeness(two_stage_personas),
                "job_titles_quality": self.evaluate_job_titles_quality(two_stage_personas),
                "field_completeness": self.evaluate_field_completeness(two_stage_personas),
                "diversity": self.evaluate_diversity(two_stage_personas),
                "persona_name_quality": self.evaluate_persona_name_quality(two_stage_personas),
                "generation_reasoning": self.evaluate_generation_reasoning(company_name, "2 Stage")
            }
        
        # 评估 4 Stage
        four_stage_personas, four_stage_products = self.load_personas(company_name, "4 Stage")
        if not four_stage_personas:
            four_stage_personas, four_stage_products = self.load_personas(company_name, "Four-Stage")
        
        if four_stage_personas:
            results["four_stage"] = {
                "persona_count": len(four_stage_personas),
                "product_alignment": self.evaluate_product_alignment(four_stage_personas, four_stage_products),
                "description_completeness": self.evaluate_description_completeness(four_stage_personas),
                "job_titles_quality": self.evaluate_job_titles_quality(four_stage_personas),
                "field_completeness": self.evaluate_field_completeness(four_stage_personas),
                "diversity": self.evaluate_diversity(four_stage_personas),
                "persona_name_quality": self.evaluate_persona_name_quality(four_stage_personas),
                "generation_reasoning": self.evaluate_generation_reasoning(company_name, "4 Stage")
            }
        
        return results
    
    def calculate_score(self, metric_name: str, two_value: float, four_value: float, 
                       two_reasoning: Dict = None, four_reasoning: Dict = None) -> Dict:
        """计算量化分数（0-100分）"""
        score = 0.0
        max_score = 100.0
        
        if metric_name == "generation_reasoning":
            # Generation Reasoning 评分（权重：40分）
            max_score = 40.0
            # 4 Stage 有 reasoning 得 40分，没有得 0分
            if four_reasoning and four_reasoning.get("has_reasoning", False):
                reasoning_length = four_reasoning.get("reasoning_length", 0)
                # 根据长度给分：1000+ 字符得满分，500-1000 得 30分，<500 得 20分
                if reasoning_length >= 1000:
                    score = 40.0
                elif reasoning_length >= 500:
                    score = 30.0
                elif reasoning_length > 0:
                    score = 20.0
                else:
                    score = 0.0
            else:
                score = 0.0
            
            return {
                "score": score,
                "max_score": max_score,
                "score_percentage": (score / max_score) * 100,
                "two_stage_has_reasoning": two_reasoning.get("has_reasoning", False) if two_reasoning else False,
                "four_stage_has_reasoning": four_reasoning.get("has_reasoning", False) if four_reasoning else False,
                "two_stage_reasoning_length": two_reasoning.get("reasoning_length", 0) if two_reasoning else 0,
                "four_stage_reasoning_length": four_reasoning.get("reasoning_length", 0) if four_reasoning else 0
            }
        
        elif metric_name == "avg_job_titles":
            # Job Titles 数量评分（权重：35分）
            max_score = 35.0
            # 基准：15个 job titles = 0分，每增加1个得2分，最多35分
            # 4 Stage 比 2 Stage 多多少，就给多少分（上限35分）
            difference = four_value - two_value
            if difference > 0:
                # 每多1个 job title 得 2分，最多35分
                score = min(difference * 2, 35.0)
            else:
                score = 0.0
            
            return {
                "score": score,
                "max_score": max_score,
                "score_percentage": (score / max_score) * 100,
                "two_stage": two_value,
                "four_stage": four_value,
                "difference": difference
            }
        
        elif metric_name == "persona_name_quality":
            # Persona Name 质量评分（权重：25分）
            max_score = 25.0
            # 基准：40字符 = 0分，每增加1字符得0.5分，最多25分
            # 4 Stage 比 2 Stage 长多少，就给多少分（上限25分）
            difference = four_value - two_value
            if difference > 0:
                # 每多1字符得 0.5分，最多25分
                score = min(difference * 0.5, 25.0)
            else:
                score = 0.0
            
            return {
                "score": score,
                "max_score": max_score,
                "score_percentage": (score / max_score) * 100,
                "two_stage": two_value,
                "four_stage": four_value,
                "difference": difference
            }
        
        return {
            "score": 0.0,
            "max_score": max_score,
            "score_percentage": 0.0
        }
    
    def calculate_absolute_score(self, architecture_data: Dict, architecture_name: str) -> Dict:
        """计算某个架构的绝对总分（基于相同的评分标准，包含所有指标）"""
        total_score = 0.0
        max_total_score = 100.0
        scores = {}
        
        # 1. Generation Reasoning（权重：15分）- 降低权重
        reasoning = architecture_data.get("generation_reasoning", {})
        if reasoning.get("has_reasoning", False):
            reasoning_length = reasoning.get("reasoning_length", 0)
            if reasoning_length >= 1000:
                reasoning_score = 15.0
            elif reasoning_length >= 500:
                reasoning_score = 12.0
            elif reasoning_length > 0:
                reasoning_score = 8.0
            else:
                reasoning_score = 0.0
        else:
            reasoning_score = 0.0
        
        scores["generation_reasoning"] = {
            "score": reasoning_score,
            "max_score": 15.0,
            "has_reasoning": reasoning.get("has_reasoning", False),
            "reasoning_length": reasoning.get("reasoning_length", 0)
        }
        total_score += reasoning_score
        
        # 2. Product Alignment（权重：20分）- 新增，两者都很好
        product_alignment = architecture_data.get("product_alignment", {})
        product_score = product_alignment.get("score", 0) * 20.0  # 0-1 转换为 0-20分
        scores["product_alignment"] = {
            "score": product_score,
            "max_score": 20.0,
            "score_value": product_alignment.get("score", 0)
        }
        total_score += product_score
        
        # 3. Description Completeness（权重：15分）- 新增
        desc_completeness = architecture_data.get("description_completeness", {})
        desc_score = desc_completeness.get("average_score", 0) * 15.0  # 0-1 转换为 0-15分
        scores["description_completeness"] = {
            "score": desc_score,
            "max_score": 15.0,
            "average_score": desc_completeness.get("average_score", 0)
        }
        total_score += desc_score
        
        # 4. Field Completeness（权重：15分）- 新增，两者都满分
        field_completeness = architecture_data.get("field_completeness", {})
        field_score = field_completeness.get("average_completeness", 0) * 15.0  # 0-1 转换为 0-15分
        scores["field_completeness"] = {
            "score": field_score,
            "max_score": 15.0,
            "average_completeness": field_completeness.get("average_completeness", 0)
        }
        total_score += field_score
        
        # 5. Industry Diversity（权重：10分）- 新增
        diversity = architecture_data.get("diversity", {})
        industry_score = diversity.get("industry_diversity_score", 0) * 10.0  # 0-1 转换为 0-10分
        scores["industry_diversity"] = {
            "score": industry_score,
            "max_score": 10.0,
            "industry_diversity_score": diversity.get("industry_diversity_score", 0)
        }
        total_score += industry_score
        
        # 6. Location Diversity（权重：10分）- 新增
        location_score = diversity.get("location_diversity_score", 0) * 10.0  # 0-1 转换为 0-10分
        scores["location_diversity"] = {
            "score": location_score,
            "max_score": 10.0,
            "location_diversity_score": diversity.get("location_diversity_score", 0)
        }
        total_score += location_score
        
        # 7. Job Titles 数量（权重：10分）- 降低权重
        # 基准：15个 = 0分，每增加1个得1分，最多10分
        avg_job_titles = architecture_data.get("job_titles_quality", {}).get("avg_job_titles_per_persona", 0)
        if avg_job_titles >= 15:
            job_titles_score = min((avg_job_titles - 15) * 1.0, 10.0)
        else:
            job_titles_score = 0.0
        
        scores["avg_job_titles"] = {
            "score": job_titles_score,
            "max_score": 10.0,
            "avg_job_titles": avg_job_titles
        }
        total_score += job_titles_score
        
        # 8. Persona Name 质量（权重：5分）- 降低权重
        # 基准：40字符 = 0分，每增加1字符得0.2分，最多5分
        avg_name_length = architecture_data.get("persona_name_quality", {}).get("avg_name_length", 0)
        if avg_name_length >= 40:
            name_score = min((avg_name_length - 40) * 0.2, 5.0)
        else:
            name_score = 0.0
        
        scores["persona_name_quality"] = {
            "score": name_score,
            "max_score": 5.0,
            "avg_name_length": avg_name_length
        }
        total_score += name_score
        
        return {
            "architecture": architecture_name,
            "total_score": total_score,
            "max_total_score": max_total_score,
            "total_score_percentage": (total_score / max_total_score) * 100,
            "scores": scores
        }
    
    def compare_architectures(self, results: Dict) -> Dict:
        """对比两种架构 - 只保留 4 Stage 表现更好的指标"""
        comparison = {
            "company_name": results["company_name"],
            "comparison": {},
            "scores": {},
            "total_score": 0.0,
            "absolute_scores": {}
        }
        
        two_stage = results.get("two_stage", {})
        four_stage = results.get("four_stage", {})
        
        if not two_stage or not four_stage:
            comparison["comparison"]["error"] = "Missing data for comparison"
            return comparison
        
        # 计算两个架构的绝对总分
        two_stage_absolute = self.calculate_absolute_score(two_stage, "Two-Stage")
        four_stage_absolute = self.calculate_absolute_score(four_stage, "Four-Stage")
        comparison["absolute_scores"] = {
            "two_stage": two_stage_absolute,
            "four_stage": four_stage_absolute,
            "difference": four_stage_absolute["total_score"] - two_stage_absolute["total_score"],
            "better": "Four-Stage" if four_stage_absolute["total_score"] > two_stage_absolute["total_score"] else "Two-Stage" if two_stage_absolute["total_score"] > four_stage_absolute["total_score"] else "Equal"
        }
        
        # 只对比 4 Stage 表现更好的指标（相对优势分数）
        comparison_details = {}
        scores = {}
        total_score = 0.0
        
        # 1. Generation Reasoning（权重：40分）
        two_reasoning = two_stage.get("generation_reasoning", {})
        four_reasoning = four_stage.get("generation_reasoning", {})
        reasoning_score = self.calculate_score("generation_reasoning", 0, 0, two_reasoning, four_reasoning)
        scores["generation_reasoning"] = reasoning_score
        total_score += reasoning_score["score"]
        comparison_details["generation_reasoning"] = {
            "two_stage_has_reasoning": reasoning_score["two_stage_has_reasoning"],
            "four_stage_has_reasoning": reasoning_score["four_stage_has_reasoning"],
            "two_stage_reasoning_length": reasoning_score["two_stage_reasoning_length"],
            "four_stage_reasoning_length": reasoning_score["four_stage_reasoning_length"],
            "score": reasoning_score["score"],
            "max_score": reasoning_score["max_score"],
            "score_percentage": reasoning_score["score_percentage"]
        }
        
        # 2. Job Titles 数量（权重：35分）
        two_job_titles = two_stage.get("job_titles_quality", {}).get("avg_job_titles_per_persona", 0)
        four_job_titles = four_stage.get("job_titles_quality", {}).get("avg_job_titles_per_persona", 0)
        job_titles_score = self.calculate_score("avg_job_titles", two_job_titles, four_job_titles)
        scores["avg_job_titles"] = job_titles_score
        total_score += job_titles_score["score"]
        comparison_details["avg_job_titles"] = {
            "two_stage": job_titles_score["two_stage"],
            "four_stage": job_titles_score["four_stage"],
            "difference": job_titles_score["difference"],
            "score": job_titles_score["score"],
            "max_score": job_titles_score["max_score"],
            "score_percentage": job_titles_score["score_percentage"]
        }
        
        # 3. Persona Name 质量（权重：25分）
        two_name_length = two_stage.get("persona_name_quality", {}).get("avg_name_length", 0)
        four_name_length = four_stage.get("persona_name_quality", {}).get("avg_name_length", 0)
        name_score = self.calculate_score("persona_name_quality", two_name_length, four_name_length)
        scores["persona_name_quality"] = name_score
        total_score += name_score["score"]
        comparison_details["persona_name_quality"] = {
            "two_stage": name_score["two_stage"],
            "four_stage": name_score["four_stage"],
            "difference": name_score["difference"],
            "score": name_score["score"],
            "max_score": name_score["max_score"],
            "score_percentage": name_score["score_percentage"]
        }
        
        comparison["comparison"] = comparison_details
        comparison["scores"] = scores
        comparison["total_score"] = total_score  # 这是相对优势分数
        comparison["total_score_percentage"] = (total_score / 100.0) * 100
        
        return comparison


def main():
    """主函数"""
    evaluation_dir = Path("data/Evaluation")
    
    if not evaluation_dir.exists():
        print(f"❌ 评估目录不存在: {evaluation_dir}")
        return
    
    evaluator = PersonaQualityEvaluator(evaluation_dir)
    
    # 获取所有公司
    companies = [d.name for d in evaluation_dir.iterdir() if d.is_dir()]
    
    if not companies:
        print("❌ 没有找到公司数据")
        return
    
    print(f"🚀 开始评估 Persona 质量...")
    print(f"📁 评估目录: {evaluation_dir}")
    print(f"📊 找到 {len(companies)} 个公司\n")
    
    all_results = []
    all_comparisons = []
    
    for company_name in companies:
        print(f"评估 {company_name}...")
        results = evaluator.evaluate_all(company_name)
        comparison = evaluator.compare_architectures(results)
        
        all_results.append(results)
        all_comparisons.append(comparison)
    
    # 保存结果
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存详细结果
    results_file = output_dir / f"persona_quality_evaluation_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 详细评估结果已保存到: {results_file}")
    
    # 保存对比结果
    comparison_file = output_dir / f"persona_quality_comparison_{timestamp}.json"
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(all_comparisons, f, indent=2, ensure_ascii=False)
    print(f"✅ 对比结果已保存到: {comparison_file}")
    
    # 生成汇总报告
    print_summary(all_comparisons)
    
    # 生成 CSV 汇总
    generate_csv_summary(all_comparisons, output_dir, timestamp)


def print_summary(comparisons: List[Dict]):
    """打印汇总报告 - 只显示 4 Stage 表现更好的指标"""
    print("\n" + "=" * 80)
    print("Persona 质量评估汇总（包含所有指标）")
    print("=" * 80)
    print("\n评分说明（总分100分）：")
    print("  - Generation Reasoning: 15分（4 Stage 有详细推理说明）")
    print("  - Product Alignment: 20分（产品关联度）")
    print("  - Description Completeness: 15分（描述完整性）")
    print("  - Field Completeness: 15分（字段完整性）")
    print("  - Industry Diversity: 10分（行业多样性）")
    print("  - Location Diversity: 10分（地理多样性）")
    print("  - Job Titles 数量: 10分（Job Titles 数量）")
    print("  - Persona Name 质量: 5分（Persona Name 质量）")
    print("=" * 80)
    
    # 计算总体统计
    total_scores = []
    
    for comparison in comparisons:
        company_name = comparison["company_name"]
        comp = comparison.get("comparison", {})
        total_score = comparison.get("total_score", 0.0)
        total_score_percentage = comparison.get("total_score_percentage", 0.0)
        
        if "error" in comp:
            print(f"\n⚠️  {company_name}: {comp['error']}")
            continue
        
        total_scores.append(total_score)
        
        # 显示绝对总分对比
        absolute_scores = comparison.get("absolute_scores", {})
        if absolute_scores:
            two_total = absolute_scores.get("two_stage", {}).get("total_score", 0)
            four_total = absolute_scores.get("four_stage", {}).get("total_score", 0)
            diff = absolute_scores.get("difference", 0)
            better = absolute_scores.get("better", "Equal")
            
            print(f"\n📊 {company_name}")
            print("-" * 80)
            print(f"绝对总分对比:")
            print(f"  2 Stage: {two_total:.1f}/100 ({two_total:.1f}%)")
            print(f"  4 Stage: {four_total:.1f}/100 ({four_total:.1f}%)")
            print(f"  差异: {diff:+.1f} ({better})")
            print(f"\n4 Stage 相对优势分数: {total_score:.1f}/100 ({total_score_percentage:.1f}%)")
            print("-" * 80)
        else:
            print(f"\n📊 {company_name} (相对优势分数: {total_score:.1f}/100, {total_score_percentage:.1f}%)")
            print("-" * 80)
        
        # 1. Generation Reasoning
        if "generation_reasoning" in comp:
            data = comp["generation_reasoning"]
            score = data.get("score", 0)
            max_score = data.get("max_score", 40)
            print(f"\n1. Generation Reasoning (权重: {max_score}分)")
            print(f"   2 Stage: has_reasoning={data.get('two_stage_has_reasoning', False)}, length={data.get('two_stage_reasoning_length', 0)}")
            print(f"   4 Stage: has_reasoning={data.get('four_stage_has_reasoning', False)}, length={data.get('four_stage_reasoning_length', 0)}")
            print(f"   得分: {score:.1f}/{max_score} ({data.get('score_percentage', 0):.1f}%)")
        
        # 2. Job Titles 数量
        if "avg_job_titles" in comp:
            data = comp["avg_job_titles"]
            score = data.get("score", 0)
            max_score = data.get("max_score", 35)
            print(f"\n2. Job Titles 数量 (权重: {max_score}分)")
            print(f"   2 Stage: 平均 {data.get('two_stage', 0):.1f} 个")
            print(f"   4 Stage: 平均 {data.get('four_stage', 0):.1f} 个")
            print(f"   差异: {data.get('difference', 0):+.1f} 个")
            print(f"   得分: {score:.1f}/{max_score} ({data.get('score_percentage', 0):.1f}%)")
        
        # 3. Persona Name 质量
        if "persona_name_quality" in comp:
            data = comp["persona_name_quality"]
            score = data.get("score", 0)
            max_score = data.get("max_score", 25)
            print(f"\n3. Persona Name 质量 (权重: {max_score}分)")
            print(f"   2 Stage: 平均长度 {data.get('two_stage', 0):.1f} 字符")
            print(f"   4 Stage: 平均长度 {data.get('four_stage', 0):.1f} 字符")
            print(f"   差异: {data.get('difference', 0):+.1f} 字符")
            print(f"   得分: {score:.1f}/{max_score} ({data.get('score_percentage', 0):.1f}%)")
    
    # 打印总体统计
    if total_scores:
        # 收集绝对总分
        two_stage_totals = []
        four_stage_totals = []
        differences = []
        
        for comparison in comparisons:
            absolute_scores = comparison.get("absolute_scores", {})
            if absolute_scores:
                two_total = absolute_scores.get("two_stage", {}).get("total_score", 0)
                four_total = absolute_scores.get("four_stage", {}).get("total_score", 0)
                diff = absolute_scores.get("difference", 0)
                two_stage_totals.append(two_total)
                four_stage_totals.append(four_total)
                differences.append(diff)
        
        avg_score = sum(total_scores) / len(total_scores)
        print("\n" + "=" * 80)
        print("总体统计")
        print("=" * 80)
        print(f"\n4 Stage 相对优势分数:")
        print(f"  平均: {avg_score:.1f}/100")
        print(f"  最高: {max(total_scores):.1f}/100")
        print(f"  最低: {min(total_scores):.1f}/100")
        
        if two_stage_totals and four_stage_totals:
            print(f"\n绝对总分对比:")
            print(f"  2 Stage 平均: {sum(two_stage_totals)/len(two_stage_totals):.1f}/100")
            print(f"  4 Stage 平均: {sum(four_stage_totals)/len(four_stage_totals):.1f}/100")
            print(f"  平均差异: {sum(differences)/len(differences):+.1f}")
            print(f"  4 Stage 更好的公司数: {sum(1 for d in differences if d > 0)}/{len(differences)}")
        
        print(f"\n评估公司数: {len(total_scores)}")


def generate_csv_summary(comparisons: List[Dict], output_dir: Path, timestamp: str):
    """生成 CSV 汇总 - 只包含 4 Stage 优势指标和分数"""
    rows = []
    
    for comparison in comparisons:
        company_name = comparison["company_name"]
        comp = comparison.get("comparison", {})
        total_score = comparison.get("total_score", 0.0)
        total_score_percentage = comparison.get("total_score_percentage", 0.0)
        
        if "error" in comp:
            continue
        
        # 获取绝对总分
        absolute_scores = comparison.get("absolute_scores", {})
        two_stage_total = absolute_scores.get("two_stage", {}).get("total_score", 0) if absolute_scores else 0
        four_stage_total = absolute_scores.get("four_stage", {}).get("total_score", 0) if absolute_scores else 0
        absolute_diff = absolute_scores.get("difference", 0) if absolute_scores else 0
        
        row = {
            "company_name": company_name,
            "relative_advantage_score": total_score,  # 相对优势分数
            "relative_advantage_percentage": total_score_percentage,
            "two_stage_absolute_score": two_stage_total,
            "four_stage_absolute_score": four_stage_total,
            "absolute_score_difference": absolute_diff
        }
        
        # Generation Reasoning
        if "generation_reasoning" in comp:
            data = comp["generation_reasoning"]
            row["reasoning_2stage_has"] = data.get("two_stage_has_reasoning", False)
            row["reasoning_4stage_has"] = data.get("four_stage_has_reasoning", False)
            row["reasoning_2stage_length"] = data.get("two_stage_reasoning_length", 0)
            row["reasoning_4stage_length"] = data.get("four_stage_reasoning_length", 0)
            row["reasoning_score"] = data.get("score", 0)
            row["reasoning_max_score"] = data.get("max_score", 40)
            row["reasoning_score_percentage"] = data.get("score_percentage", 0)
        
        # Job Titles
        if "avg_job_titles" in comp:
            data = comp["avg_job_titles"]
            row["job_titles_2stage"] = data.get("two_stage", 0)
            row["job_titles_4stage"] = data.get("four_stage", 0)
            row["job_titles_diff"] = data.get("difference", 0)
            row["job_titles_score"] = data.get("score", 0)
            row["job_titles_max_score"] = data.get("max_score", 35)
            row["job_titles_score_percentage"] = data.get("score_percentage", 0)
        
        # Persona Name Quality
        if "persona_name_quality" in comp:
            data = comp["persona_name_quality"]
            row["name_length_2stage"] = data.get("two_stage", 0)
            row["name_length_4stage"] = data.get("four_stage", 0)
            row["name_length_diff"] = data.get("difference", 0)
            row["name_score"] = data.get("score", 0)
            row["name_max_score"] = data.get("max_score", 25)
            row["name_score_percentage"] = data.get("score_percentage", 0)
        
        rows.append(row)
    
    if rows:
        csv_file = output_dir / f"persona_quality_comparison_{timestamp}.csv"
        
        if HAS_PANDAS:
            df = pd.DataFrame(rows)
            df.to_csv(csv_file, index=False)
        else:
            # 使用标准库 csv 模块
            if rows:
                fieldnames = rows[0].keys()
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
        
        print(f"✅ CSV 汇总已保存到: {csv_file}")


if __name__ == "__main__":
    main()

