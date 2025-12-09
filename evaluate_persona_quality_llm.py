#!/usr/bin/env python3
"""
LLM-based Persona Quality Evaluation Script

使用 LLM 智能评估 Persona 质量，提供更深入的质量分析和建议。
评估维度：
1. 描述质量和完整性
2. Job Titles 相关性和合理性
3. Persona Name 规范性和信息密度
4. 与产品的关联度
5. 整体一致性和逻辑性
6. 实用性和可操作性
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.llm_service import LLMService, get_llm_service
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMPersonaEvaluator:
    """使用 LLM 评估 Persona 质量的类"""
    
    def __init__(self, evaluation_dir: Path, llm_service: Optional[LLMService] = None):
        """
        初始化评估器
        
        Args:
            evaluation_dir: 评估数据目录
            llm_service: LLM 服务实例，如果为 None 则使用默认服务
        """
        self.evaluation_dir = evaluation_dir
        self.llm_service = llm_service or get_llm_service()
        
    def load_personas(self, company_name: str, architecture: str) -> tuple[List[Dict], Optional[Dict]]:
        """加载某个公司在某个架构下的 personas 和 products"""
        company_dir = self.evaluation_dir / company_name
        
        # 尝试精确匹配
        target_dir = company_dir / architecture
        if not target_dir.exists():
            # 大小写不敏感匹配
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
                    if "result" in content and "personas" in content["result"]:
                        personas_data = content["result"]["personas"]
                    elif "personas" in content:
                        personas_data = content["personas"]
                elif "product" in filename:
                    if "result" in content and "products" in content["result"]:
                        products_data = content["result"]["products"]
                    elif "products" in content:
                        products_data = content["products"]
                elif "two_stage" in filename:
                    if "result" in content:
                        if "personas" in content["result"]:
                            personas_data = content["result"]["personas"]
                        if "products" in content.get("result", {}):
                            products_data = content["result"]["products"]
                elif "three_stage" in filename:
                    if "result" in content:
                        if not personas_data and "personas" in content["result"]:
                            personas_data = content["result"]["personas"]
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
                logger.error(f"Error loading {json_file}: {e}")
        
        return personas_data, products_data
    
    def evaluate_persona_with_llm(
        self,
        persona: Dict,
        products: Optional[List[Dict]] = None,
        company_name: str = ""
    ) -> Dict:
        """
        使用 LLM 评估单个 Persona 的质量
        
        Args:
            persona: Persona 数据字典
            products: 产品列表（可选）
            company_name: 公司名称（可选）
            
        Returns:
            评估结果字典
        """
        # 构建评估提示
        prompt = self._build_evaluation_prompt(persona, products, company_name)
        
        # 调用 LLM
        try:
            # 注意：某些模型（如 gpt-5-mini）不支持自定义 temperature
            # 使用 None 让服务使用默认值
            response = self.llm_service.generate(
                prompt=prompt,
                system_message=self._get_system_message(),
                temperature=None,  # 使用默认 temperature
                max_completion_tokens=3000  # 增加 token 限制以确保完整响应
            )
            
            # 解析 LLM 响应
            evaluation_result = self._parse_llm_response(response.content, persona)
            
            # 添加元数据
            evaluation_result["llm_metadata"] = {
                "model": response.model,
                "tokens_used": response.total_tokens,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens
            }
            
            return evaluation_result
            
        except Exception as e:
            logger.error(f"Error evaluating persona {persona.get('persona_name', 'Unknown')}: {e}")
            return {
                "persona_name": persona.get("persona_name", "Unknown"),
                "error": str(e),
                "scores": {},
                "feedback": []
            }
    
    def _get_system_message(self) -> str:
        """获取系统消息"""
        return """You are an expert in evaluating buyer personas for B2B sales and marketing. 
Your task is to evaluate persona quality across multiple dimensions and provide detailed, 
constructive feedback. Be objective, specific, and actionable in your assessments.

