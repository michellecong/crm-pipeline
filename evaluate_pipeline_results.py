#!/usr/bin/env python3
"""
Pipeline Evaluation Script

评估三种架构（2-stage, 3-stage, 4-stage）的测试结果
只对比有意义的指标：
- 2 Stage vs 3 Stage 的 Personas（生成方法不同）
- 2 Stage vs 3 Stage vs 4 Stage 的 Mappings（生成方法不同）
- 2 Stage vs 3 Stage vs 4 Stage 的 Sequences（生成方法不同）
"""
import json
from pathlib import Path
from typing import Dict
import pandas as pd
from datetime import datetime

try:
    import matplotlib.pyplot as plt
    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False
    print("⚠️  matplotlib未安装，将跳过可视化功能")

# 评估数据目录
EVALUATION_DIR = Path("data/Evaluation")


def normalize_architecture_name(name: str) -> str:
    """统一架构名称（不区分大小写）"""
    name_lower = name.lower().strip()
    if "2" in name_lower and "stage" in name_lower:
        return "Two-Stage"
    elif "3" in name_lower and "stage" in name_lower:
        return "Three-Stage"
    elif "4" in name_lower and "stage" in name_lower:
        return "Four-Stage"
    return name


def remove_outliers(series: pd.Series, method: str = "iqr", multiplier: float = 1.5) -> pd.Series:
    """
    移除异常值
    
    Args:
        series: 数据序列
        method: 检测方法 ("iqr" 或 "zscore")
        multiplier: IQR方法的倍数（默认1.5）
    
    Returns:
        移除异常值后的序列
    """
    if len(series) < 3:
        return series
    
    if method == "iqr":
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - multiplier * IQR
        upper_bound = Q3 + multiplier * IQR
        return series[(series >= lower_bound) & (series <= upper_bound)]
    elif method == "zscore":
        z_scores = (series - series.mean()) / series.std()
        return series[abs(z_scores) < 3]  # 3个标准差
    else:
        return series


