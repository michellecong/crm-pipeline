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
        """
        初始化评估器
        
        Args:
            evaluation_dir: 评估数据目录
        """
        self.evaluation_dir = evaluation_dir
        
    def load_personas(self, company_name: str, architecture: str) -> tuple[List[Dict], Optional[Dict]]:
        """加载某个公司在某个架构下的 personas 和 products"""
        company_dir = self.evaluation_dir / company_name
        
        # 首先尝试精确匹配
        target_dir = company_dir / architecture
        if not target_dir.exists():
            # 如果精确匹配失败，尝试大小写不敏感匹配
            if company_dir.exists():
                for subdir in company_dir.iterdir():
                    if subdir.is_dir() and subdir.name.lower() == architecture.lower():
                        target_dir = subdir
                        break
                else:
                    return [], None
            else:
                return [], None
        
        company_dir = target_dir
        
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
        """评估 Job Titles 的质量（相关性、去重、层级分布）"""
        scores = []
        details = []
        
        for persona in personas:
            job_titles = persona.get("job_titles", [])
            if not job_titles:
                scores.append(0.0)
                details.append({
                    "persona_name": persona.get("persona_name", ""),
                    "count": 0,
                    "quality_score": 0.0,
                    "reason": "No job titles"
                })
                continue
            
            description = persona.get("description", "").lower()
            
            # 简单的词根提取函数
            def simple_stemming(word):
                """简单的词根提取，移除常见后缀"""
                if len(word) <= 4:
                    return word
                for suffix in ['ing', 'ed', 's', 'es', 'er', 'or', 'ly']:
                    if word.endswith(suffix) and len(word) > len(suffix) + 2:
                        return word[:-len(suffix)]
                return word
            
            # 1. 相关性检查（40%）：job titles 是否与 description 相关
            relevance_count = 0
            checked_titles = job_titles[:10]  # 只检查前10个，避免过度惩罚长列表
            
            for jt in checked_titles:
                jt_lower = jt.lower()
                
                # 提取关键词（去除常见停用词）
                stopwords = {'senior', 'junior', 'chief', 'manager', 'director', 'head', 'vp', 'vice', 'president', 'of', 'the', 'a', 'an', 'and', 'or', 'but'}
                jt_words = set(w for w in re.findall(r'\b\w+\b', jt_lower) if w not in stopwords)
                desc_words = set(re.findall(r'\b\w+\b', description))
                
                # 检查是否有共同的关键词
                common_words = jt_words & desc_words
                if len(jt_words) > 0 and len(common_words) > 0:
                    relevance_count += 1
                # 也检查完整匹配
                elif jt_lower in description:
                    relevance_count += 1
                # 词根匹配（提升匹配准确性）
                else:
                    jt_stems = {simple_stemming(w) for w in jt_words if len(w) > 3}
                    desc_stems = {simple_stemming(w) for w in desc_words if len(w) > 3}
                    common_stems = jt_stems & desc_stems
                    if len(jt_stems) > 0 and len(common_stems) > 0:
                        relevance_count += 1
            
            relevance_score = relevance_count / len(checked_titles) if checked_titles else 0.0
            
            # 2. 去重检查（20%）
            unique_titles = set([jt.lower().strip() for jt in job_titles])
            uniqueness_score = len(unique_titles) / len(job_titles) if job_titles else 0.0
            
            # 3. 层级分布（30%）：是否覆盖不同职级
            hierarchy_levels = {
                'c_level': ['ceo', 'cto', 'cfo', 'coo', 'cmo', 'chief', 'president'],
                'vp_level': ['vp', 'vice president'],
                'director': ['director'],
                'manager': ['manager', 'head of', 'lead'],
                'specialist': ['specialist', 'analyst', 'coordinator', 'executive']
            }
            
            levels_covered = set()
            for jt in job_titles:
                jt_lower = jt.lower()
                for level, keywords in hierarchy_levels.items():
                    if any(kw in jt_lower for kw in keywords):
                        levels_covered.add(level)
                        break
            
            # 理想情况：覆盖至少3个层级
            hierarchy_score = min(len(levels_covered) / 3.0, 1.0)
            
            # 4. 数量合理性（10%）：太少或太多都不好
            count = len(job_titles)
            if 10 <= count <= 30:
                count_score = 1.0
            elif 5 <= count < 10 or 30 < count <= 40:
                count_score = 0.7
            elif count < 5 or count > 40:
                count_score = 0.3
            else:
                count_score = 0.5
            
            # 综合评分
            quality_score = (
                relevance_score * 0.40 +
                uniqueness_score * 0.20 +
                hierarchy_score * 0.30 +
                count_score * 0.10
            )
            
            scores.append(quality_score)
            details.append({
                "persona_name": persona.get("persona_name", ""),
                "count": count,
                "relevance": round(relevance_score, 3),
                "uniqueness": round(uniqueness_score, 3),
                "hierarchy": round(hierarchy_score, 3),
                "count_score": round(count_score, 3),
                "quality_score": round(quality_score, 3)
            })
        
        # 保持向后兼容：也返回 avg_job_titles_per_persona
        avg_count = sum(len(p.get("job_titles", [])) for p in personas) / len(personas) if personas else 0.0
        
        return {
            "avg_quality_score": sum(scores) / len(scores) if scores else 0.0,
            "min_quality": min(scores) if scores else 0.0,
            "max_quality": max(scores) if scores else 0.0,
            "high_quality_personas": sum(1 for s in scores if s >= 0.7),
            "total_personas": len(scores),
            "details": details,
            # 向后兼容字段
            "avg_job_titles_per_persona": avg_count,
            "min_job_titles": min(len(p.get("job_titles", [])) for p in personas) if personas else 0,
            "max_job_titles": max(len(p.get("job_titles", [])) for p in personas) if personas else 0
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
    
    def evaluate_diversity(self, personas: List[Dict], company_name: str = "", products: Optional[List[Dict]] = None) -> Dict:
        """评估多样性（自适应评估：根据公司类型调整评分）"""
        if company_name:
            return self._evaluate_diversity_adaptive(personas, company_name, products)
        else:
            return self._evaluate_diversity_basic(personas)
    
    def _evaluate_diversity_basic(self, personas: List[Dict]) -> Dict:
        """基础多样性评估"""
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
    
    def _is_vertical_focused_company(self, company_name: str, products: Optional[List[Dict]] = None) -> bool:
        """判断公司是否专注于特定垂直行业"""
        # 垂直行业关键词（扩展版）
        vertical_keywords = [
            # 医疗健康
            'healthcare', 'medical', 'hospital', 'clinic', 'pharma', 'pharmaceutical', 'health',
            # 金融服务
            'financial', 'banking', 'insurance', 'fintech', 'wealth', 'investment', 'trading',
            # 制造业
            'manufacturing', 'automotive', 'industrial', 'factory', 'production',
            # 零售电商
            'retail', 'e-commerce', 'ecommerce', 'merchandising', 'commerce',
            # 房地产建筑
            'real estate', 'property', 'construction', 'procore', 'building',
            # 教育
            'education', 'edtech', 'learning', 'university', 'school',
            # 法律合规
            'legal', 'law', 'compliance', 'attorney', 'lawyer',
            # SaaS（垂直型）
            'saas', 'software as a service',
            # 物流供应链
            'logistics', 'supply chain', 'transportation', 'shipping',
            # 酒店餐饮
            'hospitality', 'hotel', 'restaurant', 'food service',
            # 农业
            'agriculture', 'agtech', 'farming',
            # 能源公用事业
            'energy', 'utility', 'power', 'electric',
            # 电信
            'telecom', 'telecommunications', 'wireless',
            # 媒体出版
            'media', 'publishing', 'broadcasting',
            # 公共部门
            'nonprofit', 'government', 'public sector'
        ]
        
        company_lower = company_name.lower()
        
        # 方法1：从公司名称判断（权重30%）
        name_score = sum(1 for kw in vertical_keywords if kw in company_lower) / len(vertical_keywords)
        name_indicator = name_score > 0
        
        # 方法2：从产品描述判断（权重70%）
        product_score = 0.0
        if products:
            product_texts = ' '.join([
                p.get('description', '') + ' ' + p.get('product_name', '')
                for p in products
            ]).lower()
            
            industry_mentions = {}
            for kw in vertical_keywords:
                count = product_texts.count(kw)
                if count > 0:
                    industry_mentions[kw] = count
            
            # 如果某个行业被提及3次以上，认为是垂直型
            if industry_mentions and max(industry_mentions.values()) >= 3:
                product_score = 1.0
            elif len(industry_mentions) == 1:
                product_score = 0.7  # 只提及一个行业
        
        # 综合判断
        total_score = (1.0 if name_indicator else 0.0) * 0.3 + product_score * 0.7
        return total_score >= 0.4
    
    def _evaluate_diversity_adaptive(self, personas: List[Dict], company_name: str, products: Optional[List[Dict]] = None) -> Dict:
        """自适应多样性评估：根据公司类型调整评分"""
        # 计算原始多样性指标
        basic_diversity = self._evaluate_diversity_basic(personas)
        
        # 判断公司类型
        is_vertical = self._is_vertical_focused_company(company_name, products)
        
        # 自适应评分
        if is_vertical:
            # 垂直型公司：行业集中度高 = 好（专注），地理多样性仍重要
            industry_concentration = 1 - basic_diversity["industry_diversity_score"]
            industry_score = industry_concentration * 10.0
            location_score = basic_diversity["location_diversity_score"] * 10.0
            
            interpretation = "垂直行业公司：期望行业专注（低多样性），地理覆盖广"
        else:
            # 通用型公司：高多样性 = 好（广泛适用）
            industry_score = basic_diversity["industry_diversity_score"] * 10.0
            location_score = basic_diversity["location_diversity_score"] * 10.0
            
            interpretation = "通用型公司：期望行业和地理都有多样性"
        
        # 返回结果，保持向后兼容
        result = basic_diversity.copy()
        result.update({
            "industry_score": industry_score,
            "location_score": location_score,
            "is_vertical_focused": is_vertical,
            "interpretation": interpretation,
            "adjusted_total": industry_score + location_score  # 总分20
        })
        
        return result
    
    def evaluate_generation_reasoning(self, company_name: str, architecture: str) -> Dict:
        """评估 Generation Reasoning 质量（仅适用于有 reasoning 的架构）"""
        company_base_dir = self.evaluation_dir / company_name
        
        # 尝试精确匹配
        company_dir = company_base_dir / architecture
        if not company_dir.exists():
            # 尝试大小写不敏感匹配
            if company_base_dir.exists():
                for subdir in company_base_dir.iterdir():
                    if subdir.is_dir() and subdir.name.lower() == architecture.lower():
                        company_dir = subdir
                        break
                else:
                    return {"has_reasoning": False, "reasoning_length": 0}
            else:
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
                except Exception:
                    continue
        
        return {
            "has_reasoning": reasoning_text is not None,
            "reasoning_length": reasoning_length,
            "reasoning_mentions_products": "product" in reasoning_text.lower() if reasoning_text else False,
            "reasoning_mentions_crm": "crm" in reasoning_text.lower() if reasoning_text else False
        }
    
    def evaluate_persona_name_quality(self, personas: List[Dict]) -> Dict:
        """评估 Persona Name 质量（规范性、信息完整性、长度合理性、可读性）"""
        scores = []
        details = []
        
        # 标准格式："[Geography] [Size] [Industry] - [Function]"
        format_pattern = re.compile(r'^.+?\s+.+?\s+.+?\s*-\s*.+$')
        
        # 关键词定义
        geo_keywords = ['north america', 'us', 'united states', 'europe', 'emea', 'apac', 'asia', 'global', 'latam', 'uk', 'canada', 'australia']
        size_keywords = ['enterprise', 'mid-market', 'mid market', 'smb', 'small', 'medium', 'large', 'startup']
        function_keywords = ['vp', 'director', 'manager', 'head', 'chief', 'leader', 'operations', 'sales', 'marketing', 'it', 'rev', 'revenue', 'ops']
        
        for persona in personas:
            name = persona.get("persona_name", "")
            score = 0.0
            checks = {}
            
            # 1. 格式规范性（30%）
            format_valid = bool(format_pattern.match(name))
            checks["format_valid"] = format_valid
            if format_valid:
                score += 0.30
            
            # 2. 信息完整性（40%）：是否包含4个关键组件
            name_lower = name.lower()
            has_geo = any(kw in name_lower for kw in geo_keywords)
            has_size = any(kw in name_lower for kw in size_keywords)
            has_industry = persona.get("industry", "") != "" and persona.get("industry", "").lower() in name_lower
            has_function = any(kw in name_lower for kw in function_keywords) or '-' in name
            
            checks.update({
                "has_geo": has_geo,
                "has_size": has_size,
                "has_industry": has_industry,
                "has_function": has_function
            })
            
            info_completeness = sum([has_geo, has_size, has_industry, has_function]) / 4.0
            score += info_completeness * 0.40
            
            # 3. 长度合理性（20%）：30-70字符为最佳
            length = len(name)
            if 30 <= length <= 70:
                length_score = 1.0
            elif 20 <= length < 30 or 70 < length <= 80:
                length_score = 0.7
            elif 15 <= length < 20 or 80 < length <= 100:
                length_score = 0.4
            else:
                length_score = 0.0
            
            checks["length"] = length
            checks["length_score"] = length_score
            score += length_score * 0.20
            
            # 4. 可读性（10%）：无特殊字符，单词间有空格
            has_special_chars = bool(re.search(r'[^\w\s\-]', name))
            has_proper_spacing = not bool(re.search(r'\w{20,}', name))  # 没有超长单词
            readability = (not has_special_chars) and has_proper_spacing
            checks["readability"] = readability
            if readability:
                score += 0.10
            
            scores.append(score)
            details.append({
                "persona_name": name,
                "score": round(score, 3),
                "checks": checks
            })
        
        # 向后兼容：也返回 avg_name_length
        name_lengths = [len(p.get("persona_name", "")) for p in personas]
        
        return {
            "avg_name_quality": sum(scores) / len(scores) if scores else 0.0,
            "names_with_high_quality": sum(1 for s in scores if s >= 0.7),
            "names_with_valid_format": sum(1 for d in details if d["checks"]["format_valid"]),
            "total_personas": len(scores),
            "details": details,
            # 向后兼容字段
            "avg_name_length": sum(name_lengths) / len(name_lengths) if name_lengths else 0.0,
            "valid_format_count": sum(1 for d in details if d["checks"]["format_valid"])
        }
    
    def detect_anomalies(self, results: Dict) -> List[str]:
        """检测异常的评估结果"""
        warnings = []
        company_name = results.get("company_name", "Unknown")
        
        for stage in ['two_stage', 'four_stage']:
            data = results.get(stage, {})
            if not data:
                continue
            
            stage_name = "2 Stage" if stage == "two_stage" else "4 Stage"
            
            # 检查是否有 persona 但没有 job titles
            persona_count = data.get("persona_count", 0)
            job_quality = data.get("job_titles_quality", {})
            avg_jobs = job_quality.get("avg_job_titles_per_persona", 0)
            
            if persona_count > 0 and avg_jobs == 0:
                msg = (f"{company_name} ({stage_name}): "
                       f"有 {persona_count} 个 personas 但没有 job titles")
                warnings.append(msg)

            # 检查 product alignment 是否过低
            product_alignment = data.get("product_alignment", {})
            product_score = product_alignment.get("score", 0)
            if product_score < 0.3 and persona_count > 0:
                msg = (f"{company_name} ({stage_name}): "
                       f"Product alignment 过低 ({product_score:.1%})")
                warnings.append(msg)

            # 检查 field completeness 是否不足
            field_completeness = data.get("field_completeness", {})
            field_score = field_completeness.get("average_completeness", 0)
            if field_score < 0.8 and persona_count > 0:
                msg = (f"{company_name} ({stage_name}): "
                       f"字段完整性不足 ({field_score:.1%})")
                warnings.append(msg)

            # 检查 description completeness 是否过低
            desc_completeness = data.get("description_completeness", {})
            desc_score = desc_completeness.get("average_score", 0)
            if desc_score < 0.5 and persona_count > 0:
                msg = (f"{company_name} ({stage_name}): "
                       f"描述完整性过低 ({desc_score:.1%})")
                warnings.append(msg)

            # 检查 job titles 质量是否过低
            if "avg_quality_score" in job_quality:
                quality_score = job_quality.get("avg_quality_score", 0)
                if quality_score < 0.4 and persona_count > 0:
                    msg = (f"{company_name} ({stage_name}): "
                           f"Job titles 质量过低 ({quality_score:.1%})")
                    warnings.append(msg)
        
        return warnings
    
    def evaluate_all(self, company_name: str) -> Dict:
        """评估某个公司的 2 Stage 和 4 Stage personas"""
        results = {
            "company_name": company_name,
            "two_stage": {},
            "four_stage": {}
        }
        
        # 评估 2 Stage - 尝试多种可能的目录名称
        two_stage_personas, two_stage_products = self.load_personas(company_name, "2 Stage")
        if not two_stage_personas:
            two_stage_personas, two_stage_products = self.load_personas(company_name, "2 stage")
        if not two_stage_personas:
            two_stage_personas, two_stage_products = self.load_personas(company_name, "Two-Stage")
        
        if two_stage_personas:
            results["two_stage"] = {
                "persona_count": len(two_stage_personas),
                "product_alignment": self.evaluate_product_alignment(two_stage_personas, two_stage_products),
                "description_completeness": self.evaluate_description_completeness(two_stage_personas),
                "job_titles_quality": self.evaluate_job_titles_quality(two_stage_personas),
                "field_completeness": self.evaluate_field_completeness(two_stage_personas),
                "diversity": self.evaluate_diversity(two_stage_personas, company_name, two_stage_products),
                "persona_name_quality": self.evaluate_persona_name_quality(two_stage_personas),
                "generation_reasoning": self.evaluate_generation_reasoning(company_name, "2 Stage")
            }
        
        # 评估 4 Stage - 尝试多种可能的目录名称
        four_stage_personas, four_stage_products = self.load_personas(company_name, "4 Stage")
        if not four_stage_personas:
            four_stage_personas, four_stage_products = self.load_personas(company_name, "4 stage")
        if not four_stage_personas:
            four_stage_personas, four_stage_products = self.load_personas(company_name, "Four-Stage")
        
        if four_stage_personas:
            results["four_stage"] = {
                "persona_count": len(four_stage_personas),
                "product_alignment": self.evaluate_product_alignment(four_stage_personas, four_stage_products),
                "description_completeness": self.evaluate_description_completeness(four_stage_personas),
                "job_titles_quality": self.evaluate_job_titles_quality(four_stage_personas),
                "field_completeness": self.evaluate_field_completeness(four_stage_personas),
                "diversity": self.evaluate_diversity(four_stage_personas, company_name, four_stage_products),
                "persona_name_quality": self.evaluate_persona_name_quality(four_stage_personas),
                "generation_reasoning": self.evaluate_generation_reasoning(company_name, "4 Stage")
            }
        
        # 检测异常情况
        anomalies = self.detect_anomalies(results)
        if anomalies:
            results["anomalies"] = anomalies
        
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
        """计算某个架构的绝对总分"""
        total_score = 0.0
        max_total_score = 100.0
        scores = {}
        
        # 1. Product Alignment（20分）
        product_alignment = architecture_data.get("product_alignment", {})
        product_score = product_alignment.get("score", 0) * 20.0
        scores["product_alignment"] = {
            "score": product_score,
            "max_score": 20.0,
            "score_value": product_alignment.get("score", 0)
        }
        total_score += product_score
        
        # 2. Description Completeness（15分）
        desc_completeness = architecture_data.get("description_completeness", {})
        desc_score = desc_completeness.get("average_score", 0) * 15.0
        scores["description_completeness"] = {
            "score": desc_score,
            "max_score": 15.0,
            "average_score": desc_completeness.get("average_score", 0)
        }
        total_score += desc_score
        
        # 3. Field Completeness（10分）
        field_completeness = architecture_data.get("field_completeness", {})
        field_score = field_completeness.get("average_completeness", 0) * 10.0
        scores["field_completeness"] = {
            "score": field_score,
            "max_score": 10.0,
            "average_completeness": field_completeness.get("average_completeness", 0)
        }
        total_score += field_score
        
        # 4. Job Titles 质量（15分）
        job_quality = architecture_data.get("job_titles_quality", {})
        if "avg_quality_score" in job_quality:
            job_score = job_quality.get("avg_quality_score", 0) * 15.0
        else:
            # 向后兼容：如果没有质量评分，使用数量评分
            avg_job_titles = job_quality.get("avg_job_titles_per_persona", 0)
            if avg_job_titles >= 15:
                job_score = min((avg_job_titles - 15) * 1.0, 15.0)
            else:
                job_score = 0.0
        scores["job_titles_quality"] = {
            "score": job_score,
            "max_score": 15.0,
            "avg_quality_score": job_quality.get("avg_quality_score", 0),
            "avg_job_titles": job_quality.get("avg_job_titles_per_persona", 0)
        }
        total_score += job_score
        
        # 5. Persona Name 质量（10分）
        name_quality = architecture_data.get("persona_name_quality", {})
        if "avg_name_quality" in name_quality:
            name_score = name_quality.get("avg_name_quality", 0) * 10.0
        else:
            # 向后兼容：如果没有质量评分，使用长度评分
            avg_name_length = name_quality.get("avg_name_length", 0)
            if avg_name_length >= 40:
                name_score = min((avg_name_length - 40) * 0.2, 10.0)
            else:
                name_score = 0.0
        scores["persona_name_quality"] = {
            "score": name_score,
            "max_score": 10.0,
            "avg_name_quality": name_quality.get("avg_name_quality", 0),
            "avg_name_length": name_quality.get("avg_name_length", 0)
        }
        total_score += name_score
        
        # 6. Diversity（20分）- 自适应评估
        diversity = architecture_data.get("diversity", {})
        if "adjusted_total" in diversity:
            diversity_score = diversity.get("adjusted_total", 0)
        else:
            # 向后兼容：使用基础多样性评分
            industry_score = diversity.get("industry_diversity_score", 0) * 10.0
            location_score = diversity.get("location_diversity_score", 0) * 10.0
            diversity_score = industry_score + location_score
        scores["diversity"] = {
            "score": diversity_score,
            "max_score": 20.0,
            "industry_score": diversity.get("industry_score", diversity.get("industry_diversity_score", 0) * 10.0),
            "location_score": diversity.get("location_score", diversity.get("location_diversity_score", 0) * 10.0),
            "is_vertical_focused": diversity.get("is_vertical_focused", False)
        }
        total_score += diversity_score
        
        # 7. Generation Reasoning（10分）
        reasoning = architecture_data.get("generation_reasoning", {})
        if reasoning.get("has_reasoning", False):
            reasoning_length = reasoning.get("reasoning_length", 0)
            if reasoning_length >= 1000:
                reasoning_score = 10.0
            elif reasoning_length >= 500:
                reasoning_score = 7.0
            elif reasoning_length > 0:
                reasoning_score = 4.0
            else:
                reasoning_score = 0.0
        else:
            reasoning_score = 0.0
        scores["generation_reasoning"] = {
            "score": reasoning_score,
            "max_score": 10.0,
            "has_reasoning": reasoning.get("has_reasoning", False),
            "reasoning_length": reasoning.get("reasoning_length", 0)
        }
        total_score += reasoning_score
        
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
        
        # 显示异常警告
        if "anomalies" in results and results["anomalies"]:
            print(f"  ⚠️  发现 {len(results['anomalies'])} 个异常:")
            for anomaly in results["anomalies"]:
                print(f"     - {anomaly}")
        
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
    
    print("\n评分说明（绝对总分100分）：")
    print("  - Product Alignment: 20分（产品关联度）")
    print("  - Description Completeness: 15分（描述完整性）")
    print("  - Field Completeness: 10分（字段完整性）")
    print("  - Job Titles 质量: 15分（Job Titles 质量评估）")
    print("  - Persona Name 质量: 10分（规范性评估）")
    print("  - Diversity: 20分（自适应多样性评估）")
    print("  - Generation Reasoning: 10分（推理说明质量）")
    print("\n相对优势分数（100分）：")
    print("  - Generation Reasoning: 40分（4 Stage 优势）")
    print("  - Job Titles 数量: 35分（4 Stage 优势）")
    print("  - Persona Name 质量: 25分（4 Stage 优势）")
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
            # 可视化进度条（每5分一个方块）
            two_bars = ("█" * int(two_total / 5) +
                        "░" * (20 - int(two_total / 5)))
            four_bars = ("█" * int(four_total / 5) +
                         "░" * (20 - int(four_total / 5)))
            print(f"  2 Stage: {two_total:.1f}/100 {two_bars} "
                  f"({two_total:.1f}%)")
            print(f"  4 Stage: {four_total:.1f}/100 {four_bars} "
                  f"({four_total:.1f}%)")
            # 使用表情符号表示差异
            if diff > 0:
                diff_emoji = "🟢 Better"
            elif diff < 0:
                diff_emoji = "🔴 Worse"
            else:
                diff_emoji = "⚪ Equal"
            print(f"  差异: {diff:+.1f} ({diff_emoji})")
            print(f"\n4 Stage 相对优势分数: {total_score:.1f}/100 "
                  f"({total_score_percentage:.1f}%)")
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
            two_has = data.get('two_stage_has_reasoning', False)
            two_len = data.get('two_stage_reasoning_length', 0)
            four_has = data.get('four_stage_has_reasoning', False)
            four_len = data.get('four_stage_reasoning_length', 0)
            print(f"   2 Stage: has_reasoning={two_has}, "
                  f"length={two_len}")
            print(f"   4 Stage: has_reasoning={four_has}, "
                  f"length={four_len}")
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
        
        # 显示异常情况（如果存在）
        # 注意：异常信息在 results 中，不在 comparison 中，所以这里暂时跳过
        # 异常信息已经在评估时打印了
    
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

