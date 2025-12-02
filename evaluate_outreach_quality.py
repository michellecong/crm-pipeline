#!/usr/bin/env python3
"""
Outreach Quality Evaluation Script

评估 Outreach Sequences 的质量，包括：
1. 序列结构质量（touches 数量、duration、timing 是否正确）
2. Touch 类型多样性（email, linkedin, phone 的分布）
3. 内容质量（subject line 长度、内容个性化、是否引用 pain points）
4. 与 Persona/Mappings 的匹配度
5. 序列的连贯性和渐进性

支持两种评估模式：
- 传统模式（默认）：基于规则和模式匹配
- LLM 模式（--use-llm）：使用 LLM 进行语义理解和智能评估
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
    import os
    current_file = Path(__file__).absolute()
    project_root = current_file.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from app.services.llm_service import LLMService
    from app.config import settings
    HAS_LLM = True
except (ImportError, Exception) as e:
    HAS_LLM = False
    pass


class OutreachQualityEvaluator:
    """评估 Outreach Sequence 质量的类"""
    
    def __init__(self, evaluation_dir: Path, use_llm: bool = False):
        self.evaluation_dir = evaluation_dir
        self.use_llm = use_llm and HAS_LLM
        
        # 初始化 LLM 服务（如果启用）
        if self.use_llm:
            try:
                self.llm_service = LLMService()
                print("✅ LLM 评估模式已启用")
            except Exception as e:
                print(f"⚠️  LLM 服务初始化失败: {e}，将使用传统评估模式")
                self.use_llm = False
    
    def load_outreach_and_mappings(self, company_name: str, architecture: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """加载某个公司在某个架构下的 outreach sequences、mappings 和 personas"""
        company_dir = self.evaluation_dir / company_name / architecture
        
        if not company_dir.exists():
            return [], [], []
        
        sequences_data = []
        mappings_data = []
        personas_data = []
        
        # 加载所有JSON文件
        for json_file in company_dir.glob("*.json"):
            filename = json_file.stem.lower()
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                if "outreach" in filename or "sequence" in filename:
                    # Outreach 文件
                    if "result" in content and "sequences" in content["result"]:
                        sequences_data = content["result"]["sequences"]
                elif "mapping" in filename:
                    # Mappings 文件
                    if "result" in content and "personas_with_mappings" in content["result"]:
                        mappings_data = content["result"]["personas_with_mappings"]
                elif "persona" in filename and "mapping" not in filename:
                    # 独立的 personas 文件
                    if "result" in content and "personas" in content["result"]:
                        personas_data = content["result"]["personas"]
                elif "two_stage" in filename or "three_stage" in filename:
                    # Consolidated 文件
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
        """评估序列结构质量"""
        total_touches = sequence.get("total_touches", 0)
        duration_days = sequence.get("duration_days", 0)
        touches = sequence.get("touches", [])
        
        # 1. Touches 数量检查（4-6 为理想）
        touches_count_valid = 4 <= total_touches <= 6
        touches_count_score = 1.0 if touches_count_valid else (0.5 if 3 <= total_touches <= 7 else 0.0)
        
        # 2. Duration 检查（10-21 天为理想）
        duration_valid = 10 <= duration_days <= 21
        duration_score = 1.0 if duration_valid else (0.5 if 7 <= duration_days <= 25 else 0.0)
        
        # 3. Timing 检查
        timing_valid = True
        timing_issues = []
        prev_timing = -1
        
        for i, touch in enumerate(touches):
            timing = touch.get("timing_days", -1)
            sort_order = touch.get("sort_order", i + 1)
            
            # 第一个 touch 必须是 0
            if i == 0 and timing != 0:
                timing_valid = False
                timing_issues.append(f"Touch {sort_order}: 第一个 touch 的 timing_days 应该是 0，实际是 {timing}")
            
            # Timing 应该是递增的
            if i > 0 and timing <= prev_timing:
                timing_valid = False
                timing_issues.append(f"Touch {sort_order}: timing_days ({timing}) 应该大于前一个 ({prev_timing})")
            
            # Timing 间隔应该是 2-3 天（除了第一个）
            if i > 0:
                interval = timing - prev_timing
                if not (2 <= interval <= 3):
                    timing_issues.append(f"Touch {sort_order}: 间隔 {interval} 天，理想是 2-3 天")
            
            prev_timing = timing
        
        timing_score = 1.0 if timing_valid and not timing_issues else max(0.0, 1.0 - len(timing_issues) * 0.2)
        
        # 4. Sort order 检查
        sort_order_valid = True
        for i, touch in enumerate(touches):
            expected_order = i + 1
            actual_order = touch.get("sort_order", 0)
            if actual_order != expected_order:
                sort_order_valid = False
                break
        
        sort_order_score = 1.0 if sort_order_valid else 0.5
        
        # 5. 最后一个 touch 的 timing 应该等于 duration_days
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
        """评估 Touch 类型多样性"""
        touches = sequence.get("touches", [])
        touch_types = [touch.get("touch_type", "").lower() for touch in touches]
        
        # 统计各类型数量
        type_counts = {}
        for touch_type in touch_types:
            type_counts[touch_type] = type_counts.get(touch_type, 0) + 1
        
        # 理想分布：应该有 email, linkedin, phone
        has_email = "email" in touch_types
        has_linkedin = "linkedin" in touch_types
        has_phone = "phone" in touch_types or "video" in touch_types
        
        # 多样性评分
        diversity_score = 0.0
        if has_email:
            diversity_score += 0.3
        if has_linkedin:
            diversity_score += 0.3
        if has_phone:
            diversity_score += 0.4
        
        # 检查是否有合理的类型分布
        # 理想：email 最多，linkedin 次之，phone 最少
        email_count = touch_types.count("email")
        linkedin_count = touch_types.count("linkedin")
        phone_count = touch_types.count("phone") + touch_types.count("video")
        
        distribution_score = 1.0
        if email_count < linkedin_count:
            distribution_score -= 0.2  # Email 应该最多
        if phone_count > email_count:
            distribution_score -= 0.3  # Phone 不应该比 email 多
        
        # 检查是否有 phone/video 在最后
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
        """评估内容质量"""
        touches = sequence.get("touches", [])
        persona_name = sequence.get("persona_name", "")
        
        # 创建 pain points 集合（用于检查是否引用）
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
            
            # 1. Subject line 检查
            if touch_type in ["email", "linkedin"]:
                if not subject_line:
                    subject_line_issues.append(f"Touch {touch.get('sort_order')}: {touch_type} 缺少 subject_line")
                    touch_score -= 0.2
                elif len(subject_line) > 60:
                    subject_line_issues.append(f"Touch {touch.get('sort_order')}: subject_line 过长 ({len(subject_line)} 字符)")
                    touch_score -= 0.1
                elif len(subject_line) < 10:
                    subject_line_issues.append(f"Touch {touch.get('sort_order')}: subject_line 过短 ({len(subject_line)} 字符)")
                    touch_score -= 0.1
            elif touch_type in ["phone", "video"]:
                if subject_line is not None:
                    subject_line_issues.append(f"Touch {touch.get('sort_order')}: {touch_type} 不应该有 subject_line")
                    touch_score -= 0.1
            
            # 2. Content 检查
            if not content:
                content_issues.append(f"Touch {touch.get('sort_order')}: 缺少 content_suggestion")
                touch_score -= 0.3
            else:
                # 检查是否包含个性化标记
                has_personalization = "{{first_name}}" in content or "{{company}}" in content
                if not has_personalization:
                    content_issues.append(f"Touch {touch.get('sort_order')}: 缺少个性化标记")
                    touch_score -= 0.1
                
                # 检查是否引用 pain point
                content_lower = content.lower()
                for pain_point in pain_points:
                    # 简单的关键词匹配
                    pain_keywords = set(pain_point.split()[:5])  # 取前5个词
                    content_words = set(content_lower.split())
                    if len(pain_keywords & content_words) >= 2:  # 至少2个关键词匹配
                        pain_point_references += 1
                        break
                
                # 检查内容长度
                if len(content) < 50:
                    content_issues.append(f"Touch {touch.get('sort_order')}: 内容过短")
                    touch_score -= 0.1
                elif len(content) > 500:
                    content_issues.append(f"Touch {touch.get('sort_order')}: 内容过长")
                    touch_score -= 0.05
            
            # 3. Objective 检查
            objective = touch.get("objective", "")
            if not objective:
                content_issues.append(f"Touch {touch.get('sort_order')}: 缺少 objective")
                touch_score -= 0.1
            
            touch_scores.append(max(0.0, touch_score))
        
        avg_touch_score = sum(touch_scores) / len(touch_scores) if touch_scores else 0.0
        
        # Pain point 引用率
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
        """评估序列的连贯性和渐进性"""
        touches = sequence.get("touches", [])
        objective = sequence.get("objective", "")
        
        if len(touches) < 2:
            return {
                "coherence_score": 0.0,
                "progression_score": 0.0,
                "overall_coherence_score": 0.0,
                "issues": ["序列太短，无法评估连贯性"]
            }
        
        # 1. 检查每个 touch 的 objective 是否相关
        objectives = [touch.get("objective", "") for touch in touches]
        sequence_objective_words = set(objective.lower().split())
        
        objective_relevance = []
        for i, touch_obj in enumerate(objectives):
            if touch_obj:
                touch_obj_words = set(touch_obj.lower().split())
                # 检查是否有共同的关键词
                common_words = sequence_objective_words & touch_obj_words
                relevance = len(common_words) / max(len(sequence_objective_words), 1)
                objective_relevance.append(relevance)
            else:
                objective_relevance.append(0.0)
        
        coherence_score = sum(objective_relevance) / len(objective_relevance) if objective_relevance else 0.0
        
        # 2. 检查渐进性（后面的 touch 应该更深入或更具体）
        progression_score = 0.5  # 默认中等分数
        # 简单的启发式：检查后面的 touch 是否包含更多细节词
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
    
    def evaluate_all_sequences(self, company_name: str, architecture: str) -> Dict:
        """评估某个公司在某个架构下的所有 sequences"""
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
            "sequence_details": []
        }
        
        for sequence in sequences_data:
            persona_name = sequence.get("persona_name", "")
            
            # 找到对应的 mappings
            persona_mappings = None
            for mapping_group in mappings_data:
                if mapping_group.get("persona_name") == persona_name:
                    persona_mappings = [mapping_group]
                    break
            
            # 评估各项指标
            structure = self.evaluate_sequence_structure(sequence)
            diversity = self.evaluate_touch_diversity(sequence)
            content = self.evaluate_content_quality(sequence, persona_mappings)
            coherence = self.evaluate_sequence_coherence(sequence)
            
            # 计算总体评分
            overall_score = (
                structure["overall_structure_score"] * 0.25 +
                diversity["overall_diversity_score"] * 0.25 +
                content["overall_content_score"] * 0.3 +
                coherence["overall_coherence_score"] * 0.2
            )
            
            results["sequence_details"].append({
                "persona_name": persona_name,
                "sequence_name": sequence.get("name", ""),
                "structure": structure,
                "diversity": diversity,
                "content": content,
                "coherence": coherence,
                "overall_score": overall_score
            })
        
        # 计算汇总统计
        if results["sequence_details"]:
            structure_scores = [s["structure"]["overall_structure_score"] for s in results["sequence_details"]]
            diversity_scores = [s["diversity"]["overall_diversity_score"] for s in results["sequence_details"]]
            content_scores = [s["content"]["overall_content_score"] for s in results["sequence_details"]]
            coherence_scores = [s["coherence"]["overall_coherence_score"] for s in results["sequence_details"]]
            overall_scores = [s["overall_score"] for s in results["sequence_details"]]
            
            results["summary"] = {
                "avg_structure_score": sum(structure_scores) / len(structure_scores) if structure_scores else 0.0,
                "avg_diversity_score": sum(diversity_scores) / len(diversity_scores) if diversity_scores else 0.0,
                "avg_content_score": sum(content_scores) / len(content_scores) if content_scores else 0.0,
                "avg_coherence_score": sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0,
                "avg_overall_score": sum(overall_scores) / len(overall_scores) if overall_scores else 0.0
            }
        
        return results
    
    def compare_architectures(self, two_stage_results: Dict, three_stage_results: Dict = None, four_stage_results: Dict = None) -> Dict:
        """对比两种或三种架构的 outreach 质量"""
        comparison = {
            "company_name": two_stage_results.get("company_name", ""),
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
        
        metrics = {
            "structure_score": "avg_structure_score",
            "diversity_score": "avg_diversity_score",
            "content_score": "avg_content_score",
            "coherence_score": "avg_coherence_score",
            "overall_score": "avg_overall_score"
        }
        
        comparison_details = {}
        for metric_name, summary_key in metrics.items():
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
        
        comparison["comparison"] = comparison_details
        return comparison


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="评估 Outreach Sequences 质量")
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="使用 LLM 进行智能评估（更灵活，但需要 API 调用）"
    )
    args = parser.parse_args()
    
    evaluation_dir = Path("data/Evaluation")
    
    if not evaluation_dir.exists():
        print(f"❌ 评估目录不存在: {evaluation_dir}")
        return
    
    evaluator = OutreachQualityEvaluator(evaluation_dir, use_llm=args.use_llm)
    
    # 获取所有公司
    companies = [d.name for d in evaluation_dir.iterdir() if d.is_dir()]
    
    if not companies:
        print("❌ 没有找到公司数据")
        return
    
    print(f"🚀 开始评估 Outreach Sequences 质量...")
    print(f"📁 评估目录: {evaluation_dir}")
    print(f"📊 找到 {len(companies)} 个公司\n")
    
    all_results = []
    all_comparisons = []
    
    for company_name in companies:
        print(f"评估 {company_name}...")
        
        # 评估各架构
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
    
    # 保存结果
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存详细结果
    results_file = output_dir / f"outreach_quality_evaluation_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 详细评估结果已保存到: {results_file}")
    
    # 保存对比结果
    comparison_file = output_dir / f"outreach_quality_comparison_{timestamp}.json"
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(all_comparisons, f, indent=2, ensure_ascii=False)
    print(f"✅ 对比结果已保存到: {comparison_file}")
    
    # 打印汇总
    print("\n" + "=" * 80)
    print("Outreach 质量评估汇总（2 Stage vs 3 Stage vs 4 Stage）")
    print("=" * 80)
    
    for comparison in all_comparisons:
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


if __name__ == "__main__":
    main()