class PipelineEvaluator:
    """评估pipeline结果的类"""

    def __init__(self, evaluation_dir: Path):
        self.evaluation_dir = evaluation_dir
        self.results = []

    def load_company_data(self, company_name: str, architecture: str) -> Dict:
        """加载某个公司在某个架构下的所有数据"""
        company_dir = self.evaluation_dir / company_name / architecture

        if not company_dir.exists():
            return {}

        # 归一化架构名称（不区分大小写）
        normalized_architecture = normalize_architecture_name(architecture)

        data = {
            "company_name": company_name,
            "architecture": normalized_architecture,
            "products": None,
            "personas": None,
            "mappings": None,
            "sequences": None,
            "two_stage": None,
            "three_stage": None,
        }

        # 加载所有JSON文件
        for json_file in company_dir.glob("*.json"):
            filename = json_file.stem.lower()

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)

                # 根据文件名判断类型
                if "product" in filename:
                    data["products"] = content
                elif "persona" in filename and "mapping" not in filename:
                    data["personas"] = content
                elif "mapping" in filename:
                    data["mappings"] = content
                elif "outreach" in filename or "sequence" in filename:
                    data["sequences"] = content
                elif "two_stage" in filename:
                    data["two_stage"] = content
                elif "three_stage" in filename:
                    data["three_stage"] = content

            except Exception as e:
                print(f"Error loading {json_file}: {e}")

        return data

    def extract_metrics(self, data: Dict) -> Dict:
        """从数据中提取评估指标"""
        metrics = {
            "company_name": data["company_name"],
            "architecture": normalize_architecture_name(data["architecture"]),
            "num_products": 0,
            "num_personas": 0,
            "num_mappings": 0,
            "num_sequences": 0,
            "num_touches": 0,
            "avg_mappings_per_persona": 0,
            "avg_touches_per_sequence": 0,
            "total_tokens": 0,
            "total_time_seconds": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }

        # 提取Products指标
        if data.get("products"):
            products_data = data["products"].get("result", {}).get("products", [])
            metrics["num_products"] = len(products_data)

        # 提取Personas指标
        personas_data = []
        if data.get("personas"):
            personas_data = data["personas"].get("result", {}).get("personas", [])
        elif data.get("two_stage"):
            personas_data = data["two_stage"].get("result", {}).get("personas", [])
        elif data.get("three_stage"):
            # Three-stage没有单独的personas文件，personas在mappings中
            mappings_data = data["three_stage"].get("result", {}).get("personas_with_mappings", [])
            # 从mappings中提取persona名称作为personas
            personas_data = [{"persona_name": p.get("persona_name")} for p in mappings_data]

        metrics["num_personas"] = len(personas_data)

        # 提取Mappings指标
        mappings_data = []
        if data.get("mappings"):
            mappings_data = data["mappings"].get("result", {}).get("personas_with_mappings", [])
        elif data.get("two_stage"):
            mappings_data = data["two_stage"].get("result", {}).get("personas_with_mappings", [])
        elif data.get("three_stage"):
            mappings_data = data["three_stage"].get("result", {}).get("personas_with_mappings", [])

        metrics["num_mappings"] = sum(len(p.get("mappings", [])) for p in mappings_data)
        if metrics["num_personas"] > 0:
            metrics["avg_mappings_per_persona"] = metrics["num_mappings"] / metrics["num_personas"]

        # 提取Sequences指标
        sequences_data = []
        if data.get("sequences"):
            sequences_data = data["sequences"].get("result", {}).get("sequences", [])
        elif data.get("two_stage"):
            sequences_data = data["two_stage"].get("result", {}).get("sequences", [])
        elif data.get("three_stage"):
            sequences_data = data["three_stage"].get("result", {}).get("sequences", [])

        metrics["num_sequences"] = len(sequences_data)
        metrics["num_touches"] = sum(len(s.get("touches", [])) for s in sequences_data)
        if metrics["num_sequences"] > 0:
            metrics["avg_touches_per_sequence"] = metrics["num_touches"] / metrics["num_sequences"]

        # 提取Token和时间指标
        usage_data = None
        time_data = None

        # 判断是否为四阶段架构（有独立的products, personas, mappings, sequences文件）
        is_four_stage = (
            data.get("products") is not None
            and data.get("personas") is not None
            and data.get("mappings") is not None
            and data.get("sequences") is not None
            and data.get("two_stage") is None
            and data.get("three_stage") is None
        )

        if is_four_stage:
            # 四阶段架构：分别统计每个文件的token和时间
            # Products
            if data.get("products"):
                products_result = data["products"].get("result", {})
                products_usage = products_result.get("usage", {})
                products_time = products_result.get("generation_time_seconds", 0)
                if products_usage:
                    metrics["prompt_tokens"] += products_usage.get("prompt_tokens", 0)
                    metrics["completion_tokens"] += products_usage.get("completion_tokens", 0)
                    metrics["total_tokens"] += products_usage.get("total_tokens", 0)
                if products_time:
                    metrics["total_time_seconds"] += products_time

            # Personas
            if data.get("personas"):
                personas_result = data["personas"].get("result", {})
                personas_usage = personas_result.get("usage", {})
                personas_time = personas_result.get("generation_time_seconds", 0)
                if personas_usage:
                    metrics["prompt_tokens"] += personas_usage.get("prompt_tokens", 0)
                    metrics["completion_tokens"] += personas_usage.get("completion_tokens", 0)
                    metrics["total_tokens"] += personas_usage.get("total_tokens", 0)
                if personas_time:
                    metrics["total_time_seconds"] += personas_time

            # Mappings
            if data.get("mappings"):
                mappings_result = data["mappings"].get("result", {})
                mappings_usage = mappings_result.get("usage", {})
                mappings_time = mappings_result.get("generation_time_seconds", 0)
                if mappings_usage:
                    metrics["prompt_tokens"] += mappings_usage.get("prompt_tokens", 0)
                    metrics["completion_tokens"] += mappings_usage.get("completion_tokens", 0)
                    metrics["total_tokens"] += mappings_usage.get("total_tokens", 0)
                if mappings_time:
                    metrics["total_time_seconds"] += mappings_time

            # Sequences
            if data.get("sequences"):
                sequences_result = data["sequences"].get("result", {})
                sequences_usage = sequences_result.get("usage", {})
                sequences_time = sequences_result.get("generation_time_seconds", 0)
                if sequences_usage:
                    metrics["prompt_tokens"] += sequences_usage.get("prompt_tokens", 0)
                    metrics["completion_tokens"] += sequences_usage.get("completion_tokens", 0)
                    metrics["total_tokens"] += sequences_usage.get("total_tokens", 0)
                if sequences_time:
                    metrics["total_time_seconds"] += sequences_time
        else:
            # 两阶段或三阶段架构：从consolidated文件提取
            if data.get("two_stage"):
                result = data["two_stage"].get("result", {})
                usage_data = result.get("usage", {})
                time_data = result.get("generation_time_seconds")
            elif data.get("three_stage"):
                result = data["three_stage"].get("result", {})
                usage_data = result.get("usage", {})
                time_data = result.get("generation_time_seconds")

            # 从products文件提取（如果有，两阶段和三阶段也可能有独立的products文件）
            if data.get("products"):
                products_result = data["products"].get("result", {})
                products_usage = products_result.get("usage", {})
                products_time = products_result.get("generation_time_seconds", 0)
                if products_usage:
                    metrics["prompt_tokens"] += products_usage.get("prompt_tokens", 0)
                    metrics["completion_tokens"] += products_usage.get("completion_tokens", 0)
                    metrics["total_tokens"] += products_usage.get("total_tokens", 0)
                if products_time:
                    metrics["total_time_seconds"] += products_time

            # 从personas文件提取（Three-Stage有独立的personas文件）
            if data.get("personas"):
                personas_result = data["personas"].get("result", {})
                personas_usage = personas_result.get("usage", {})
                personas_time = personas_result.get("generation_time_seconds", 0)
                if personas_usage:
                    metrics["prompt_tokens"] += personas_usage.get("prompt_tokens", 0)
                    metrics["completion_tokens"] += personas_usage.get("completion_tokens", 0)
                    metrics["total_tokens"] += personas_usage.get("total_tokens", 0)
                if personas_time:
                    metrics["total_time_seconds"] += personas_time

            # 从sequences/outreach文件提取（如果有独立的sequences文件）
            if data.get("sequences"):
                sequences_result = data["sequences"].get("result", {})
                sequences_usage = sequences_result.get("usage", {})
                sequences_time = sequences_result.get("generation_time_seconds", 0)
                if sequences_usage:
                    metrics["prompt_tokens"] += sequences_usage.get("prompt_tokens", 0)
                    metrics["completion_tokens"] += sequences_usage.get("completion_tokens", 0)
                    metrics["total_tokens"] += sequences_usage.get("total_tokens", 0)
                if sequences_time:
                    metrics["total_time_seconds"] += sequences_time

            # 从consolidated文件提取（two_stage或three_stage）
            if usage_data:
                metrics["prompt_tokens"] += usage_data.get("prompt_tokens", 0)
                metrics["completion_tokens"] += usage_data.get("completion_tokens", 0)
                metrics["total_tokens"] += usage_data.get("total_tokens", 0)

            if time_data:
                metrics["total_time_seconds"] += time_data

        return metrics

    def evaluate_all(self) -> pd.DataFrame:
        """评估所有公司的所有架构"""
        all_metrics = []

        # 遍历所有公司
        for company_dir in self.evaluation_dir.iterdir():
            if not company_dir.is_dir():
                continue

            company_name = company_dir.name

            # 遍历所有架构
            for arch_dir in company_dir.iterdir():
                if not arch_dir.is_dir():
                    continue

                # 加载数据（架构名称会在load_company_data中归一化）
                data = self.load_company_data(company_name, arch_dir.name)

                if not data:
                    continue

                # 提取指标
                metrics = self.extract_metrics(data)
                all_metrics.append(metrics)

        # 转换为DataFrame
        df = pd.DataFrame(all_metrics)
        return df

    def generate_meaningful_comparison(self, df: pd.DataFrame) -> Dict:
        """生成有意义的架构对比（只对比生成方法不同的部分）"""
        comparison = {
            "personas_comparison": {},
            "mappings_comparison": {},
            "sequences_comparison": {},
            "overall_performance": {},
            "notes": []
        }
        
        # 1. Personas对比：2 Stage vs 3 Stage（生成方法不同）
        two_stage_personas = df[df["architecture"] == "Two-Stage"]["num_personas"]
        three_stage_personas = df[df["architecture"] == "Three-Stage"]["num_personas"]

        if len(two_stage_personas) > 0 and len(three_stage_personas) > 0:
            comparison["personas_comparison"] = {
                "two_stage": {
                    "avg": float(two_stage_personas.mean()),
                    "std": float(two_stage_personas.std()) if len(two_stage_personas) > 1 else 0.0,
                    "count": int(len(two_stage_personas))
                },
                "three_stage": {
                    "avg": float(three_stage_personas.mean()),
                    "std": float(three_stage_personas.std()) if len(three_stage_personas) > 1 else 0.0,
                    "count": int(len(three_stage_personas))
                },
                "difference": float(two_stage_personas.mean() - three_stage_personas.mean()),
                "note": "对比有意义：2 Stage使用consolidated生成，3 Stage使用独立生成"
            }

        # 2. Mappings对比：2 Stage vs 3 Stage vs 4 Stage（生成方法不同）
        two_stage_mappings = df[df["architecture"] == "Two-Stage"]["num_mappings"]
        three_stage_mappings = df[df["architecture"] == "Three-Stage"]["num_mappings"]
        four_stage_mappings = df[df["architecture"] == "Four-Stage"]["num_mappings"]

        if len(two_stage_mappings) > 0 and len(three_stage_mappings) > 0 and len(four_stage_mappings) > 0:
            comparison["mappings_comparison"] = {
                "two_stage": {
                    "avg": float(two_stage_mappings.mean()),
                    "std": float(two_stage_mappings.std()) if len(two_stage_mappings) > 1 else 0.0,
                    "count": int(len(two_stage_mappings))
                },
                "three_stage": {
                    "avg": float(three_stage_mappings.mean()),
                    "std": float(three_stage_mappings.std()) if len(three_stage_mappings) > 1 else 0.0,
                    "count": int(len(three_stage_mappings))
                },
                "four_stage": {
                    "avg": float(four_stage_mappings.mean()),
                    "std": float(four_stage_mappings.std()) if len(four_stage_mappings) > 1 else 0.0,
                    "count": int(len(four_stage_mappings))
                },
                "best": max(
                    ("Two-Stage", two_stage_mappings.mean()),
                    ("Three-Stage", three_stage_mappings.mean()),
                    ("Four-Stage", four_stage_mappings.mean()),
                    key=lambda x: x[1]
                )[0],
                "note": "对比有意义：2/3 Stage一起生成，4 Stage独立生成"
            }

        # 3. Sequences对比：2 Stage vs 3 Stage vs 4 Stage（生成方法不同）
        two_stage_sequences = df[df["architecture"] == "Two-Stage"]["num_sequences"]
        three_stage_sequences = df[df["architecture"] == "Three-Stage"]["num_sequences"]
        four_stage_sequences = df[df["architecture"] == "Four-Stage"]["num_sequences"]

        if len(two_stage_sequences) > 0 and len(three_stage_sequences) > 0 and len(four_stage_sequences) > 0:
            comparison["sequences_comparison"] = {
                "two_stage": {
                    "avg": float(two_stage_sequences.mean()),
                    "std": float(two_stage_sequences.std()) if len(two_stage_sequences) > 1 else 0.0,
                    "count": int(len(two_stage_sequences))
                },
                "three_stage": {
                    "avg": float(three_stage_sequences.mean()),
                    "std": float(three_stage_sequences.std()) if len(three_stage_sequences) > 1 else 0.0,
                    "count": int(len(three_stage_sequences))
                },
                "four_stage": {
                    "avg": float(four_stage_sequences.mean()),
                    "std": float(four_stage_sequences.std()) if len(four_stage_sequences) > 1 else 0.0,
                    "count": int(len(four_stage_sequences))
                },
                "best": max(
                    ("Two-Stage", two_stage_sequences.mean()),
                    ("Three-Stage", three_stage_sequences.mean()),
                    ("Four-Stage", four_stage_sequences.mean()),
                    key=lambda x: x[1]
                )[0],
                "note": "对比有意义：2/3 Stage一起生成，4 Stage独立生成"
            }

        # 4. 整体性能对比：所有架构
        comparison["overall_performance"] = {}
        comparison["outliers"] = {}  # 记录异常值信息
        
        for arch in ["Two-Stage", "Three-Stage", "Four-Stage"]:
            arch_df = df[df["architecture"] == arch]
            if len(arch_df) > 0:
                # 对于Three-Stage的时间，移除异常值
                if arch == "Three-Stage":
                    time_series = arch_df["total_time_seconds"]
                    time_without_outliers = remove_outliers(time_series, method="iqr", multiplier=1.5)
                    
                    # 记录异常值信息
                    outliers = time_series[~time_series.index.isin(time_without_outliers.index)]
                    if len(outliers) > 0:
                        outlier_companies = arch_df.loc[outliers.index, "company_name"].tolist()
                        outlier_times = outliers.tolist()
                        comparison["outliers"][arch] = {
                            "companies": outlier_companies,
                            "times": outlier_times,
                            "count": len(outliers)
                        }
                    
                    # 使用移除异常值后的数据计算平均时间
                    avg_time = float(time_without_outliers.mean()) if len(time_without_outliers) > 0 else float(time_series.mean())
                    count_without_outliers = len(time_without_outliers)
                else:
                    avg_time = float(arch_df["total_time_seconds"].mean())
                    count_without_outliers = len(arch_df)
                
                comparison["overall_performance"][arch] = {
                    "avg_tokens": float(arch_df["total_tokens"].mean()),
                    "avg_time_seconds": avg_time,
                    "avg_time_seconds_with_outliers": float(arch_df["total_time_seconds"].mean()) if arch == "Three-Stage" else None,
                    "avg_mappings": float(arch_df["num_mappings"].mean()),
                    "avg_sequences": float(arch_df["num_sequences"].mean()),
                    "count": int(len(arch_df)),
                    "count_without_outliers": count_without_outliers if arch == "Three-Stage" else None
                }

        # 添加说明
        comparison["notes"] = [
            "Personas对比：只对比2 Stage vs 3 Stage（生成方法不同）",
            "Mappings对比：对比2 Stage vs 3 Stage vs 4 Stage（生成方法不同）",
            "Sequences对比：对比2 Stage vs 3 Stage vs 4 Stage（生成方法不同）",
            "注意：3 Stage vs 4 Stage的Personas对比没有意义（生成方法相同）",
            "注意：3 Stage vs 4 Stage的Products对比没有意义（生成方法相同）"
        ]

        return comparison

    def save_results(self, df: pd.DataFrame, output_dir: Path = Path("evaluation_results")):
        """保存评估结果"""
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细数据
        csv_path = output_dir / f"detailed_metrics_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        print(f"✅ 详细指标已保存到: {csv_path}")

        # 生成有意义的对比报告
        comparison = self.generate_meaningful_comparison(df)
        comparison_path = output_dir / f"meaningful_comparison_{timestamp}.json"
        with open(comparison_path, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        print(f"✅ 有意义对比报告已保存到: {comparison_path}")

        # 生成对比CSV（只包含有意义的对比）
        comparison_csv_path = output_dir / f"meaningful_comparison_{timestamp}.csv"
        comparison_df = df.groupby("architecture").agg({
            "num_personas": ["mean", "std", "count"],
            "num_mappings": ["mean", "std", "count"],
            "num_sequences": ["mean", "std", "count"],
            "num_touches": ["mean", "std"],
            "total_tokens": ["mean", "std"],
            "total_time_seconds": ["mean", "std"],
        }).round(2)
        comparison_df.to_csv(comparison_csv_path)
        print(f"✅ 对比数据已保存到: {comparison_csv_path}")

        # 打印汇总统计
        self.print_summary(comparison, df)

        # 生成可视化图表
        if HAS_VISUALIZATION:
            self.generate_visualizations(df, output_dir, timestamp)

        return output_dir

    def print_summary(self, comparison: Dict, df: pd.DataFrame):
        """打印汇总统计"""
        print("\n" + "=" * 80)
        print("评估结果汇总（只包含有意义的对比）")
        print("=" * 80)

        print(f"\n📊 总体统计:")
        print(f"   - 公司数量: {df['company_name'].nunique()}")
        print(f"   - 架构数量: {df['architecture'].nunique()}")
        print(f"   - 总运行次数: {len(df)}")

        # Personas对比（2 Stage vs 3 Stage）
        if comparison.get("personas_comparison"):
            pc = comparison["personas_comparison"]
            print(f"\n👥 Personas对比（2 Stage vs 3 Stage）:")
            print(f"   2 Stage: 平均 {pc['two_stage']['avg']:.1f} 个 (n={pc['two_stage']['count']})")
            print(f"   3 Stage: 平均 {pc['three_stage']['avg']:.1f} 个 (n={pc['three_stage']['count']})")
            print(f"   差异: {pc['difference']:.1f}")
            print(f"   说明: {pc['note']}")

        # Mappings对比（2 Stage vs 3 Stage vs 4 Stage）
        if comparison.get("mappings_comparison"):
            mc = comparison["mappings_comparison"]
            print(f"\n🔗 Mappings对比（2 Stage vs 3 Stage vs 4 Stage）:")
            print(f"   2 Stage: 平均 {mc['two_stage']['avg']:.1f} 个 (n={mc['two_stage']['count']})")
            print(f"   3 Stage: 平均 {mc['three_stage']['avg']:.1f} 个 (n={mc['three_stage']['count']})")
            print(f"   4 Stage: 平均 {mc['four_stage']['avg']:.1f} 个 (n={mc['four_stage']['count']})")
            print(f"   最佳: {mc['best']}")
            print(f"   说明: {mc['note']}")

        # Sequences对比（2 Stage vs 3 Stage vs 4 Stage）
        if comparison.get("sequences_comparison"):
            sc = comparison["sequences_comparison"]
            print(f"\n📧 Sequences对比（2 Stage vs 3 Stage vs 4 Stage）:")
            print(f"   2 Stage: 平均 {sc['two_stage']['avg']:.1f} 个 (n={sc['two_stage']['count']})")
            print(f"   3 Stage: 平均 {sc['three_stage']['avg']:.1f} 个 (n={sc['three_stage']['count']})")
            print(f"   4 Stage: 平均 {sc['four_stage']['avg']:.1f} 个 (n={sc['four_stage']['count']})")
            print(f"   最佳: {sc['best']}")
            print(f"   说明: {sc['note']}")

        # 整体性能
        if comparison.get("overall_performance"):
            print(f"\n⚡ 整体性能对比:")
            for arch, perf in comparison["overall_performance"].items():
                print(f"   {arch}:")
                print(f"      - 平均Token: {perf['avg_tokens']:,.0f}")
                if perf.get('avg_time_seconds_with_outliers') is not None:
                    # Three-Stage显示排除异常值后的时间
                    print(f"      - 平均时间: {perf['avg_time_seconds']:.1f}秒 (排除异常值后, n={perf['count_without_outliers']})")
                    print(f"      - 平均时间(含异常值): {perf['avg_time_seconds_with_outliers']:.1f}秒 (n={perf['count']})")
                else:
                    print(f"      - 平均时间: {perf['avg_time_seconds']:.1f}秒")
                print(f"      - 平均Mappings: {perf['avg_mappings']:.1f}")
                print(f"      - 平均Sequences: {perf['avg_sequences']:.1f}")
            
            # 显示异常值信息
            if comparison.get("outliers"):
                print(f"\n🔍 异常值检测:")
                for arch, outlier_info in comparison["outliers"].items():
                    print(f"   {arch}:")
                    for i, (company, time) in enumerate(zip(outlier_info["companies"], outlier_info["times"])):
                        print(f"      - {company}: {time:.1f}秒 (已排除)")

        # 注意事项
        if comparison.get("notes"):
            print(f"\n⚠️  注意事项:")
            for note in comparison["notes"]:
                print(f"   - {note}")
            if comparison.get("outliers"):
                print(f"   - Three-Stage的平均时间已排除异常值（使用IQR方法检测）")

    def generate_visualizations(self, df: pd.DataFrame, output_dir: Path, timestamp: str):
        """生成可视化图表（只包含有意义的对比）"""
        try:
            plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False

            # 1. Personas对比（2 Stage vs 3 Stage）
            fig, axes = plt.subplots(1, 1, figsize=(10, 6))
            fig.suptitle('Personas对比：2 Stage vs 3 Stage', fontsize=14, fontweight='bold')

            personas_data = []
            archs = []
            for arch in ["Two-Stage", "Three-Stage"]:
                arch_df = df[df["architecture"] == arch]
                if len(arch_df) > 0:
                    personas_data.append(arch_df["num_personas"].values)
                    archs.append(arch)

            if personas_data:
                axes.boxplot(personas_data, labels=archs)
                axes.set_ylabel('Personas数量')
                axes.set_title('对比有意义：生成方法不同', fontsize=12)
                axes.grid(axis='y', alpha=0.3)

            plt.tight_layout()
            personas_chart_path = output_dir / f"personas_comparison_{timestamp}.png"
            plt.savefig(personas_chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Personas对比图表已保存到: {personas_chart_path}")

            # 2. Mappings对比（2 Stage vs 3 Stage vs 4 Stage）
            fig, axes = plt.subplots(1, 1, figsize=(12, 6))
            fig.suptitle('Mappings对比：2 Stage vs 3 Stage vs 4 Stage', fontsize=14, fontweight='bold')

            mappings_data = []
            archs = []
            for arch in ["Two-Stage", "Three-Stage", "Four-Stage"]:
                arch_df = df[df["architecture"] == arch]
                if len(arch_df) > 0:
                    mappings_data.append(arch_df["num_mappings"].values)
                    archs.append(arch)

            if mappings_data:
                axes.boxplot(mappings_data, labels=archs)
                axes.set_ylabel('Mappings数量')
                axes.set_title('对比有意义：生成方法不同', fontsize=12)
                axes.grid(axis='y', alpha=0.3)

            plt.tight_layout()
            mappings_chart_path = output_dir / f"mappings_comparison_{timestamp}.png"
            plt.savefig(mappings_chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Mappings对比图表已保存到: {mappings_chart_path}")

            # 3. Sequences对比（2 Stage vs 3 Stage vs 4 Stage）
            fig, axes = plt.subplots(1, 1, figsize=(12, 6))
            fig.suptitle('Sequences对比：2 Stage vs 3 Stage vs 4 Stage', fontsize=14, fontweight='bold')

            sequences_data = []
            archs = []
            for arch in ["Two-Stage", "Three-Stage", "Four-Stage"]:
                arch_df = df[df["architecture"] == arch]
                if len(arch_df) > 0:
                    sequences_data.append(arch_df["num_sequences"].values)
                    archs.append(arch)

            if sequences_data:
                axes.boxplot(sequences_data, labels=archs)
                axes.set_ylabel('Sequences数量')
                axes.set_title('对比有意义：生成方法不同', fontsize=12)
                axes.grid(axis='y', alpha=0.3)

            plt.tight_layout()
            sequences_chart_path = output_dir / f"sequences_comparison_{timestamp}.png"
            plt.savefig(sequences_chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Sequences对比图表已保存到: {sequences_chart_path}")

            # 4. 整体性能对比
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('整体架构性能对比', fontsize=16, fontweight='bold')

            # Token对比
            arch_tokens = df.groupby("architecture")["total_tokens"].mean()
            axes[0, 0].bar(arch_tokens.index, arch_tokens.values, color=['#3498db', '#2ecc71', '#e74c3c'])
            axes[0, 0].set_title('平均Token消耗', fontsize=12, fontweight='bold')
            axes[0, 0].set_ylabel('Token数量')
            axes[0, 0].grid(axis='y', alpha=0.3)

            # 时间对比（排除异常值）
            arch_time_data = {}
            for arch in ["Two-Stage", "Three-Stage", "Four-Stage"]:
                arch_df = df[df["architecture"] == arch]
                if len(arch_df) > 0:
                    if arch == "Three-Stage":
                        # 排除异常值
                        time_series = arch_df["total_time_seconds"]
                        time_without_outliers = remove_outliers(time_series, method="iqr", multiplier=1.5)
                        arch_time_data[arch] = time_without_outliers.mean() if len(time_without_outliers) > 0 else time_series.mean()
                    else:
                        arch_time_data[arch] = arch_df["total_time_seconds"].mean()
            
            if arch_time_data:
                arch_time = pd.Series(arch_time_data)
                axes[0, 1].bar(arch_time.index, arch_time.values, color=['#3498db', '#2ecc71', '#e74c3c'])
                axes[0, 1].set_title('平均生成时间 (排除异常值)', fontsize=12, fontweight='bold')
                axes[0, 1].set_ylabel('时间 (秒)')
                axes[0, 1].grid(axis='y', alpha=0.3)

            # Mappings对比
            arch_mappings = df.groupby("architecture")["num_mappings"].mean()
            axes[1, 0].bar(arch_mappings.index, arch_mappings.values, color=['#3498db', '#2ecc71', '#e74c3c'])
            axes[1, 0].set_title('平均Mappings数量', fontsize=12, fontweight='bold')
            axes[1, 0].set_ylabel('Mappings数量')
            axes[1, 0].grid(axis='y', alpha=0.3)

            # Sequences对比
            arch_sequences = df.groupby("architecture")["num_sequences"].mean()
            axes[1, 1].bar(arch_sequences.index, arch_sequences.values, color=['#3498db', '#2ecc71', '#e74c3c'])
            axes[1, 1].set_title('平均Sequences数量', fontsize=12, fontweight='bold')
            axes[1, 1].set_ylabel('Sequences数量')
            axes[1, 1].grid(axis='y', alpha=0.3)

            plt.tight_layout()
            performance_path = output_dir / f"performance_comparison_{timestamp}.png"
            plt.savefig(performance_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ 性能对比图表已保存到: {performance_path}")

        except Exception as e:
            print(f"⚠️  生成可视化图表时出错: {e}")


def main():
    """主函数"""
    print("🚀 开始评估Pipeline结果...")
    print(f"📁 评估目录: {EVALUATION_DIR}")

    if not EVALUATION_DIR.exists():
        print(f"❌ 错误: 评估目录不存在: {EVALUATION_DIR}")
        return

    evaluator = PipelineEvaluator(EVALUATION_DIR)

    # 评估所有数据
    df = evaluator.evaluate_all()

    if df.empty:
        print("❌ 没有找到评估数据")
        return

    print(f"\n✅ 成功加载 {len(df)} 条评估记录")
    print(f"   公司: {df['company_name'].nunique()} 个")
    print(f"   架构: {df['architecture'].nunique()} 种")
    print(f"   架构列表: {sorted(df['architecture'].unique())}")

    # 保存结果
    output_dir = evaluator.save_results(df)

    print(f"\n✨ 评估完成！结果保存在: {output_dir}")


if __name__ == "__main__":
    main()