Always respond in JSON format with the following structure:
{
    "overall_score": <0-100>,
    "scores": {
        "description_quality": <0-100>,
        "job_titles_relevance": <0-100>,
        "name_quality": <0-100>,
        "product_alignment": <0-100>,
        "consistency": <0-100>,
        "practicality": <0-100>
    },
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...],
    "recommendations": ["recommendation1", "recommendation2", ...],
    "detailed_feedback": {
        "description": "detailed feedback on description quality",
        "job_titles": "detailed feedback on job titles",
        "name": "detailed feedback on persona name",
        "product_alignment": "detailed feedback on product alignment",
        "consistency": "detailed feedback on internal consistency",
        "practicality": "detailed feedback on practicality"
    }
}"""
    
    def _build_evaluation_prompt(
        self,
        persona: Dict,
        products: Optional[List[Dict]] = None,
        company_name: str = ""
    ) -> str:
        """构建评估提示"""
        
        # 准备产品信息
        products_text = ""
        if products:
            products_text = "\n\nProducts:\n"
            for p in products:
                products_text += f"- {p.get('product_name', 'Unknown')}: {p.get('description', 'No description')}\n"
        
        prompt = f"""Evaluate the quality of the following buyer persona:

Company: {company_name}
{products_text}

Persona Details:
- Name: {persona.get('persona_name', 'N/A')}
- Tier: {persona.get('tier', 'N/A')}
- Industry: {persona.get('industry', 'N/A')}
- Location: {persona.get('location', 'N/A')}
- Company Size: {persona.get('company_size_range', 'N/A')}
- Company Type: {persona.get('company_type', 'N/A')}
- Description: {persona.get('description', 'N/A')}
- Job Titles ({len(persona.get('job_titles', []))} total):
"""
        
        # 添加 job titles
        for i, jt in enumerate(persona.get('job_titles', [])[:20], 1):  # 限制显示前20个
            prompt += f"  {i}. {jt}\n"
        
        prompt += """
\nPlease evaluate this persona across the following dimensions using these specific criteria:

1. **Description Quality** (0-100):
   Give 90-100 points if:
   - ✅ Includes ALL 4 metrics: team size, deal size, sales cycle, stakeholders
   - ✅ Uses specific numbers (e.g., "10-15 reps" not "small team")
   - ✅ Written in clear, professional language
   - ✅ Includes pain points or buying triggers
   
   Give 70-89 points if:
   - ⚠️ Includes 3 of 4 metrics
   - ⚠️ Some vague language but mostly specific
   - ⚠️ Professional but could be clearer
   
   Give 50-69 points if:
   - ⚠️ Includes 2 of 4 metrics
   - ⚠️ Mostly vague descriptions
   
   Give below 50 if:
   - ❌ Missing most metrics
   - ❌ Very vague or poorly written

2. **Job Titles Relevance** (0-100):
   Give 90-100 points if:
   - ✅ ALL titles match the industry and persona description
   - ✅ Covers 4+ hierarchy levels (C-suite, VP, Director, Manager, Specialist)
   - ✅ No duplicate or near-duplicate titles
   - ✅ Realistic titles for the company size and industry
   
   Give 70-89 points if:
   - ⚠️ Most titles match (80%+)
   - ⚠️ Covers 3 hierarchy levels
   - ⚠️ Few duplicates (< 10%)
   
   Give 50-69 points if:
   - ⚠️ Some titles match (60-79%)
   - ⚠️ Limited hierarchy coverage (1-2 levels)
   - ⚠️ Some duplicates
   
   Give below 50 if:
   - ❌ Many irrelevant titles
   - ❌ All same level or too many duplicates

3. **Name Quality** (0-100):
   Standard format: "[Geography] [Size] [Industry] - [Function]"
   
   Give 90-100 points if:
   - ✅ Perfect format with all 4 components
   - ✅ 30-70 characters
   - ✅ Clear and readable
   - ✅ Unique and descriptive
   
   Give 70-89 points if:
   - ⚠️ Has 3 of 4 components
   - ⚠️ 20-80 characters
   - ⚠️ Mostly clear
   
   Give 50-69 points if:
   - ⚠️ Has 2 of 4 components
   - ⚠️ Too short or too long
   
   Give below 50 if:
   - ❌ Missing format or very unclear

4. **Product Alignment** (0-100):
   Give 90-100 points if:
   - ✅ Description explicitly mentions products by name
   - ✅ Clear use cases for the products
   - ✅ Persona's needs match product capabilities
   
   Give 70-89 points if:
   - ⚠️ Mentions product category (e.g., "CRM") but not specific products
   - ⚠️ Implied fit but not explicit
   
   Give 50-69 points if:
   - ⚠️ Vague connection to products
   
   Give below 50 if:
   - ❌ No clear connection to products

