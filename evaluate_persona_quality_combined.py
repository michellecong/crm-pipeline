#!/usr/bin/env python3
"""
Combined Persona Quality Evaluation Script

结合传统规则评估和 LLM 智能评估，生成综合质量分数。
结合两种方法的优势：
- 传统评估：量化指标、可复现性
- LLM 评估：语义理解、逻辑一致性
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from evaluate_persona_quality import PersonaQualityEvaluator
from evaluate_persona_quality_llm import LLMPersonaEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CombinedPersonaEvaluator:
    """结合传统规则和 LLM 评估的综合评估器"""
    
    def __init__(
        self,
        evaluation_dir: Path,
        traditional_weight: float = 0.4,
        llm_weight: float = 0.6,
        llm_service=None,
        llm_results_dir: Optional[Path] = None,
        use_cached_llm: bool = True
    ):
        """
        初始化综合评估器
        
        Args:
            evaluation_dir: 评估数据目录
            traditional_weight: 传统评估的权重（默认 0.4）
            llm_weight: LLM 评估的权重（默认 0.6）
            llm_service: LLM 服务实例（可选）
            llm_results_dir: LLM 评估结果目录（用于缓存，默认: evaluation_results）
            use_cached_llm: 是否使用缓存的 LLM 评估结果（默认: True）
        """
        self.evaluation_dir = evaluation_dir
        self.traditional_weight = traditional_weight
        self.llm_weight = llm_weight
        self.use_cached_llm = use_cached_llm
        
        # 确保权重和为 1.0
        total_weight = traditional_weight + llm_weight
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(
                f"Weights sum to {total_weight}, normalizing to 1.0"
            )
            self.traditional_weight /= total_weight
            self.llm_weight /= total_weight
        
        # 初始化两个评估器
        self.traditional_evaluator = PersonaQualityEvaluator(evaluation_dir)
        self.llm_evaluator = LLMPersonaEvaluator(evaluation_dir, llm_service)
        
        # LLM 结果目录（用于查找缓存）
        if llm_results_dir is None:
            self.llm_results_dir = Path("evaluation_results")
        else:
            self.llm_results_dir = Path(llm_results_dir)
    
    def normalize_traditional_score(self, score: float) -> float:
        """
        将传统评估的分数（0-100）归一化
        
        传统评估的分数范围通常是 60-90，需要映射到 0-100
        """
        # 假设传统评估的合理范围是 50-100
        # 将 50-100 映射到 0-100
        if score < 50:
            return max(0, score * 0.8)  # 低于50分按比例压缩
        else:
            return score
    
    def normalize_llm_score(self, score: float) -> float:
        """
        将 LLM 评估的分数（0-100）归一化
        
        LLM 评估的分数范围通常是 70-95，需要映射到 0-100
        """
        # LLM 评估通常分数较高，可能需要稍微调整
        # 但通常已经在 0-100 范围内，直接返回
        return score
    
    def combine_scores(
        self,
        traditional_score: float,
        llm_score: float,
        use_llm_only_for_overlap: bool = True
    ) -> Dict:
        """
        结合传统评估和 LLM 评估的分数
        
        Args:
            traditional_score: 传统评估分数（0-100）
            llm_score: LLM 评估分数（0-100）
            use_llm_only_for_overlap: 对于重叠的指标，是否只使用 LLM 评估（默认: True）
            
        Returns:
            综合评估结果字典
        """
        # 归一化分数
        norm_traditional = self.normalize_traditional_score(traditional_score)
        norm_llm = self.normalize_llm_score(llm_score)
        
        # 如果启用"重叠指标只用 LLM"，则只使用 LLM 分数
        # 因为重叠指标（Product Alignment, Description, Job Titles, Name）在 LLM 评估中更准确
        if use_llm_only_for_overlap:
            combined_score = norm_llm
            traditional_contribution = 0.0
            llm_contribution = norm_llm
        else:
            # 计算加权平均（旧方法）
            combined_score = (
                norm_traditional * self.traditional_weight +
                norm_llm * self.llm_weight
            )
            traditional_contribution = norm_traditional * self.traditional_weight
            llm_contribution = norm_llm * self.llm_weight
        
        return {
            "combined_score": round(combined_score, 2),
            "traditional_score": round(norm_traditional, 2),
            "llm_score": round(norm_llm, 2),
            "traditional_weight": self.traditional_weight,
            "llm_weight": self.llm_weight,
            "use_llm_only_for_overlap": use_llm_only_for_overlap,
            "score_breakdown": {
                "traditional_contribution": round(traditional_contribution, 2),
                "llm_contribution": round(llm_contribution, 2)
            }
        }
    
    def evaluate_company(
        self,
        company_name: str,
        architecture: str = "4 Stage"
    ) -> Dict:
        """
        评估某个公司在某个架构下的 Persona 质量
        
        Args:
            company_name: 公司名称
            architecture: 架构名称
            
        Returns:
            综合评估结果
        """
        logger.info(f"Evaluating {company_name} - {architecture} (Combined)")
        
        # 1. 传统评估
        logger.info("Running traditional evaluation...")
        traditional_results = self.traditional_evaluator.evaluate_all(company_name)
        
        # 获取指定架构的绝对总分
        architecture_key = "two_stage" if architecture == "2 Stage" else "four_stage"
        architecture_data = traditional_results.get(architecture_key, {})
        
        if not architecture_data:
            return {
                "company_name": company_name,
                "architecture": architecture,
                "error": f"No data found for {architecture}",
                "combined_score": 0
            }
        
        traditional_absolute = self.traditional_evaluator.calculate_absolute_score(
            architecture_data, architecture
        )
        traditional_total = traditional_absolute.get("total_score", 0)
        
        # 2. LLM 评估（尝试使用缓存）
        llm_results = None
        
        if self.use_cached_llm:
            # 尝试从已有结果文件中加载
            cached_result = self._load_cached_llm_result(company_name, architecture)
            if cached_result:
                logger.info(f"Using cached LLM evaluation result for {company_name} - {architecture}")
                llm_results = cached_result
            else:
                logger.info(f"No cached LLM result found, running LLM evaluation...")
        
        if llm_results is None:
            logger.info("Running LLM evaluation...")
            llm_results = self.llm_evaluator.evaluate_all_personas(
                company_name, architecture
            )
        
        if "error" in llm_results:
            logger.warning(f"LLM evaluation failed: {llm_results['error']}")
            # 如果 LLM 评估失败，只使用传统评估
            return {
                "company_name": company_name,
                "architecture": architecture,
                "combined_score": self.normalize_traditional_score(traditional_total),
                "traditional_score": self.normalize_traditional_score(traditional_total),
                "llm_score": None,
                "llm_error": llm_results.get("error"),
                "traditional_details": traditional_absolute
            }
        
        llm_summary = llm_results.get("summary", {})
        llm_total = llm_summary.get("average_overall_score", 0)
        
        # 3. 计算综合分数
        # 策略：对于重叠的指标，只使用 LLM 评估（更准确）
        # 传统评估只保留独有的指标（Diversity, Generation Reasoning）
        
        # 提取传统评估独有的指标分数
        traditional_unique_scores = traditional_absolute.get("scores", {})
        diversity_score = traditional_unique_scores.get("diversity", {}).get("score", 0)
        diversity_max = traditional_unique_scores.get("diversity", {}).get("max_score", 20)
        reasoning_score = traditional_unique_scores.get("generation_reasoning", {}).get("score", 0)
        reasoning_max = traditional_unique_scores.get("generation_reasoning", {}).get("max_score", 10)
        
        # 归一化传统评估独有的指标（Diversity + Generation Reasoning = 30分）
        norm_diversity = (diversity_score / diversity_max * 100) if diversity_max > 0 else 0
        norm_reasoning = (reasoning_score / reasoning_max * 100) if reasoning_max > 0 else 0
        
        # 传统评估独有的指标权重（30分 / 100分 = 30%）
        traditional_unique_weight = 0.30
        # LLM 评估权重（重叠指标 + LLM 独有指标 = 70%）
        llm_weight_for_combined = 0.70
        
        # 综合分数 = LLM 评估分数（重叠指标）* 70% + 传统评估独有指标 * 30%
        combined_score = (
            llm_total * llm_weight_for_combined +
            (norm_diversity + norm_reasoning) / 2 * traditional_unique_weight
        )
        
        combined = {
            "combined_score": round(combined_score, 2),
            "traditional_score": round(traditional_total, 2),
            "llm_score": round(llm_total, 2),
            "traditional_weight": traditional_unique_weight,
            "llm_weight": llm_weight_for_combined,
            "use_llm_only_for_overlap": True,
            "score_breakdown": {
                "llm_contribution": round(llm_total * llm_weight_for_combined, 2),
                "traditional_unique_contribution": round(
                    (norm_diversity + norm_reasoning) / 2 * traditional_unique_weight, 2
                ),
                "diversity_score": round(norm_diversity, 2),
                "reasoning_score": round(norm_reasoning, 2)
            }
        }
        
        # 4. 按维度结合（如果可能）
        dimension_scores = self._combine_dimensions(
            traditional_absolute,
            llm_summary
        )
        
        return {
            "company_name": company_name,
            "architecture": architecture,
            "evaluation_timestamp": datetime.now().isoformat(),
            **combined,
            "dimension_scores": dimension_scores,
            "traditional_details": traditional_absolute,
            "llm_details": llm_summary,
            "persona_count": llm_results.get("persona_count", 0)
        }
    
    def _combine_dimensions(
        self,
        traditional_absolute: Dict,
        llm_summary: Dict
    ) -> Dict:
        """
        按维度结合传统评估和 LLM 评估的分数
        
        Args:
            traditional_absolute: 传统评估的绝对分数详情
            llm_summary: LLM 评估的汇总结果
            
        Returns:
            各维度的综合分数
        """
        dimension_mapping = {
            # 传统评估维度 -> LLM 评估维度
            # 重叠的指标：只使用 LLM 评估（更准确）
            "product_alignment": "product_alignment",  # 重叠：只用 LLM
            "description_completeness": "description_quality",  # 重叠：只用 LLM
            "job_titles_quality": "job_titles_relevance",  # 重叠：只用 LLM
            "persona_name_quality": "name_quality",  # 重叠：只用 LLM
            "field_completeness": "consistency",  # 部分重叠：只用 LLM
            # 传统评估独有的指标：只使用传统评估
            "diversity": None,  # LLM 评估没有直接对应的维度（传统独有）
            "generation_reasoning": None,  # LLM 评估没有直接对应的维度（传统独有）
        }
        
        combined_dimensions = {}
        
        # 获取传统评估的各维度分数（0-100 归一化）
        traditional_scores = traditional_absolute.get("scores", {})
        
        # 获取 LLM 评估的各维度平均分
        llm_dimensions = llm_summary.get("dimension_averages", {})
        
        # 结合每个维度
        for trad_dim, llm_dim in dimension_mapping.items():
            if trad_dim in traditional_scores:
                trad_score_data = traditional_scores[trad_dim]
                trad_max = trad_score_data.get("max_score", 100)
                trad_score = trad_score_data.get("score", 0)
                
                # 归一化传统评估分数到 0-100
                if trad_max > 0:
                    norm_trad = (trad_score / trad_max) * 100
                else:
                    norm_trad = 0
                
                # 获取 LLM 评估分数
                if llm_dim and llm_dim in llm_dimensions:
                    llm_avg = llm_dimensions[llm_dim].get("average", 0)
                    
                    # 对于重叠的指标，只使用 LLM 评估（因为 LLM 更准确）
                    # 重叠指标包括：product_alignment, description_completeness, 
                    # job_titles_quality, persona_name_quality, field_completeness
                    if trad_dim in ["product_alignment", "description_completeness", 
                                   "job_titles_quality", "persona_name_quality", 
                                   "field_completeness"]:
                        # 重叠指标：只使用 LLM 评估
                        combined = llm_avg
                        note = "Overlapping metric: using LLM only (more accurate)"
                    else:
                        # 非重叠指标：使用加权平均（虽然当前没有这种情况）
                        combined = (
                            norm_trad * self.traditional_weight +
                            llm_avg * self.llm_weight
                        )
                        note = None
                    
                    combined_dimensions[trad_dim] = {
                        "combined_score": round(combined, 2),
                        "traditional_score": round(norm_trad, 2),
                        "llm_score": round(llm_avg, 2),
                        "llm_dimension": llm_dim,
                        "note": note if note else None
                    }
                else:
                    # 如果 LLM 评估没有对应维度，只使用传统评估
                    combined_dimensions[trad_dim] = {
                        "combined_score": round(norm_trad, 2),
                        "traditional_score": round(norm_trad, 2),
                        "llm_score": None,
                        "note": "No LLM equivalent dimension"
                    }
        
        # 添加 LLM 特有的维度（Consistency, Practicality）
        if "consistency" in llm_dimensions:
            consistency_avg = llm_dimensions["consistency"].get("average", 0)
            combined_dimensions["consistency"] = {
                "combined_score": round(consistency_avg, 2),
                "traditional_score": None,
                "llm_score": round(consistency_avg, 2),
                "note": "LLM-only dimension"
            }
        
        if "practicality" in llm_dimensions:
            practicality_avg = llm_dimensions["practicality"].get("average", 0)
            combined_dimensions["practicality"] = {
                "combined_score": round(practicality_avg, 2),
                "traditional_score": None,
                "llm_score": round(practicality_avg, 2),
                "note": "LLM-only dimension"
            }
        
        return combined_dimensions
    
    def _load_cached_llm_result(
        self,
        company_name: str,
        architecture: str
    ) -> Optional[Dict]:
        """
        从已有结果文件中加载 LLM 评估结果
        
        支持多种文件格式：
        1. llm_persona_evaluation_<company>_<architecture>_*.json (单个架构评估)
        2. llm_persona_comparison_<company>_*.json (对比结果，包含多个架构)
        
        Args:
            company_name: 公司名称
            architecture: 架构名称
            
        Returns:
            LLM 评估结果字典，如果找不到则返回 None
        """
        if not self.llm_results_dir.exists():
            return None
        
        # 方法1: 查找单个架构的评估结果文件
        # 文件名格式: llm_persona_evaluation_<company>_<architecture>_*.json
        arch_normalized = architecture.replace(" ", "_")
        pattern1 = f"llm_persona_evaluation_{company_name}_{arch_normalized}_*.json"
        
        matching_files = sorted(
            self.llm_results_dir.glob(pattern1),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # 最新的在前
        )
        
        if matching_files:
            latest_file = matching_files[0]
            try:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # 验证数据是否完整
                if ("summary" in cached_data and 
                    "personas" in cached_data and
                    cached_data.get("company_name") == company_name and
                    cached_data.get("architecture") == architecture):
                    logger.info(f"Loaded cached LLM result from {latest_file.name}")
                    return cached_data
                else:
                    logger.warning(f"Cached file {latest_file.name} format invalid, ignoring")
            except Exception as e:
                logger.warning(f"Failed to load cached LLM result from {latest_file}: {e}")
        
        # 方法2: 从对比结果文件中提取单个架构的数据
        # 文件名格式: llm_persona_comparison_<company>_*.json
        pattern2 = f"llm_persona_comparison_{company_name}_*.json"
        comparison_files = sorted(
            self.llm_results_dir.glob(pattern2),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for comp_file in comparison_files:
            try:
                with open(comp_file, 'r', encoding='utf-8') as f:
                    comp_data = json.load(f)
                
                # 检查是否包含指定架构的数据
                if (comp_data.get("company_name") == company_name and
                    "architectures" in comp_data and
                    architecture in comp_data["architectures"]):
                    
                    arch_data = comp_data["architectures"][architecture]
                    
                    # 构建符合期望格式的结果
                    # 需要包含 summary 和 personas
                    if "summary" in arch_data and "personas" in arch_data:
                        result = {
                            "company_name": company_name,
                            "architecture": architecture,
                            "summary": arch_data["summary"],
                            "personas": arch_data["personas"],
                            "persona_count": arch_data.get("persona_count", len(arch_data.get("personas", [])))
                        }
                        logger.info(f"Extracted LLM result for {architecture} from comparison file {comp_file.name}")
                        return result
                    elif "summary" in arch_data:
                        # 如果只有 summary，也返回（但缺少 personas 详情）
                        result = {
                            "company_name": company_name,
                            "architecture": architecture,
                            "summary": arch_data["summary"],
                            "personas": [],
                            "persona_count": arch_data.get("persona_count", 0)
                        }
                        logger.info(f"Extracted LLM summary for {architecture} from comparison file {comp_file.name} (no persona details)")
                        return result
            except Exception as e:
                logger.warning(f"Failed to load comparison file {comp_file}: {e}")
                continue
        
        return None
    
    def _load_cached_combined_result(
        self,
        company_name: str
    ) -> Optional[Dict]:
        """
        从已有结果文件中加载综合评估结果（如果已存在）
        
        Args:
            company_name: 公司名称
            
        Returns:
            综合评估结果字典，如果找不到则返回 None
        """
        if not self.llm_results_dir.exists():
            return None
        
        # 查找综合评估对比结果文件
        # 文件名格式: combined_persona_comparison_<company>_*.json
        pattern = f"combined_persona_comparison_{company_name}_*.json"
        
        matching_files = sorted(
            self.llm_results_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # 最新的在前
        )
        
        if matching_files:
            latest_file = matching_files[0]
            try:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # 验证数据是否完整
                if (cached_data.get("company_name") == company_name and
                    "architectures" in cached_data):
                    logger.info(f"Found cached combined result from {latest_file.name}")
                    return cached_data
            except Exception as e:
                logger.warning(f"Failed to load cached combined result from {latest_file}: {e}")
        
        return None
    
    def compare_architectures(
        self,
        company_name: str,
        architectures: List[str] = ["2 Stage", "4 Stage"],
        use_cached: bool = True
    ) -> Dict:
        """
        对比不同架构的综合评估结果
        
        Args:
            company_name: 公司名称
            architectures: 要对比的架构列表
            use_cached: 是否使用已有的综合评估结果（默认: True）
            
        Returns:
            对比结果字典
        """
        # 如果启用缓存，先尝试加载已有的综合评估结果
        if use_cached:
            cached_comparison = self._load_cached_combined_result(company_name)
            if cached_comparison:
                # 检查是否包含所有需要的架构
                cached_archs = set(cached_comparison.get("architectures", {}).keys())
                required_archs = set(architectures)
                
                if required_archs.issubset(cached_archs):
                    logger.info(f"Using cached combined comparison result for {company_name}")
                    # 更新时间戳
                    cached_comparison["comparison_timestamp"] = datetime.now().isoformat()
                    return cached_comparison
                else:
                    logger.info(f"Cached result missing some architectures, will recompute")
        
        comparison = {
            "company_name": company_name,
            "comparison_timestamp": datetime.now().isoformat(),
            "architectures": {},
            "comparison_summary": {}
        }
        
        results = {}
        for arch in architectures:
            logger.info(f"Evaluating {company_name} - {arch}...")
            result = self.evaluate_company(company_name, arch)
            results[arch] = result
            comparison["architectures"][arch] = result
        
        # 计算对比统计
        if len(results) == 2:
            arch_names = list(results.keys())
            arch1_name, arch2_name = arch_names[0], arch_names[1]
            
            arch1_score = results[arch1_name].get("combined_score", 0)
            arch2_score = results[arch2_name].get("combined_score", 0)
            
            comparison["comparison_summary"] = {
                arch1_name: {
                    "combined_score": arch1_score,
                    "traditional_score": results[arch1_name].get("traditional_score", 0),
                    "llm_score": results[arch1_name].get("llm_score", 0)
                },
                arch2_name: {
                    "combined_score": arch2_score,
                    "traditional_score": results[arch2_name].get("traditional_score", 0),
                    "llm_score": results[arch2_name].get("llm_score", 0)
                },
                "difference": {
                    "combined_score_diff": arch2_score - arch1_score,
                    "traditional_score_diff": (
                        results[arch2_name].get("traditional_score", 0) -
                        results[arch1_name].get("traditional_score", 0)
                    ),
                    "llm_score_diff": (
                        results[arch2_name].get("llm_score", 0) -
                        results[arch1_name].get("llm_score", 0)
                    )
                }
            }
        
        return comparison
    
    def batch_compare_all_companies(
        self,
        companies: Optional[List[str]] = None,
        architectures: List[str] = ["2 Stage", "4 Stage"]
    ) -> Dict:
        """
        批量比较所有公司的评估结果
        
        Args:
            companies: 要比较的公司列表（如果为 None，则从结果文件中自动发现）
            architectures: 要对比的架构列表
            
        Returns:
            批量对比结果字典
        """
        # 如果没有指定公司列表，从结果文件中自动发现
        if companies is None:
            companies = self._discover_companies_from_results()
        
        logger.info(f"Batch comparing {len(companies)} companies")
        
        batch_result = {
            "batch_comparison_timestamp": datetime.now().isoformat(),
            "companies": {},
            "summary_statistics": {},
            "rankings": {}
        }
        
        all_scores = {arch: [] for arch in architectures}
        
        # 评估每个公司
        for company_name in companies:
            logger.info(f"Processing {company_name}...")
            comparison = self.compare_architectures(
                company_name,
                architectures=architectures,
                use_cached=True
            )
            
            batch_result["companies"][company_name] = comparison
            
            # 收集分数用于统计
            for arch in architectures:
                if arch in comparison.get("architectures", {}):
                    arch_data = comparison["architectures"][arch]
                    score = arch_data.get("combined_score", 0)
                    all_scores[arch].append({
                        "company": company_name,
                        "score": score,
                        "traditional_score": arch_data.get("traditional_score", 0),
                        "llm_score": arch_data.get("llm_score", 0)
                    })
        
        # 计算汇总统计
        for arch in architectures:
            scores = [s["score"] for s in all_scores[arch]]
            if scores:
                batch_result["summary_statistics"][arch] = {
                    "count": len(scores),
                    "mean": round(sum(scores) / len(scores), 2),
                    "min": round(min(scores), 2),
                    "max": round(max(scores), 2),
                    "std": round(
                        (sum((x - sum(scores) / len(scores))**2 for x in scores) / len(scores))**0.5,
                        2
                    ) if len(scores) > 1 else 0
                }
        
        # 生成排名
        for arch in architectures:
            sorted_scores = sorted(
                all_scores[arch],
                key=lambda x: x["score"],
                reverse=True
            )
            batch_result["rankings"][arch] = [
                {
                    "rank": i + 1,
                    "company": item["company"],
                    "combined_score": item["score"],
                    "traditional_score": item["traditional_score"],
                    "llm_score": item["llm_score"]
                }
                for i, item in enumerate(sorted_scores)
            ]
        
        # 计算架构差异统计
        if len(architectures) == 2:
            differences = []
            for company_name in companies:
                comp = batch_result["companies"][company_name]
                if "comparison_summary" in comp and "difference" in comp["comparison_summary"]:
                    diff = comp["comparison_summary"]["difference"]
                    differences.append({
                        "company": company_name,
                        "combined_score_diff": diff.get("combined_score_diff", 0),
                        "traditional_score_diff": diff.get("traditional_score_diff", 0),
                        "llm_score_diff": diff.get("llm_score_diff", 0)
                    })
            
            if differences:
                batch_result["summary_statistics"]["architecture_differences"] = {
                    "mean_combined_diff": round(
                        sum(d["combined_score_diff"] for d in differences) / len(differences),
                        2
                    ),
                    "mean_traditional_diff": round(
                        sum(d["traditional_score_diff"] for d in differences) / len(differences),
                        2
                    ),
                    "mean_llm_diff": round(
                        sum(d["llm_score_diff"] for d in differences) / len(differences),
                        2
                    ),
                    "companies_improved": len([d for d in differences if d["combined_score_diff"] > 0]),
                    "companies_degraded": len([d for d in differences if d["combined_score_diff"] < 0]),
                    "companies_same": len([d for d in differences if d["combined_score_diff"] == 0])
                }
        
        return batch_result
    
    def _discover_companies_from_results(self) -> List[str]:
        """
        从结果文件中自动发现所有公司名称
        
        Returns:
            公司名称列表
        """
        if not self.llm_results_dir.exists():
            return []
        
        companies = set()
        
        # 从 llm_persona_comparison 文件中提取公司名称
        pattern = "llm_persona_comparison_*.json"
        for file_path in self.llm_results_dir.glob(pattern):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "company_name" in data:
                        companies.add(data["company_name"])
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
        
        # 从 combined_persona_comparison 文件中提取公司名称
        pattern = "combined_persona_comparison_*.json"
        for file_path in self.llm_results_dir.glob(pattern):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "company_name" in data:
                        companies.add(data["company_name"])
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
        
        return sorted(list(companies))


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="结合传统规则和 LLM 评估 Persona 质量"
    )
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
        "--batch-compare",
        action="store_true",
        help="批量比较所有公司的评估结果"
    )
    parser.add_argument(
        "--traditional-weight",
        type=float,
        default=0.4,
        help="传统评估的权重（默认: 0.4）"
    )
    parser.add_argument(
        "--llm-weight",
        type=float,
        default=0.6,
        help="LLM 评估的权重（默认: 0.6）"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation_results",
        help="输出目录（默认: evaluation_results）"
    )
    parser.add_argument(
        "--use-cached-llm",
        action="store_true",
        default=True,
        help="使用缓存的 LLM 评估结果（默认: True）"
    )
    parser.add_argument(
        "--no-cached-llm",
        dest="use_cached_llm",
        action="store_false",
        help="不使用缓存的 LLM 评估结果，重新运行评估"
    )
    parser.add_argument(
        "--use-cached-combined",
        action="store_true",
        default=True,
        help="使用缓存的综合评估结果（默认: True）"
    )
    parser.add_argument(
        "--no-cached-combined",
        dest="use_cached_combined",
        action="store_false",
        help="不使用缓存的综合评估结果，重新计算"
    )
    args = parser.parse_args()
    
    evaluation_dir = Path("data/Evaluation")
    
    if not evaluation_dir.exists():
        print(f"❌ 评估目录不存在: {evaluation_dir}")
        return
    
    # 检查 API key（如果需要 LLM 评估）
    if args.llm_weight > 0:
        from app.config import settings
        if not settings.OPENAI_API_KEY:
            print("⚠️  警告: 未设置 OPENAI_API_KEY，LLM 评估将失败")
            print("   将只使用传统评估")
    
    evaluator = CombinedPersonaEvaluator(
        evaluation_dir,
        traditional_weight=args.traditional_weight,
        llm_weight=args.llm_weight,
        llm_results_dir=Path(args.output_dir),
        use_cached_llm=args.use_cached_llm
    )
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{'='*80}")
    print("综合评估配置")
    print(f"{'='*80}")
    print(f"传统评估权重: {args.traditional_weight}")
    print(f"LLM 评估权重: {args.llm_weight}")
    print(f"使用 LLM 缓存: {args.use_cached_llm}")
    if args.use_cached_llm:
        print("  → 如果已有 LLM 评估结果，将直接使用，不重复调用 API")
        print("  → 支持从以下文件加载:")
        print("    - llm_persona_evaluation_<company>_<architecture>_*.json")
        print("    - llm_persona_comparison_<company>_*.json")
    else:
        print("  → 将重新运行 LLM 评估（会调用 API）")
    print(f"使用综合评估缓存: {args.use_cached_combined}")
    if args.use_cached_combined:
        print("  → 如果已有综合评估结果，将直接使用，不重复计算")
        print("  → 支持从以下文件加载:")
        print("    - combined_persona_comparison_<company>_*.json")
    else:
        print("  → 将重新计算综合评估结果")
    print(f"{'='*80}\n")
    
    if args.batch_compare:
        # 批量比较所有公司
        print(f"\n{'='*80}")
        print("批量比较所有公司")
        print(f"{'='*80}\n")
        
        # 如果指定了公司，只比较指定的公司；否则自动发现所有公司
        if args.company:
            companies = [args.company]
        else:
            companies = None  # 让函数自动发现
        
        batch_result = evaluator.batch_compare_all_companies(
            companies=companies,
            architectures=["2 Stage", "4 Stage"]
        )
        
        # 保存结果
        output_file = output_dir / f"combined_persona_batch_comparison_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(batch_result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 批量对比结果已保存到: {output_file}\n")
        
        # 打印汇总统计
        if "summary_statistics" in batch_result:
            stats = batch_result["summary_statistics"]
            print("="*80)
            print("汇总统计")
            print("="*80)
            
            for arch in ["2 Stage", "4 Stage"]:
                if arch in stats:
                    arch_stats = stats[arch]
                    print(f"\n{arch}:")
                    print(f"  公司数量: {arch_stats.get('count', 0)}")
                    print(f"  平均分数: {arch_stats.get('mean', 0):.2f}/100")
                    print(f"  最高分: {arch_stats.get('max', 0):.2f}/100")
                    print(f"  最低分: {arch_stats.get('min', 0):.2f}/100")
                    print(f"  标准差: {arch_stats.get('std', 0):.2f}")
            
            if "architecture_differences" in stats:
                diff_stats = stats["architecture_differences"]
                print(f"\n架构差异统计 (4 Stage - 2 Stage):")
                print(f"  平均综合分数差异: {diff_stats.get('mean_combined_diff', 0):+.2f} 分")
                print(f"  平均传统评估差异: {diff_stats.get('mean_traditional_diff', 0):+.2f} 分")
                print(f"  平均 LLM 评估差异: {diff_stats.get('mean_llm_diff', 0):+.2f} 分")
                print(f"  改进的公司数: {diff_stats.get('companies_improved', 0)}")
                print(f"  退步的公司数: {diff_stats.get('companies_degraded', 0)}")
                print(f"  持平的公司数: {diff_stats.get('companies_same', 0)}")
        
        # 打印排名
        if "rankings" in batch_result:
            print(f"\n{'='*80}")
            print("公司排名")
            print(f"{'='*80}")
            
            for arch in ["2 Stage", "4 Stage"]:
                if arch in batch_result["rankings"]:
                    print(f"\n{arch} 排名:")
                    rankings = batch_result["rankings"][arch]
                    for rank_info in rankings[:10]:  # 只显示前10名
                        print(f"  {rank_info['rank']}. {rank_info['company']}: "
                              f"{rank_info['combined_score']:.1f}/100 "
                              f"(传统: {rank_info['traditional_score']:.1f}, "
                              f"LLM: {rank_info['llm_score']:.1f})")
    
    elif args.compare:
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
                architectures=["2 Stage", "4 Stage"],
                use_cached=args.use_cached_combined
            )
            
            # 保存结果
            output_file = output_dir / f"combined_persona_comparison_{company_name}_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 对比结果已保存到: {output_file}")
            
            # 打印汇总
            if "comparison_summary" in comparison:
                summary = comparison["comparison_summary"]
                print(f"\n汇总统计:")
                
                for arch_name in ["2 Stage", "4 Stage"]:
                    if arch_name in summary:
                        arch_summary = summary[arch_name]
                        print(f"\n{arch_name}:")
                        print(f"  综合分数: {arch_summary.get('combined_score', 0):.1f}/100")
                        print(f"  传统评估: {arch_summary.get('traditional_score', 0):.1f}/100")
                        print(f"  LLM 评估: {arch_summary.get('llm_score', 0):.1f}/100")
                
                if "difference" in summary:
                    diffs = summary["difference"]
                    print(f"\n差异分析 (4 Stage - 2 Stage):")
                    print(f"  综合分数差异: {diffs.get('combined_score_diff', 0):+.1f} 分")
                    print(f"  传统评估差异: {diffs.get('traditional_score_diff', 0):+.1f} 分")
                    print(f"  LLM 评估差异: {diffs.get('llm_score_diff', 0):+.1f} 分")
    
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
            
            result = evaluator.evaluate_company(company_name, args.architecture)
            
            # 保存结果
            output_file = output_dir / f"combined_persona_evaluation_{company_name}_{args.architecture.replace(' ', '_')}_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 评估结果已保存到: {output_file}")
            
            # 打印汇总
            print(f"\n综合评估结果:")
            print(f"  综合分数: {result.get('combined_score', 0):.1f}/100")
            print(f"  传统评估: {result.get('traditional_score', 0):.1f}/100")
            print(f"  LLM 评估: {result.get('llm_score', 0):.1f}/100")
            
            if "dimension_scores" in result:
                print(f"\n各维度综合分数:")
                for dim, scores in result["dimension_scores"].items():
                    combined = scores.get("combined_score", 0)
                    trad = scores.get("traditional_score", "N/A")
                    llm = scores.get("llm_score", "N/A")
                    print(f"  {dim}: {combined:.1f}/100 (传统: {trad}, LLM: {llm})")


if __name__ == "__main__":
    main()

