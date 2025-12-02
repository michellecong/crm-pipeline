#!/usr/bin/env python3
"""
生成综合评估汇总表格

整合以下评估结果：
1. Persona 质量评估
2. Mapping 质量评估
3. Outreach 质量评估
4. Pipeline 指标（Time 和 Token）

生成 CSV 对比表格
"""
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import glob


def load_latest_evaluation_file(pattern: str) -> Path:
    """加载最新的评估文件"""
    files = sorted(glob.glob(str(Path("evaluation_results") / pattern)), reverse=True)
    if files:
        return Path(files[0])
    return None


def load_json_file(file_path: Path) -> Dict:
    """加载 JSON 文件"""
    if not file_path or not file_path.exists():
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_pipeline_metrics(company_name: str, architecture: str) -> Dict:
    """提取 pipeline 的 time 和 token 指标"""
    evaluation_dir = Path("data/Evaluation")
    company_dir = evaluation_dir / company_name / architecture
    
    if not company_dir.exists():
        return {"total_tokens": 0, "total_time_seconds": 0}
    
    metrics = {"total_tokens": 0, "total_time_seconds": 0}
    
    for json_file in company_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            result = content.get("result", {})
            
            # 提取 usage
            usage = result.get("usage", {})
            if usage:
                metrics["total_tokens"] += usage.get("total_tokens", 0)
            
            # 提取 time
            time_seconds = result.get("generation_time_seconds", 0)
            if time_seconds:
                metrics["total_time_seconds"] += time_seconds
            
            # 检查 statistics
            stats = result.get("statistics", {})
            if stats:
                token_breakdown = stats.get("token_breakdown", {})
                if token_breakdown:
                    metrics["total_tokens"] += token_breakdown.get("total_tokens", 0)
                if stats.get("total_runtime_seconds"):
                    metrics["total_time_seconds"] += stats.get("total_runtime_seconds", 0)
        except:
            continue
    
    return metrics


