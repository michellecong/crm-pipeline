#!/usr/bin/env python3
"""
Mapping Quality Evaluation Script

评估 Mappings 的质量，包括：
1. Value Proposition 与 Product 的匹配度
2. Value Proposition 与 Persona 的匹配度
3. 文本质量（长度、完整性）
4. 量化指标（是否包含量化收益）
5. Pain Point 和 Value Proposition 的匹配度

混合评估模式：
- 所有指标使用 LLM 评估（一次调用评估所有指标）
- 传统方法作为补充：Text Quality（长度检查）、Quantified Benefits（模式匹配）

使用方法：
    python evaluate_mapping_quality.py
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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
    # Add project root to path to import app modules
    current_file = Path(__file__).absolute()
    project_root = current_file.parent  # evaluate_mapping_quality.py is in project root
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from app.services.llm_service import LLMService
    HAS_LLM = True
except (ImportError, Exception):
    HAS_LLM = False
    # Only print warning if explicitly trying to use LLM
    pass


class MappingQualityEvaluator:
    """评估 Mapping 质量的类（混合模式：LLM + 传统方法补充）"""
    
    def __init__(self, evaluation_dir: Path):
        """
        初始化评估器
        
        Args:
            evaluation_dir: 评估数据目录
        """
        self.evaluation_dir = evaluation_dir
        
        # 初始化 LLM 服务
        self.use_llm = HAS_LLM
        self.llm_service = None
        if self.use_llm:
            try:
                print("🔧 正在初始化 LLM 服务...")
                self.llm_service = LLMService()
                print(f"✅ LLM 评估模式已启用（混合模式：LLM + 传统方法补充）")
            except Exception as e:
                print(f"⚠️  LLM 服务初始化失败: {e}，将使用传统评估模式")
                self.use_llm = False
        else:
            print(f"⚠️  LLM 服务不可用，将使用传统评估模式")
        
        # 行业关键词映射
        self.industry_keywords = {
            "Financial Services": ["bank", "financial", "fraud", "compliance", "risk", "trading", "aml", "regulatory", "audit", "governance"],
            "Manufacturing": ["manufacturing", "plant", "factory", "production", "maintenance", "supply chain", "operations", "ot", "industrial"],
            "Healthcare": ["healthcare", "clinical", "patient", "medical", "pharma", "hospital", "ehr", "rcm", "revenue cycle"],
            "Retail/E-commerce": ["retail", "ecommerce", "merchandising", "inventory", "customer", "conversion", "sales", "store"],
            "B2B SaaS Platforms": ["saas", "revenue", "gtm", "revops", "sales ops", "forecast", "pipeline", "crm"],
        }
        
        # 角色关键词映射
        self.role_keywords = {
            "Data & AI": ["data", "analytics", "ml", "machine learning", "ai", "model", "pipeline", "governance", "catalog"],
            "Ops & Data Leaders": ["operations", "ops", "data", "analytics", "pipeline", "etl", "maintenance"],
            "Revenue Ops": ["revenue", "revops", "sales", "forecast", "pipeline", "gtm", "crm", "analytics"],
            "Merch & Analytics": ["merchandising", "analytics", "inventory", "customer", "personalization", "conversion"],
            "Clinical Data & RCM": ["clinical", "data", "rcm", "revenue cycle", "patient", "medical", "ehr"],
        }
        
        # 公司规模关键词
        self.size_keywords = {
            "enterprise": ["enterprise", "large", "complex", "multi-site", "global", "scale"],
            "mid-market": ["mid-market", "growing", "scaling", "emerging"],
            "small": ["small", "startup", "lean", "boutique"]
        }
    
    def load_mappings_and_personas(self, company_name: str, architecture: str) -> Tuple[List[Dict], List[Dict], Optional[List[Dict]]]:
        """加载某个公司在某个架构下的 mappings、personas 和 products"""
        company_base_dir = self.evaluation_dir / company_name
        
        # 首先尝试精确匹配
        company_dir = company_base_dir / architecture
        if not company_dir.exists():
            # 如果精确匹配失败，尝试大小写不敏感匹配
            if company_base_dir.exists():
                for subdir in company_base_dir.iterdir():
                    if subdir.is_dir() and subdir.name.lower() == architecture.lower():
                        company_dir = subdir
                        break
                else:
                    return [], [], None
            else:
                return [], [], None
        
        mappings_data = []
        personas_data = []
        products_data = None
        
        # 加载所有JSON文件
        for json_file in company_dir.glob("*.json"):
            filename = json_file.stem.lower()
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                if "mapping" in filename:
                    # Mappings 文件
                    if "result" in content and "personas_with_mappings" in content["result"]:
                        mappings_data = content["result"]["personas_with_mappings"]
                elif "persona" in filename and "mapping" not in filename:
                    # 独立的 personas 文件
                    if "result" in content and "personas" in content["result"]:
                        personas_data = content["result"]["personas"]
                elif "product" in filename:
                    # Products 文件
                    if "result" in content and "products" in content["result"]:
                        products_data = content["result"]["products"]
                elif "two_stage" in filename:
                    # Two-Stage consolidated 文件
                    if "result" in content:
                        if "personas_with_mappings" in content["result"]:
                            mappings_data = content["result"]["personas_with_mappings"]
                        if "personas" in content["result"]:
                            personas_data = content["result"]["personas"]
                        if "products" in content.get("result", {}):
                            products_data = content["result"]["products"]
                elif "three_stage" in filename:
                    # Three-Stage consolidated 文件
                    if "result" in content:
                        if "personas_with_mappings" in content["result"]:
                            mappings_data = content["result"]["personas_with_mappings"]
                            # 从 mappings 中提取 personas
                            for pwm in mappings_data:
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
                            
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
        
        return mappings_data, personas_data, products_data
    
    def evaluate_product_match(self, value_proposition: str, products: List[Dict]) -> Dict:
        """评估 Value Proposition 与 Product 的匹配度"""
        if not products or len(products) == 0:
            return {
                "has_product_mention": False,
                "mentioned_products": [],
                "product_count": 0,
                "product_names_found": [],
                "score": 0.0
            }
        
        # 提取所有产品名称
        product_names = [p.get("product_name", "") for p in products]
        
        # 检查 Value Proposition 中是否提及产品
        mentioned_products = []
        product_names_found = []
        
        value_prop_lower = value_proposition.lower()
        
        for product_name in product_names:
            if not product_name:
                continue
            
            # 检查完整产品名称
            if product_name.lower() in value_prop_lower:
                mentioned_products.append(product_name)
                product_names_found.append(product_name)
            else:
                # 检查产品名称的关键词（去除公司名）
                product_keywords = self._extract_product_keywords(product_name)
                for keyword in product_keywords:
                    if keyword.lower() in value_prop_lower and len(keyword) > 3:
                        mentioned_products.append(product_name)
                        product_names_found.append(product_name)
                        break
        
        # 计算分数：有产品提及得1.0，否则0.0
        score = 1.0 if len(mentioned_products) > 0 else 0.0
        
        return {
            "has_product_mention": len(mentioned_products) > 0,
            "mentioned_products": mentioned_products,
            "product_count": len(mentioned_products),
            "product_names_found": product_names_found,
            "score": score
        }
    
    def _extract_product_keywords(self, product_name: str) -> List[str]:
        """提取产品名称的关键词"""
        # 移除常见的公司名前缀
        name = product_name
        common_prefixes = ["databricks", "salesforce", "hubspot", "monday", "atlassian", "snowflake", "workday", "procore", "servicenow"]
        
        for prefix in common_prefixes:
            if name.lower().startswith(prefix.lower()):
                name = name[len(prefix):].strip()
                break
        
        # 分割成关键词
        keywords = re.split(r'[\s\-&/]+', name)
        keywords = [k for k in keywords if len(k) > 2]
        
        return keywords
    
    def evaluate_persona_match(self, value_proposition: str, pain_point: str, persona: Dict) -> Dict:
        """评估 Value Proposition 与 Persona 的匹配度"""
        if not persona:
            return {
                "industry_match_score": 0.0,
                "role_match_score": 0.0,
                "size_match_score": 0.0,
                "overall_match_score": 0.0
            }
        
        # 合并文本用于关键词匹配
        combined_text = (value_proposition + " " + pain_point).lower()
        
        # 1. 行业匹配度
        industry = persona.get("industry", "")
        industry_match_score = 0.0
        if industry:
            industry_keywords = self.industry_keywords.get(industry, [])
            if industry_keywords:
                matches = sum(1 for keyword in industry_keywords if keyword.lower() in combined_text)
                industry_match_score = min(matches / len(industry_keywords) * 2, 1.0)  # 归一化到0-1
        
        # 2. 角色匹配度（基于 persona_name 和 job_titles）
        role_match_score = 0.0
        persona_name = persona.get("persona_name", "").lower()
        
        # 从 persona_name 提取角色关键词
        role_keywords_to_check = []
        for role, keywords in self.role_keywords.items():
            if any(kw in persona_name for kw in role.lower().split()):
                role_keywords_to_check.extend(keywords)
        
        # 也从 job_titles 提取关键词
        job_titles = persona.get("job_titles", [])
        for job_title in job_titles:
            job_lower = job_title.lower()
            if "data" in job_lower or "analytics" in job_lower:
                role_keywords_to_check.extend(["data", "analytics", "ml", "machine learning"])
            if "revenue" in job_lower or "sales" in job_lower:
                role_keywords_to_check.extend(["revenue", "sales", "forecast", "pipeline"])
            if "operations" in job_lower or "ops" in job_lower:
                role_keywords_to_check.extend(["operations", "ops", "pipeline", "etl"])
            if "merchandising" in job_lower or "commerce" in job_lower:
                role_keywords_to_check.extend(["merchandising", "inventory", "customer", "conversion"])
            if "clinical" in job_lower or "healthcare" in job_lower:
                role_keywords_to_check.extend(["clinical", "patient", "medical", "rcm"])
        
        if role_keywords_to_check:
            unique_keywords = list(set(role_keywords_to_check))
            matches = sum(1 for keyword in unique_keywords if keyword.lower() in combined_text)
            role_match_score = min(matches / max(len(unique_keywords), 1) * 2, 1.0)  # 归一化到0-1
        
        # 3. 公司规模匹配度
        size_range = persona.get("company_size_range", "")
        size_match_score = 0.0
        if size_range:
            # 判断是 enterprise, mid-market 还是 small
            size_type = "enterprise"
            if "500" in size_range or "200" in size_range or "50" in size_range:
                if "2000" in size_range or "5000" in size_range or "10000" in size_range:
                    size_type = "mid-market"
                else:
                    size_type = "small"
            
            size_keywords = self.size_keywords.get(size_type, [])
            if size_keywords:
                matches = sum(1 for keyword in size_keywords if keyword.lower() in combined_text)
                size_match_score = min(matches / len(size_keywords) * 2, 1.0) if len(size_keywords) > 0 else 0.0
        
        # 综合匹配度（加权平均）
        overall_match_score = (
            industry_match_score * 0.4 +
            role_match_score * 0.4 +
            size_match_score * 0.2
        )
        
        return {
            "industry_match_score": industry_match_score,
            "role_match_score": role_match_score,
            "size_match_score": size_match_score,
            "overall_match_score": overall_match_score,
            "industry": industry,
            "size_range": size_range
        }
    
    def evaluate_text_quality(self, pain_point: str, value_proposition: str) -> Dict:
        """评估文本质量"""
        pain_point_len = len(pain_point)
        value_prop_len = len(value_proposition)
        
        # 检查长度是否符合要求（20-300字符）
        pain_point_valid = 20 <= pain_point_len <= 300
        value_prop_valid = 20 <= value_prop_len <= 300
        
        # 检查是否包含必要信息
        pain_point_has_who = bool(re.search(r'\b(teams?|leaders?|engineers?|analysts?|reps?|staff|organizations?|companies?)\b', pain_point, re.I))
        pain_point_has_impact = bool(re.search(r'\b(causing|leading to|resulting in|increasing|decreasing|delaying|reducing|improving)\b', pain_point, re.I))
        
        value_prop_has_how = bool(re.search(r'\b(provides|enables|automates|unifies|consolidates|accelerates|reduces|improves|cuts|delivers)\b', value_proposition, re.I))
        
        completeness_score = (
            (1.0 if pain_point_has_who else 0.0) * 0.25 +
            (1.0 if pain_point_has_impact else 0.0) * 0.25 +
            (1.0 if value_prop_has_how else 0.0) * 0.5
        )
        
        return {
            "pain_point_length": pain_point_len,
            "value_proposition_length": value_prop_len,
            "pain_point_valid_length": pain_point_valid,
            "value_proposition_valid_length": value_prop_valid,
            "completeness_score": completeness_score,
            "pain_point_has_who": pain_point_has_who,
            "pain_point_has_impact": pain_point_has_impact,
            "value_prop_has_how": value_prop_has_how
        }
    
    def evaluate_quantified_benefits(self, value_proposition: str) -> Dict:
        """评估量化指标"""
        # 查找百分比
        percentages = re.findall(r'\d+%', value_proposition)
        
        # 查找倍数（如 "3x", "10x"）
        multipliers = re.findall(r'\d+x', value_proposition, re.I)
        
        # 查找时间（如 "hours", "days", "weeks", "months"）
        time_mentions = re.findall(r'\d+\s*(?:hour|day|week|month|year)', value_proposition, re.I)
        
        # 查找金额（如 "$100K", "$2M"）
        amounts = re.findall(r'\$[€£¥]?\s*\d+[KMB]?', value_proposition, re.I)
        
        has_quantified_benefit = len(percentages) > 0 or len(multipliers) > 0 or len(time_mentions) > 0 or len(amounts) > 0
        
        return {
            "has_quantified_benefit": has_quantified_benefit,
            "percentages": percentages,
            "multipliers": multipliers,
            "time_mentions": time_mentions,
            "amounts": amounts,
            "total_metrics": len(percentages) + len(multipliers) + len(time_mentions) + len(amounts)
        }
    
    def evaluate_all_metrics_with_llm(
        self,
        pain_point: str,
        value_proposition: str,
        persona: Dict,
        products: List[Dict]
    ) -> Optional[Dict]:
        """
        一次 LLM 调用评估所有指标（混合模式）
        
        Args:
            pain_point: Pain Point 文本
            value_proposition: Value Proposition 文本
            persona: Persona 数据
            products: 产品列表
        
        Returns:
            包含所有指标评估结果的字典，如果失败返回 None
        """
        if not self.use_llm:
            return None
        
        # 构建评估 prompt
        persona_desc = persona.get('description', 'N/A') or 'N/A'
        if persona_desc != 'N/A' and len(persona_desc) > 300:
            persona_desc = persona_desc[:300] + "..."
        
        persona_info = f"""