5. **Consistency** (0-100):
   Give 90-100 points if:
   - ✅ All fields align logically (e.g., Enterprise size → large deals)
   - ✅ Job titles match industry and description
   - ✅ No contradictions
   - ✅ All required fields present and meaningful
   
   Give 70-89 points if:
   - ⚠️ Minor inconsistencies
   - ⚠️ One field seems off
   
   Give 50-69 points if:
   - ⚠️ Multiple inconsistencies
   
   Give below 50 if:
   - ❌ Major contradictions or missing critical fields

6. **Practicality** (0-100):
   Give 90-100 points if:
   - ✅ Sales teams can immediately identify and target this persona
   - ✅ Specific enough to guide messaging and outreach
   - ✅ Realistic and achievable target
   - ✅ Clearly differentiated from other personas
   
   Give 70-89 points if:
   - ⚠️ Mostly actionable but some vague areas
   - ⚠️ Could be more specific
   
   Give 50-69 points if:
   - ⚠️ Too generic to be useful
   
   Give below 50 if:
   - ❌ Not actionable or unrealistic

**Important**: Be strict and objective. A score of 90+ should be reserved for truly excellent personas. Most good personas should score 70-85.

Provide your evaluation in JSON format as specified in the system message."""
        
        return prompt
    
    def _parse_llm_response(self, response_text: str, persona: Dict) -> Dict:
        """解析 LLM 响应"""
        import re
        
        # 保存原始响应（用于调试）
        raw_response = response_text
        
        try:
            # 尝试提取 JSON（可能包含在代码块中）
            # 首先尝试查找 JSON 代码块
            json_match = re.search(
                r'```(?:json)?\s*(\{.*?\})\s*```',
                response_text,
                re.DOTALL
            )
            
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接查找 JSON 对象（从第一个 { 到最后一个 }）
                # 使用更精确的匹配，考虑嵌套的 JSON
                brace_count = 0
                start_idx = response_text.find('{')
                if start_idx == -1:
                    raise ValueError("No JSON object found in response")
                
                end_idx = start_idx
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == '{':
                        brace_count += 1
                    elif response_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                
                if brace_count != 0:
                    # 如果括号不匹配，尝试找到最后一个 }
                    end_idx = response_text.rfind('}')
                    if end_idx > start_idx:
                        json_str = response_text[start_idx:end_idx + 1]
                    else:
                        raise ValueError("Invalid JSON structure")
                else:
                    json_str = response_text[start_idx:end_idx]
            
            # 清理 JSON 字符串（移除可能的尾随文本）
            json_str = json_str.strip()
            
            result = json.loads(json_str)
            
            # 添加 persona 信息
            result["persona_name"] = persona.get("persona_name", "Unknown")
            
            # 验证和规范化分数
            if "overall_score" not in result:
                result["overall_score"] = 0
            
            if "scores" not in result:
                result["scores"] = {}
            
            # 确保所有分数在 0-100 范围内
            result["overall_score"] = max(0, min(100, result.get("overall_score", 0)))
            for key in result["scores"]:
                if isinstance(result["scores"][key], (int, float)):
                    result["scores"][key] = max(0, min(100, result["scores"][key]))
            
            # 确保其他字段存在
            if "strengths" not in result:
                result["strengths"] = []
            if "weaknesses" not in result:
                result["weaknesses"] = []
            if "recommendations" not in result:
                result["recommendations"] = []
            if "detailed_feedback" not in result:
                result["detailed_feedback"] = {}
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            logger.debug(f"Response text (first 1000 chars): {raw_response[:1000]}")
            logger.debug(f"Response text (last 500 chars): {raw_response[-500:]}")
            
            # 返回基本结构，保存原始响应
            return {
                "persona_name": persona.get("persona_name", "Unknown"),
                "overall_score": 0,
                "scores": {},
                "strengths": [],
                "weaknesses": [],
                "recommendations": [],
                "detailed_feedback": {},
                "raw_response": raw_response[:2000],  # 保存前2000字符用于调试
                "parse_error": str(e)
            }
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response text (first 1000 chars): {raw_response[:1000]}")
            
            # 返回基本结构
            return {
                "persona_name": persona.get("persona_name", "Unknown"),
                "overall_score": 0,
                "scores": {},
                "strengths": [],
                "weaknesses": [],
                "recommendations": [],
                "detailed_feedback": {},
                "raw_response": raw_response[:2000],
                "parse_error": str(e)
            }
    
    def evaluate_all_personas(
        self,
        company_name: str,
        architecture: str = "4 Stage"
    ) -> Dict:
        """
        评估某个公司在某个架构下的所有 personas
        
        Args:
            company_name: 公司名称
            architecture: 架构名称（"2 Stage" 或 "4 Stage"）
            
        Returns:
            评估结果字典
        """
        personas, products = self.load_personas(company_name, architecture)
        
        if not personas:
            return {
                "company_name": company_name,
                "architecture": architecture,
                "error": f"No personas found for {company_name} in {architecture}",
                "persona_count": 0
            }
        
        results = {
            "company_name": company_name,
            "architecture": architecture,
            "persona_count": len(personas),
            "evaluation_timestamp": datetime.now().isoformat(),
            "personas": []
        }
        
        logger.info(f"Evaluating {len(personas)} personas for {company_name} ({architecture})...")
        
        # 评估每个 persona
        for i, persona in enumerate(personas, 1):
            logger.info(f"Evaluating persona {i}/{len(personas)}: {persona.get('persona_name', 'Unknown')}")
            
            evaluation = self.evaluate_persona_with_llm(
                persona=persona,
                products=products,
                company_name=company_name
            )
            
            results["personas"].append({
                "persona_data": persona,
                "evaluation": evaluation
            })
        
        # 计算汇总统计
        results["summary"] = self._calculate_summary(results["personas"])
        
        return results
    
    def _calculate_summary(self, persona_evaluations: List[Dict]) -> Dict:
        """计算汇总统计"""
        if not persona_evaluations:
            return {}
        
        overall_scores = []
        dimension_scores = {
            "description_quality": [],
            "job_titles_relevance": [],
            "name_quality": [],
            "product_alignment": [],
            "consistency": [],
            "practicality": []
        }
        
        for item in persona_evaluations:
            eval_data = item.get("evaluation", {})
            
            if "overall_score" in eval_data:
                overall_scores.append(eval_data["overall_score"])
            
            scores = eval_data.get("scores", {})
            for dim in dimension_scores:
                if dim in scores:
                    dimension_scores[dim].append(scores[dim])
        
        summary = {
            "average_overall_score": sum(overall_scores) / len(overall_scores) if overall_scores else 0,
            "min_overall_score": min(overall_scores) if overall_scores else 0,
            "max_overall_score": max(overall_scores) if overall_scores else 0,
            "dimension_averages": {}
        }
        
        for dim, scores_list in dimension_scores.items():
            if scores_list:
                summary["dimension_averages"][dim] = {
                    "average": sum(scores_list) / len(scores_list),
                    "min": min(scores_list),
                    "max": max(scores_list)
                }
        
        return summary
    
    def compare_architectures(
        self,
        company_name: str,
        architectures: List[str] = ["2 Stage", "4 Stage"]
    ) -> Dict:
        """
        对比不同架构的 Persona 质量
        
        Args:
            company_name: 公司名称
            architectures: 要对比的架构列表
            
        Returns:
            对比结果字典
        """
        comparison = {
            "company_name": company_name,
            "comparison_timestamp": datetime.now().isoformat(),
            "architectures": {}
        }
        
        for arch in architectures:
            logger.info(f"Evaluating {company_name} - {arch}...")
            results = self.evaluate_all_personas(company_name, arch)
            comparison["architectures"][arch] = results
        
        # 计算对比统计
        comparison["comparison_summary"] = self._compare_architectures_summary(
            comparison["architectures"]
        )
        
        return comparison
    
    def _compare_architectures_summary(self, architectures_data: Dict) -> Dict:
        """对比不同架构的汇总统计"""
        summary = {}
        
        for arch_name, arch_data in architectures_data.items():
            if "summary" in arch_data:
                summary[arch_name] = arch_data["summary"]
        
        # 计算差异
        if len(summary) == 2:
            arch_names = list(summary.keys())
            arch1_name, arch2_name = arch_names[0], arch_names[1]
            
            arch1_summary = summary[arch1_name]
            arch2_summary = summary[arch2_name]
            
            differences = {
                "overall_score_diff": (
                    arch2_summary.get("average_overall_score", 0) -
                    arch1_summary.get("average_overall_score", 0)
                )
            }
            
            # 计算各维度的差异
            differences["dimension_diffs"] = {}
            for dim in arch1_summary.get("dimension_averages", {}):
                if dim in arch2_summary.get("dimension_averages", {}):
                    arch1_avg = arch1_summary["dimension_averages"][dim]["average"]
                    arch2_avg = arch2_summary["dimension_averages"][dim]["average"]
                    differences["dimension_diffs"][dim] = arch2_avg - arch1_avg
            
            summary["differences"] = differences
        
        return summary


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="使用 LLM 评估 Persona 质量")
    parser.add_argument(
        "--company",
        type=str,
        help="要评估的公司名称（如果不指定，评估所有公司）"
    )
    parser.add_argument(
        "--architecture",
        type=str,
        default="4 Stage",
        help="架构名称（默认: 4 Stage）"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="对比不同架构（2 Stage vs 4 Stage）"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation_results",
        help="输出目录（默认: evaluation_results）"
    )
    args = parser.parse_args()
    
    evaluation_dir = Path("data/Evaluation")
    
    if not evaluation_dir.exists():
        print(f"❌ 评估目录不存在: {evaluation_dir}")
        return
    
    # 检查 API key
    if not settings.OPENAI_API_KEY:
        print("❌ 错误: 未设置 OPENAI_API_KEY")
        print("请在 .env 文件中设置 OPENAI_API_KEY")
        return
    
    evaluator = LLMPersonaEvaluator(evaluation_dir)
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.compare:
        # 对比不同架构
        if args.company:
            companies = [args.company]
        else:
            companies = [d.name for d in evaluation_dir.iterdir() if d.is_dir()]
        
        for company_name in companies:
            print(f"\n{'='*80}")
            print(f"对比评估: {company_name}")
            print(f"{'='*80}\n")
            
            comparison = evaluator.compare_architectures(
                company_name,
                architectures=["2 Stage", "4 Stage"]
            )
            
            # 保存结果
            output_file = output_dir / f"llm_persona_comparison_{company_name}_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 对比结果已保存到: {output_file}")
            
            # 打印汇总
            if "comparison_summary" in comparison:
                summary = comparison["comparison_summary"]
                print(f"\n汇总统计:")
                for arch_name, arch_summary in summary.items():
                    if arch_name != "differences":
                        print(f"\n{arch_name}:")
                        print(f"  平均总分: {arch_summary.get('average_overall_score', 0):.1f}/100")
                
                if "differences" in summary:
                    diffs = summary["differences"]
                    print(f"\n差异分析:")
                    print(f"  总分差异: {diffs.get('overall_score_diff', 0):+.1f}")
                    if "dimension_diffs" in diffs:
                        print(f"  各维度差异:")
                        for dim, diff in diffs["dimension_diffs"].items():
                            print(f"    {dim}: {diff:+.1f}")
    
    else:
        # 评估单个架构
        if args.company:
            companies = [args.company]
        else:
            companies = [d.name for d in evaluation_dir.iterdir() if d.is_dir()]
        
        for company_name in companies:
            print(f"\n{'='*80}")
            print(f"评估: {company_name} - {args.architecture}")
            print(f"{'='*80}\n")
            
            results = evaluator.evaluate_all_personas(company_name, args.architecture)
            
            # 保存结果
            output_file = output_dir / f"llm_persona_evaluation_{company_name}_{args.architecture.replace(' ', '_')}_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 评估结果已保存到: {output_file}")
            
            # 打印汇总
            if "summary" in results:
                summary = results["summary"]
                print(f"\n汇总统计:")
                print(f"  平均总分: {summary.get('average_overall_score', 0):.1f}/100")
                print(f"  最高分: {summary.get('max_overall_score', 0):.1f}/100")
                print(f"  最低分: {summary.get('min_overall_score', 0):.1f}/100")
                
                if "dimension_averages" in summary:
                    print(f"\n各维度平均分:")
                    for dim, stats in summary["dimension_averages"].items():
                        print(f"  {dim}: {stats['average']:.1f}/100 (范围: {stats['min']:.1f}-{stats['max']:.1f})")


if __name__ == "__main__":
    main()