def main():
    """主函数"""
    print("🚀 生成综合评估汇总表格...")
    
    # 1. 加载最新的评估结果
    persona_file = load_latest_evaluation_file("persona_quality_comparison_*.json")
    mapping_file = load_latest_evaluation_file("mapping_quality_comparison_*.json")
    outreach_file = load_latest_evaluation_file("outreach_quality_comparison_*.json")
    
    persona_data = load_json_file(persona_file) if persona_file else []
    mapping_data = load_json_file(mapping_file) if mapping_file else []
    outreach_data = load_json_file(outreach_file) if outreach_file else []
    
    print(f"✅ 加载评估结果:")
    print(f"   Persona: {persona_file.name if persona_file else '未找到'}")
    print(f"   Mapping: {mapping_file.name if mapping_file else '未找到'}")
    print(f"   Outreach: {outreach_file.name if outreach_file else '未找到'}")
    
    # 2. 获取所有公司名称
    companies = set()
    if persona_data:
        companies.update([c["company_name"] for c in persona_data])
    if mapping_data:
        companies.update([c["company_name"] for c in mapping_data])
    if outreach_data:
        companies.update([c["company_name"] for c in outreach_data])
    
    companies = sorted(list(companies))
    print(f"\n📊 找到 {len(companies)} 个公司")
    
    # 3. 生成汇总表格
    rows = []
    
    for company_name in companies:
        row = {"company_name": company_name}
        
        # 从各评估结果中提取数据
        for arch_name in ["2 Stage", "3 Stage", "4 Stage"]:
            prefix = arch_name.lower().replace(" ", "_")
            
            # Persona 数据
            persona_item = None
            if persona_data:
                for p in persona_data:
                    if p["company_name"] == company_name:
                        persona_item = p
                        break
            
            if persona_item:
                absolute_scores = persona_item.get("absolute_scores", {})
                
                if arch_name == "2 Stage":
                    arch_key = "two_stage"
                    if arch_key in absolute_scores:
                        arch_data = absolute_scores[arch_key]
                        row[f"{prefix}_persona_quality"] = arch_data.get("total_score_percentage", 0) / 100.0
                        row[f"{prefix}_persona_count"] = 0
                    else:
                        row[f"{prefix}_persona_count"] = 0
                        row[f"{prefix}_persona_quality"] = 0
                elif arch_name == "3 Stage":
                    # Stage 3 使用 Stage 2 的 Persona 质量（因为 Stage 3 的 Personas 来自 Stage 2）
                    if "two_stage" in absolute_scores:
                        arch_data = absolute_scores["two_stage"]
                        row[f"{prefix}_persona_quality"] = arch_data.get("total_score_percentage", 0) / 100.0
                        row[f"{prefix}_persona_count"] = 0
                    else:
                        row[f"{prefix}_persona_count"] = 0
                        row[f"{prefix}_persona_quality"] = 0
                elif arch_name == "4 Stage":
                    arch_key = "four_stage"
                    if arch_key in absolute_scores:
                        arch_data = absolute_scores[arch_key]
                        row[f"{prefix}_persona_quality"] = arch_data.get("total_score_percentage", 0) / 100.0
                        row[f"{prefix}_persona_count"] = 0
                    else:
                        row[f"{prefix}_persona_count"] = 0
                        row[f"{prefix}_persona_quality"] = 0
                else:
                    row[f"{prefix}_persona_count"] = 0
                    row[f"{prefix}_persona_quality"] = 0
            else:
                row[f"{prefix}_persona_count"] = 0
                row[f"{prefix}_persona_quality"] = 0
            
            # Mapping 数据
            mapping_comp = None
            if mapping_data:
                for m in mapping_data:
                    if m["company_name"] == company_name:
                        mapping_comp = m.get("comparison", {})
                        break
            
            if mapping_comp:
                # 计算 overall score（加权平均）
                arch_key_map = {
                    "2 Stage": "two_stage",
                    "3 Stage": "three_stage",
                    "4 Stage": "four_stage"
                }
                arch_key = arch_key_map.get(arch_name, "")
                
                product_match = mapping_comp.get("product_match_score", {}).get(arch_key, 0)
                persona_match = mapping_comp.get("persona_match_score", {}).get(arch_key, 0)
                text_quality = mapping_comp.get("text_quality_score", {}).get(arch_key, 0)
                quantified_rate = mapping_comp.get("quantified_benefit_rate", {}).get(arch_key, 0)
                pain_value = mapping_comp.get("pain_value_match_score", {}).get(arch_key, 0)
                
                overall_score = (
                    product_match * 0.2 +
                    persona_match * 0.2 +
                    text_quality * 0.2 +
                    quantified_rate * 0.2 +
                    pain_value * 0.2
                )
                
                row[f"{prefix}_mapping_count"] = 0  # 需要从详细数据中提取
                row[f"{prefix}_mapping_overall"] = round(overall_score, 3)
                row[f"{prefix}_mapping_quantified_rate"] = round(quantified_rate, 3)
            else:
                row[f"{prefix}_mapping_count"] = 0
                row[f"{prefix}_mapping_overall"] = 0
                row[f"{prefix}_mapping_quantified_rate"] = 0
            
            # Outreach 数据
            outreach_comp = None
            if outreach_data:
                for o in outreach_data:
                    if o["company_name"] == company_name:
                        outreach_comp = o.get("comparison", {})
                        break
            
            if outreach_comp:
                overall = outreach_comp.get("overall_score", {})
                if arch_name == "2 Stage":
                    row[f"{prefix}_outreach_count"] = 0
                    row[f"{prefix}_outreach_overall"] = overall.get("two_stage", 0)
                elif arch_name == "3 Stage":
                    row[f"{prefix}_outreach_count"] = 0
                    row[f"{prefix}_outreach_overall"] = overall.get("three_stage", 0)
                elif arch_name == "4 Stage":
                    row[f"{prefix}_outreach_count"] = 0
                    row[f"{prefix}_outreach_overall"] = overall.get("four_stage", 0)
            else:
                row[f"{prefix}_outreach_count"] = 0
                row[f"{prefix}_outreach_overall"] = 0
            
            # Pipeline 指标
            arch_variants = {
                "2 Stage": ["2 Stage", "Two-Stage", "2 stage"],
                "3 Stage": ["3 Stage", "Three-Stage", "3 stage"],
                "4 Stage": ["4 Stage", "Four-Stage", "4 stage"]
            }
            
            pipeline_metrics = {"total_tokens": 0, "total_time_seconds": 0}
            for variant in arch_variants[arch_name]:
                metrics = extract_pipeline_metrics(company_name, variant)
                if metrics["total_tokens"] > 0:
                    pipeline_metrics = metrics
                    break
            
            row[f"{prefix}_tokens"] = pipeline_metrics["total_tokens"]
            row[f"{prefix}_time_minutes"] = round(pipeline_metrics["total_time_seconds"] / 60, 2)
        
        rows.append(row)
    
    # 4. 保存 CSV
    if rows:
        output_dir = Path("evaluation_results")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = output_dir / f"comprehensive_evaluation_summary_{timestamp}.csv"
        
        fieldnames = rows[0].keys()
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"\n✅ 汇总表格已保存到: {csv_file}")
        
        # 打印汇总统计
        print("\n" + "=" * 80)
        print("汇总统计（平均值）")
        print("=" * 80)
        
        # 计算平均值
        for arch_name in ["2 Stage", "3 Stage", "4 Stage"]:
            prefix = arch_name.lower().replace(" ", "_")
            print(f"\n{arch_name}:")
            
            persona_qualities = [float(r.get(f"{prefix}_persona_quality", 0)) for r in rows if float(r.get(f"{prefix}_persona_quality", 0)) > 0]
            mapping_overalls = [float(r.get(f"{prefix}_mapping_overall", 0)) for r in rows if float(r.get(f"{prefix}_mapping_overall", 0)) > 0]
            outreach_overalls = [float(r.get(f"{prefix}_outreach_overall", 0)) for r in rows if float(r.get(f"{prefix}_outreach_overall", 0)) > 0]
            tokens = [int(r.get(f"{prefix}_tokens", 0)) for r in rows if int(r.get(f"{prefix}_tokens", 0)) > 0]
            
            # 时间数据：移除异常值（使用 IQR 方法）
            times_raw = [float(r.get(f"{prefix}_time_minutes", 0)) for r in rows if float(r.get(f"{prefix}_time_minutes", 0)) > 0]
            if times_raw and len(times_raw) > 2:
                sorted_times = sorted(times_raw)
                q1_idx = len(sorted_times) // 4
                q3_idx = 3 * len(sorted_times) // 4
                q1 = sorted_times[q1_idx]
                q3 = sorted_times[q3_idx]
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                times = [t for t in times_raw if lower_bound <= t <= upper_bound]
                outliers = [t for t in times_raw if t < lower_bound or t > upper_bound]
                if outliers:
                    print(f"  ⚠️  {arch_name} 时间异常值已移除: {outliers}")
            else:
                times = times_raw
            
            if persona_qualities:
                print(f"  Persona 质量: {sum(persona_qualities)/len(persona_qualities):.3f}")
            if mapping_overalls:
                print(f"  Mapping 质量: {sum(mapping_overalls)/len(mapping_overalls):.3f}")
            if outreach_overalls:
                print(f"  Outreach 质量: {sum(outreach_overalls)/len(outreach_overalls):.3f}")
            if tokens:
                print(f"  Token 消耗: {sum(tokens)/len(tokens):.0f}")
            if times:
                print(f"  时间消耗（分钟）: {sum(times)/len(times):.2f}")
    else:
        print("❌ 没有数据可汇总")


if __name__ == "__main__":
    main()