Persona Name: {persona.get('persona_name', 'N/A')}
Industry: {persona.get('industry', 'N/A')}
Company Size: {persona.get('company_size_range', 'N/A')}
Job Titles: {', '.join(persona.get('job_titles', []) or [])}
Description: {persona_desc}
"""
        
        products_info = ""
        if products and len(products) > 0:
            products_list = "\n".join([
                f"- {p.get('product_name', 'N/A')}: {p.get('description', 'N/A')[:150]}"
                for p in products[:10]
            ])
            products_info = f"""
## 产品列表
{products_list}
"""
        
        prompt = f"""请评估以下 Pain Point 和 Value Proposition 的匹配质量。

## Persona 信息
{persona_info}{products_info}
## 待评估的 Mapping
Pain Point: {pain_point}
Value Proposition: {value_proposition}

## 评估任务
请从以下维度进行评估：

1. **Pain-Value Match (问题-方案匹配度)**: Value Proposition 是否直接、有效地解决了 Pain Point 中提到的问题？需要深度语义理解，判断方案是否真正解决问题。

2. **Persona Match (角色匹配度)**: Value Proposition 是否与 Persona 的角色、行业、公司规模相匹配？需要理解隐含的角色特征和行业背景。

3. **Product Match (产品匹配度)**: Value Proposition 是否自然、合理地提及了相关产品？能否理解概念匹配（如 'unified analytics platform' = 'Lakehouse'）？

4. **Text Quality (文本流畅度)**: 文本是否流畅、自然，没有语法错误？是否符合 B2B SaaS 行业的专业表达？语气是否合适？

请以 JSON 格式返回评估结果：
{{
  "pain_value_match": {{
    "score": 0.0-1.0,
    "reason": "详细说明匹配度的理由"
  }},
  "persona_match": {{
    "overall_match_score": 0.0-1.0,
    "role_match_score": 0.0-1.0,
    "industry_match_score": 0.0-1.0,
    "size_match_score": 0.0-1.0,
    "reason": "详细说明匹配度的理由"
  }},
  "product_match": {{
    "score": 0.0-1.0,
    "has_product_mention": true/false,
    "mentioned_products": ["product1", "product2", ...],
    "reason": "详细说明匹配度的理由"
  }},
  "text_quality": {{
    "fluency_score": 0.0-1.0,
    "professionalism_score": 0.0-1.0,
    "overall_score": 0.0-1.0,
    "reason": "详细说明评估理由"
  }}
}}
"""
        
        try:
            response = self.llm_service.generate(
                prompt=prompt,
                system_message="你是一个专业的 B2B 营销内容评估专家。请仔细分析并给出客观、专业的评估。",
                temperature=None,
                max_completion_tokens=1500
            )
            
            # 解析 JSON 响应
            content = response.content.strip()
            
            if not content:
                raise ValueError("LLM 返回了空响应")
            
            # 提取 JSON
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
            
            # 解析 JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        return None
                else:
                    return None
            
            # 转换为标准格式
            llm_results = {}
            
            if 'pain_value_match' in result:
                pvm = result["pain_value_match"]
                llm_results['pain_value_match'] = {
                    "match_score": float(pvm.get("score", 0.0)),
                    "reason": pvm.get("reason", ""),
                    "evaluation_method": "llm"
                }
            
            if 'persona_match' in result:
                pm = result["persona_match"]
                llm_results['persona_match'] = {
                    "overall_match_score": float(pm.get("overall_match_score", 0.0)),
                    "role_match_score": float(pm.get("role_match_score", 0.0)),
                    "industry_match_score": float(pm.get("industry_match_score", 0.0)),
                    "size_match_score": float(pm.get("size_match_score", 0.0)),
                    "reason": pm.get("reason", ""),
                    "evaluation_method": "llm"
                }
            
            if 'product_match' in result:
                pm = result["product_match"]
                llm_results['product_match'] = {
                    "score": float(pm.get("score", 0.0)),
                    "has_product_mention": bool(pm.get("has_product_mention", False)),
                    "mentioned_products": pm.get("mentioned_products", []),
                    "reason": pm.get("reason", ""),
                    "evaluation_method": "llm"
                }
            
            if 'text_quality' in result:
                tq = result["text_quality"]
                llm_results['text_quality'] = {
                    "fluency_score": float(tq.get("fluency_score", 0.0)),
                    "professionalism_score": float(tq.get("professionalism_score", 0.0)),
                    "overall_score": float(tq.get("overall_score", 0.0)),
                    "reason": tq.get("reason", ""),
                    "evaluation_method": "llm"
                }
            
            return llm_results
            
        except Exception as e:
            # 静默失败，返回 None，让调用者回退到传统方法
            # 只在调试时打印错误
            if False:  # 设置为 True 可以看到详细错误
                print(f"    LLM 评估异常: {e}")
            return None
    
    def evaluate_with_llm(
        self,
        pain_point: str,
        value_proposition: str,
        persona: Dict,
        products: List[Dict]
    ) -> Dict:
        """使用 LLM 进行智能评估"""
        if not self.use_llm:
            raise ValueError("LLM evaluation is not enabled")
        
        # 构建评估 prompt
        persona_desc = persona.get('description', 'N/A') or 'N/A'
        if persona_desc != 'N/A' and len(persona_desc) > 200:
            persona_desc = persona_desc[:200]
        
        persona_info = f"""
Persona Name: {persona.get('persona_name', 'N/A')}
Industry: {persona.get('industry', 'N/A')}
Company Size: {persona.get('company_size_range', 'N/A')}
Job Titles: {', '.join(persona.get('job_titles', []) or [])}
Description: {persona_desc}
"""
        
        products_info = "\n".join([
            f"- {p.get('product_name', 'N/A')}: {p.get('description', 'N/A')[:100]}"
            for p in (products or [])[:5]
        ])
        
        prompt = f"""请评估以下 Pain Point 和 Value Proposition 的匹配质量。

## Persona 信息
{persona_info}

## 产品列表
{products_info}

## 待评估的 Mapping
Pain Point: {pain_point}
Value Proposition: {value_proposition}

## 评估任务
请从以下维度进行评估，每个维度给出 0-1 的分数和简短理由：

1. **Product Match (产品匹配度)**: Value Proposition 是否自然、合理地提及了相关产品？产品名称是否与产品列表匹配？
2. **Persona Match (角色匹配度)**: Value Proposition 是否与 Persona 的角色、行业、公司规模相匹配？
3. **Pain-Value Match (问题-方案匹配度)**: Value Proposition 是否直接、有效地解决了 Pain Point 中提到的问题？
4. **Text Quality (文本质量)**: 文本是否清晰、完整、专业？长度是否合适（20-300字符）？
5. **Quantified Benefits (量化收益)**: 是否包含具体的量化指标（百分比、倍数、时间、金额）？

请以 JSON 格式返回评估结果：
{{
  "product_match": {{
    "score": 0.0-1.0,
    "reason": "简短理由"
  }},
  "persona_match": {{
    "score": 0.0-1.0,
    "reason": "简短理由"
  }},
  "pain_value_match": {{
    "score": 0.0-1.0,
    "reason": "简短理由"
  }},
  "text_quality": {{
    "score": 0.0-1.0,
    "reason": "简短理由"
  }},
  "quantified_benefits": {{
    "score": 0.0-1.0,
    "has_quantified": true/false,
    "reason": "简短理由"
  }},
  "overall_score": 0.0-1.0,
  "overall_reason": "总体评价"
}}
"""
        
        try:
            # 调用 LLM
            # 注意：某些模型（如 gpt-5-mini）可能只支持默认 temperature，所以使用 None 让服务使用默认值
            response = self.llm_service.generate(
                prompt=prompt,
                system_message="你是一个专业的 B2B 营销内容评估专家。请仔细分析并给出客观、专业的评估。",
                temperature=None,  # 使用默认值，让模型决定
                max_completion_tokens=1000
            )
            
            # 解析 JSON 响应
            content = response.content.strip()
            
            # 如果响应为空，抛出异常
            if not content:
                raise ValueError("LLM 返回了空响应")
            
            # 尝试提取 JSON（可能包含 markdown 代码块）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                # 查找第一个代码块
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1].strip()
                    # 移除语言标识符（如 "json"）
                    if content.startswith("json"):
                        content = content[4:].strip()
                    elif content.startswith("JSON"):
                        content = content[4:].strip()
            
            # 尝试解析 JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                # 如果解析失败，尝试查找 JSON 对象
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        raise ValueError(f"无法解析 LLM 返回的 JSON: {e}. 响应内容: {content[:200]}")
                else:
                    raise ValueError(f"无法解析 LLM 返回的 JSON: {e}. 响应内容: {content[:200]}")
            
            # 转换为标准格式
            return {
                "product_match": {
                    "score": result.get("product_match", {}).get("score", 0.0),
                    "has_product_mention": result.get("product_match", {}).get("score", 0.0) > 0.5,
                    "reason": result.get("product_match", {}).get("reason", "")
                },
                "persona_match": {
                    "overall_match_score": result.get("persona_match", {}).get("score", 0.0),
                    "reason": result.get("persona_match", {}).get("reason", "")
                },
                "text_quality": {
                    "completeness_score": result.get("text_quality", {}).get("score", 0.0),
                    "reason": result.get("text_quality", {}).get("reason", "")
                },
                "quantified_benefits": {
                    "has_quantified_benefit": result.get("quantified_benefits", {}).get("has_quantified", False),
                    "score": result.get("quantified_benefits", {}).get("score", 0.0),
                    "reason": result.get("quantified_benefits", {}).get("reason", "")
                },
                "pain_value_match": {
                    "match_score": result.get("pain_value_match", {}).get("score", 0.0),
                    "reason": result.get("pain_value_match", {}).get("reason", "")
                },
                "overall_score": result.get("overall_score", 0.0),
                "overall_reason": result.get("overall_reason", ""),
                "evaluation_method": "llm"
            }
            
        except Exception as e:
            print(f"⚠️  LLM 评估失败: {e}，回退到传统评估方法")
            # 回退到传统方法
            return None
    
    def evaluate_pain_value_match(self, pain_point: str, value_proposition: str) -> Dict:
        """评估 Pain Point 和 Value Proposition 的匹配度"""
        # 简单的关键词匹配
        pain_lower = pain_point.lower()
        value_lower = value_proposition.lower()
        
        # 提取 Pain Point 中的问题关键词
        problem_keywords = []
        problem_patterns = [
            r"struggle\s+with\s+(\w+)",
            r"lack\s+(\w+)",
            r"can't\s+(\w+)",
            r"waste\s+(\w+)",
            r"face\s+(\w+)",
            r"spend\s+(\w+)",
        ]
        
        for pattern in problem_patterns:
            matches = re.findall(pattern, pain_lower)
            problem_keywords.extend(matches)
        
        # 提取 Value Proposition 中的解决方案关键词
        solution_keywords = []
        solution_patterns = [
            r"provides\s+(\w+)",
            r"enables\s+(\w+)",
            r"automates\s+(\w+)",
            r"unifies\s+(\w+)",
            r"consolidates\s+(\w+)",
            r"reduces\s+(\w+)",
            r"improves\s+(\w+)",
        ]
        
        for pattern in solution_patterns:
            matches = re.findall(pattern, value_lower)
            solution_keywords.extend(matches)
        
        # 计算匹配度（简单的关键词重叠）
        if problem_keywords and solution_keywords:
            # 检查是否有相关的关键词匹配
            common_keywords = set(["data", "analytics", "pipeline", "revenue", "sales"])
            matches = sum(
                1 for pk in problem_keywords[:3] for sk in solution_keywords[:3]
                if pk in sk or sk in pk or len(set([pk, sk]) & common_keywords) > 0
            )
            match_score = min(
                matches / max(len(problem_keywords), len(solution_keywords)), 1.0
            )
        else:
            match_score = 0.5  # 如果没有明显的关键词，给中等分数
        
        return {
            "match_score": match_score,
            "problem_keywords": problem_keywords[:5],
            "solution_keywords": solution_keywords[:5]
        }
    
    def evaluate_all_mappings(self, company_name: str, architecture: str) -> Dict:
        """评估某个公司在某个架构下的所有 mappings"""
        mappings_data, personas_data, products_data = self.load_mappings_and_personas(
            company_name, architecture
        )
        
        if not mappings_data:
            return {
                "company_name": company_name,
                "architecture": architecture,
                "error": "No mappings data found"
            }
        
        # 创建 persona 字典（通过 persona_name 索引）
        persona_dict = {p.get("persona_name", ""): p for p in personas_data}
        
        results = {
            "company_name": company_name,
            "architecture": architecture,
            "total_personas": len(mappings_data),
            "total_mappings": 0,
            "mapping_details": []
        }
        
        total_mappings_count = sum(len(pm.get("mappings", [])) for pm in mappings_data)
        print(f"  找到 {total_mappings_count} 个 mappings，开始评估...")
        
        for idx, persona_mapping in enumerate(mappings_data):
            persona_name = persona_mapping.get("persona_name", "")
            mappings = persona_mapping.get("mappings", [])
            
            persona = persona_dict.get(persona_name, {})
            print(f"  评估 Persona: {persona_name} ({len(mappings)} 个 mappings)")
            
            for mapping_idx, mapping in enumerate(mappings):
                pain_point = mapping.get("pain_point", "")
                value_proposition = mapping.get("value_proposition", "")
                
                # 显示进度
                current_count = results["total_mappings"] + 1
                if current_count % 5 == 0 or current_count == 1:
                    print(f"    正在评估第 {current_count}/{total_mappings_count} 个 mapping...")
                
                # 混合评估：一次 LLM 调用评估所有指标
                evaluation_metadata = {"method": "hybrid"}
                
                # 一次 LLM 调用评估所有指标
                try:
                    llm_results = self.evaluate_all_metrics_with_llm(
                        pain_point, value_proposition, persona, products_data or []
                    )
                except Exception as e:
                    print(f"    ⚠️  LLM 调用失败: {e}，使用传统方法")
                    llm_results = None
                
                # 1. Pain-Value Match
                if llm_results and 'pain_value_match' in llm_results:
                    pain_value_match = llm_results['pain_value_match']
                else:
                    pain_value_match = self.evaluate_pain_value_match(pain_point, value_proposition)
                    pain_value_match["evaluation_method"] = "traditional"
                
                # 2. Persona Match
                if llm_results and 'persona_match' in llm_results:
                    persona_match = llm_results['persona_match']
                else:
                    persona_match = self.evaluate_persona_match(value_proposition, pain_point, persona)
                    persona_match["evaluation_method"] = "traditional"
                
                # 3. Product Match
                if llm_results and 'product_match' in llm_results:
                    product_match = llm_results['product_match']
                else:
                    product_match = self.evaluate_product_match(value_proposition, products_data or [])
                    product_match["evaluation_method"] = "traditional"
                
                # 4. Text Quality（混合：传统方法检查长度 + LLM 评估流畅度）
                text_quality = self.evaluate_text_quality(pain_point, value_proposition)  # 传统方法：长度、结构
                text_quality["evaluation_method"] = "traditional"
                
                if llm_results and 'text_quality' in llm_results:
                    tq_llm = llm_results['text_quality']
                    text_quality["fluency_score"] = tq_llm.get("fluency_score", 0.0)
                    text_quality["professionalism_score"] = tq_llm.get("professionalism_score", 0.0)
                    text_quality["fluency_reason"] = tq_llm.get("reason", "")
                    # 综合分数：基础检查（50%）+ 流畅度（50%）
                    text_quality["completeness_score"] = (
                        text_quality["completeness_score"] * 0.5 +
                        tq_llm.get("overall_score", 0.0) * 0.5
                    )
                    text_quality["evaluation_method"] = "hybrid"
                
                # 5. Quantified Benefits（传统方法足够，模式匹配任务）
                quantified_benefits = self.evaluate_quantified_benefits(value_proposition)
                quantified_benefits["evaluation_method"] = "traditional"
                
                results["mapping_details"].append({
                    "persona_name": persona_name,
                    "pain_point": pain_point,
                    "value_proposition": value_proposition,
                    "product_match": product_match,
                    "persona_match": persona_match,
                    "text_quality": text_quality,
                    "quantified_benefits": quantified_benefits,
                    "pain_value_match": pain_value_match,
                    "evaluation_metadata": evaluation_metadata
                })
                
                results["total_mappings"] += 1
        
        # 计算汇总统计
        if results["mapping_details"]:
            product_match_scores = [m["product_match"]["score"] for m in results["mapping_details"]]
            persona_match_scores = [m["persona_match"]["overall_match_score"] for m in results["mapping_details"]]
            text_quality_scores = [m["text_quality"]["completeness_score"] for m in results["mapping_details"]]
            quantified_benefit_rates = [1.0 if m["quantified_benefits"]["has_quantified_benefit"] else 0.0 for m in results["mapping_details"]]
            pain_value_match_scores = [m["pain_value_match"]["match_score"] for m in results["mapping_details"]]
            
            results["summary"] = {
                "avg_product_match_score": sum(product_match_scores) / len(product_match_scores) if product_match_scores else 0.0,
                "avg_persona_match_score": sum(persona_match_scores) / len(persona_match_scores) if persona_match_scores else 0.0,
                "avg_text_quality_score": sum(text_quality_scores) / len(text_quality_scores) if text_quality_scores else 0.0,
                "quantified_benefit_rate": sum(quantified_benefit_rates) / len(quantified_benefit_rates) if quantified_benefit_rates else 0.0,
                "avg_pain_value_match_score": sum(pain_value_match_scores) / len(pain_value_match_scores) if pain_value_match_scores else 0.0,
                "mappings_with_product_mention": sum(1 for m in results["mapping_details"] if m["product_match"]["has_product_mention"]),
                "mappings_with_quantified_benefits": sum(1 for m in results["mapping_details"] if m["quantified_benefits"]["has_quantified_benefit"])
            }
        
        return results
    
    def compare_architectures(self, two_stage_results: Dict, three_stage_results: Dict = None, four_stage_results: Dict = None) -> Dict:
        """对比两种或三种架构的 mappings 质量"""
        comparison = {
            "company_name": two_stage_results.get("company_name", ""),
            "comparison": {}
        }
        
        two_summary = two_stage_results.get("summary", {})
        three_summary = three_stage_results.get("summary", {}) if three_stage_results else {}
        four_summary = four_stage_results.get("summary", {}) if four_stage_results else {}
        
        # 检查是否有足够的数据
        has_two = bool(two_summary)
        has_three = bool(three_summary)
        has_four = bool(four_summary)
        
        if not has_two:
            comparison["comparison"]["error"] = "Missing 2-stage summary data"
            return comparison
        
        if not has_three and not has_four:
            comparison["comparison"]["error"] = "Missing 3-stage or 4-stage summary data"
            return comparison
        
        # 对比各项指标
        metrics = {
            "product_match_score": "avg_product_match_score",
            "persona_match_score": "avg_persona_match_score",
            "text_quality_score": "avg_text_quality_score",
            "quantified_benefit_rate": "quantified_benefit_rate",
            "pain_value_match_score": "avg_pain_value_match_score"
        }
        
        comparison_details = {}
        for metric_name, summary_key in metrics.items():
            two_value = two_summary.get(summary_key, 0)
            three_value = three_summary.get(summary_key, 0) if has_three else None
            four_value = four_summary.get(summary_key, 0) if has_four else None
            
            # 找出最佳值
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
        
        # 产品提及率对比
        two_product_mention_rate = two_stage_results.get("summary", {}).get("mappings_with_product_mention", 0) / max(two_stage_results.get("total_mappings", 1), 1)
        three_product_mention_rate = None
        four_product_mention_rate = None
        
        if has_three:
            three_product_mention_rate = three_stage_results.get("summary", {}).get("mappings_with_product_mention", 0) / max(three_stage_results.get("total_mappings", 1), 1)
        if has_four:
            four_product_mention_rate = four_stage_results.get("summary", {}).get("mappings_with_product_mention", 0) / max(four_stage_results.get("total_mappings", 1), 1)
        
        mention_values = {"two_stage": two_product_mention_rate}
        if three_product_mention_rate is not None:
            mention_values["three_stage"] = three_product_mention_rate
        if four_product_mention_rate is not None:
            mention_values["four_stage"] = four_product_mention_rate
        
        best_mention_stage = max(mention_values.items(), key=lambda x: x[1])[0] if mention_values else "two_stage"
        
        comparison_details["product_mention_rate"] = {
            "two_stage": two_product_mention_rate,
            "three_stage": three_product_mention_rate,
            "four_stage": four_product_mention_rate,
            "best": best_mention_stage
        }
        
        comparison["comparison"] = comparison_details
        
        return comparison


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="评估 Mappings 质量（混合模式）")
    parser.add_argument(
        "--company",
        type=str,
        help="只评估指定的公司（如果不指定，评估所有公司）"
    )
    args = parser.parse_args()
    
    evaluation_dir = Path("data/Evaluation")
    
    if not evaluation_dir.exists():
        print(f"❌ 评估目录不存在: {evaluation_dir}")
        return
    
    evaluator = MappingQualityEvaluator(evaluation_dir)
    
    # 获取要评估的公司列表
    if args.company:
        companies = [args.company]
        if not (evaluation_dir / args.company).exists():
            print(f"❌ 公司目录不存在: {args.company}")
            return
    else:
        companies = [d.name for d in evaluation_dir.iterdir() if d.is_dir()]
    
    if not companies:
        print("❌ 没有找到公司数据")
        return
    
    print(f"🚀 开始评估 Mappings 质量...")
    print(f"📁 评估目录: {evaluation_dir}")
    print(f"📊 评估 {len(companies)} 个公司: {', '.join(companies)}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 准备输出目录
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)
    
    all_results = []
    all_comparisons = []
    
    for idx, company_name in enumerate(companies, 1):
        print(f"\n{'='*80}")
        print(f"评估公司 {idx}/{len(companies)}: {company_name}")
        print(f"{'='*80}")
        
        try:
            # 评估 2 Stage
            print(f"\n📊 评估 2 Stage...")
            two_stage_results = evaluator.evaluate_all_mappings(company_name, "2 Stage")
            if "error" in two_stage_results:
                two_stage_results = evaluator.evaluate_all_mappings(company_name, "Two-Stage")
            if "error" in two_stage_results:
                two_stage_results = evaluator.evaluate_all_mappings(company_name, "2 stage")
            
            # 评估 3 Stage
            print(f"\n📊 评估 3 Stage...")
            three_stage_results = evaluator.evaluate_all_mappings(company_name, "3 Stage")
            if "error" in three_stage_results:
                three_stage_results = evaluator.evaluate_all_mappings(company_name, "Three-Stage")
            if "error" in three_stage_results:
                three_stage_results = evaluator.evaluate_all_mappings(company_name, "3 stage")
            
            # 评估 4 Stage
            print(f"\n📊 评估 4 Stage...")
            four_stage_results = evaluator.evaluate_all_mappings(company_name, "4 Stage")
            if "error" in four_stage_results:
                four_stage_results = evaluator.evaluate_all_mappings(company_name, "Four-Stage")
            if "error" in four_stage_results:
                four_stage_results = evaluator.evaluate_all_mappings(company_name, "4 stage")
            
            # 进行三方比较
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
            
            print(f"\n✅ {company_name} 评估完成 ({idx}/{len(companies)})")
            
            # 每评估完一个公司就保存一次（防止中途出错丢失数据）
            if idx % 2 == 0 or idx == len(companies):
                temp_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_file = output_dir / f"mapping_quality_evaluation_temp_{temp_timestamp}.json"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(all_results, f, indent=2, ensure_ascii=False)
                print(f"💾 临时保存: {temp_file} ({len(all_results)} 个公司)")
                
        except Exception as e:
            print(f"\n❌ 评估 {company_name} 时出错: {e}")
            import traceback
            traceback.print_exc()
            # 即使出错也保存已完成的评估
            all_results.append({
                "company_name": company_name,
                "error": str(e)
            })
            continue
    
    # 保存最终结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{'='*80}")
    print(f"开始保存最终结果（共 {len(all_results)} 个公司）...")
    print(f"{'='*80}")
    
    # 保存详细结果
    results_file = output_dir / f"mapping_quality_evaluation_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 详细评估结果已保存到: {results_file}")
    
    # 保存对比结果
    comparison_file = output_dir / f"mapping_quality_comparison_{timestamp}.json"
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(all_comparisons, f, indent=2, ensure_ascii=False)
    print(f"✅ 对比结果已保存到: {comparison_file}")
    
    # 生成汇总报告
    print_summary(all_comparisons)
    
    print(f"\n✨ 评估完成！")
    print(f"⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 结果已保存到: {output_dir}")
    
    # 确保程序正常退出（清理资源）
    import sys
    sys.exit(0)


def print_summary(comparisons: List[Dict]):
    """打印汇总报告"""
    print("\n" + "=" * 80)
    print("Mappings 质量评估汇总（2 Stage vs 3 Stage vs 4 Stage）")
    print("=" * 80)
    
    for comparison in comparisons:
        company_name = comparison["company_name"]
        comp = comparison.get("comparison", {})
        
        if "error" in comp:
            print(f"\n⚠️  {company_name}: {comp['error']}")
            continue
        
        print(f"\n📊 {company_name}:")
        print("-" * 80)
        
        for metric_name, metric_data in comp.items():
            if isinstance(metric_data, dict) and "two_stage" in metric_data:
                two_val = metric_data["two_stage"]
                three_val = metric_data.get("three_stage")
                four_val = metric_data.get("four_stage")
                best = metric_data.get("best", "two_stage")
                
                print(f"\n{metric_name}:")
                print(f"  2 Stage: {two_val:.3f}")
                if three_val is not None:
                    marker_3 = " ⭐" if best == "three_stage" else ""
                    print(f"  3 Stage: {three_val:.3f}{marker_3}")
                if four_val is not None:
                    marker_4 = " ⭐" if best == "four_stage" else ""
                    print(f"  4 Stage: {four_val:.3f}{marker_4}")
                print(f"  最佳: {best.replace('_', ' ').title()}")
    
    # 计算总体统计
    if comparisons:
        metrics_to_avg = {}
        for comparison in comparisons:
            comp = comparison.get("comparison", {})
            if "error" in comp:
                continue
            
            for metric_name, metric_data in comp.items():
                if isinstance(metric_data, dict) and "two_stage" in metric_data:
                    if metric_name not in metrics_to_avg:
                        metrics_to_avg[metric_name] = {"two": [], "three": [], "four": []}
                    metrics_to_avg[metric_name]["two"].append(metric_data["two_stage"])
                    if metric_data.get("three_stage") is not None:
                        metrics_to_avg[metric_name]["three"].append(metric_data["three_stage"])
                    if metric_data.get("four_stage") is not None:
                        metrics_to_avg[metric_name]["four"].append(metric_data["four_stage"])
        
        print("\n" + "=" * 80)
        print("总体统计")
        print("=" * 80)
        
        for metric_name, values in metrics_to_avg.items():
            two_avg = sum(values["two"]) / len(values["two"]) if values["two"] else 0
            three_avg = sum(values["three"]) / len(values["three"]) if values["three"] else 0
            four_avg = sum(values["four"]) / len(values["four"]) if values["four"] else 0
            
            print(f"\n{metric_name}:")
            print(f"  2 Stage 平均: {two_avg:.3f}")
            if values["three"]:
                print(f"  3 Stage 平均: {three_avg:.3f}")
            if values["four"]:
                print(f"  4 Stage 平均: {four_avg:.3f}")
            
            # 找出最佳平均值
            avgs = {"2 Stage": two_avg}
            if values["three"]:
                avgs["3 Stage"] = three_avg
            if values["four"]:
                avgs["4 Stage"] = four_avg
            best_avg = max(avgs.items(), key=lambda x: x[1])[0] if avgs else "2 Stage"
            print(f"  最佳平均: {best_avg} ({max(avgs.values()):.3f})")




if __name__ == "__main__":
    main()

