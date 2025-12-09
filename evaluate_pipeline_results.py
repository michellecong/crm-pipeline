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
                    return {}
            else:
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

    def generate_time_token_analysis(self, df: pd.DataFrame) -> Dict:
        """生成时间和Token的详细对比分析"""
        analysis = {
            "time_analysis": {},
            "token_analysis": {},
            "efficiency_metrics": {},
            "stage_breakdown": {},
            "comparison_summary": {}
        }
        
        # 按架构分组
        for arch in ["Two-Stage", "Three-Stage", "Four-Stage"]:
            arch_df = df[df["architecture"] == arch]
            if len(arch_df) == 0:
                continue
            
            # 时间分析
            time_series = arch_df["total_time_seconds"]
            time_without_outliers = remove_outliers(time_series, method="iqr", multiplier=1.5)
            
            analysis["time_analysis"][arch] = {
                "mean": float(time_series.mean()),
                "median": float(time_series.median()),
                "std": float(time_series.std()) if len(time_series) > 1 else 0.0,
                "min": float(time_series.min()),
                "max": float(time_series.max()),
                "mean_without_outliers": float(time_without_outliers.mean()) if len(time_without_outliers) > 0 else float(time_series.mean()),
                "count": int(len(time_series)),
                "count_without_outliers": int(len(time_without_outliers))
            }
            
            # Token分析
            token_series = arch_df["total_tokens"]
            prompt_tokens = arch_df["prompt_tokens"].sum()
            completion_tokens = arch_df["completion_tokens"].sum()
            
            analysis["token_analysis"][arch] = {
                "total_tokens_mean": float(token_series.mean()),
                "total_tokens_median": float(token_series.median()),
                "total_tokens_std": float(token_series.std()) if len(token_series) > 1 else 0.0,
                "total_tokens_min": float(token_series.min()),
                "total_tokens_max": float(token_series.max()),
                "prompt_tokens_total": int(prompt_tokens),
                "completion_tokens_total": int(completion_tokens),
                "prompt_tokens_mean": float(arch_df["prompt_tokens"].mean()),
                "completion_tokens_mean": float(arch_df["completion_tokens"].mean()),
                "prompt_ratio": float(prompt_tokens / token_series.sum() * 100) if token_series.sum() > 0 else 0.0,
                "completion_ratio": float(completion_tokens / token_series.sum() * 100) if token_series.sum() > 0 else 0.0,
                "count": int(len(token_series))
            }
            
            # 效率指标
            avg_time = analysis["time_analysis"][arch]["mean_without_outliers"]
            avg_tokens = analysis["token_analysis"][arch]["total_tokens_mean"]
            avg_mappings = float(arch_df["num_mappings"].mean())
            avg_sequences = float(arch_df["num_sequences"].mean())
            
            analysis["efficiency_metrics"][arch] = {
                "tokens_per_second": float(avg_tokens / avg_time) if avg_time > 0 else 0.0,
                "mappings_per_token": float(avg_mappings / avg_tokens) if avg_tokens > 0 else 0.0,
                "sequences_per_token": float(avg_sequences / avg_tokens) if avg_tokens > 0 else 0.0,
                "mappings_per_second": float(avg_mappings / avg_time) if avg_time > 0 else 0.0,
                "sequences_per_second": float(avg_sequences / avg_time) if avg_time > 0 else 0.0,
                "time_per_mapping": float(avg_time / avg_mappings) if avg_mappings > 0 else 0.0,
                "time_per_sequence": float(avg_time / avg_sequences) if avg_sequences > 0 else 0.0
            }
        
        # 对比总结（相对于2-Stage的变化）
        two_stage_time = analysis["time_analysis"].get("Two-Stage", {}).get("mean_without_outliers", 0)
        two_stage_tokens = analysis["token_analysis"].get("Two-Stage", {}).get("total_tokens_mean", 0)
        
        for arch in ["Three-Stage", "Four-Stage"]:
            if arch in analysis["time_analysis"]:
                arch_time = analysis["time_analysis"][arch]["mean_without_outliers"]
                arch_tokens = analysis["token_analysis"][arch]["total_tokens_mean"]
                
                analysis["comparison_summary"][arch] = {
                    "time_vs_two_stage": {
                        "absolute_change": float(arch_time - two_stage_time),
                        "percentage_change": float((arch_time - two_stage_time) / two_stage_time * 100) if two_stage_time > 0 else 0.0,
                        "multiplier": float(arch_time / two_stage_time) if two_stage_time > 0 else 0.0
                    },
                    "tokens_vs_two_stage": {
                        "absolute_change": float(arch_tokens - two_stage_tokens),
                        "percentage_change": float((arch_tokens - two_stage_tokens) / two_stage_tokens * 100) if two_stage_tokens > 0 else 0.0,
                        "multiplier": float(arch_tokens / two_stage_tokens) if two_stage_tokens > 0 else 0.0
                    }
                }
        
        return analysis

    def generate_meaningful_comparison(self, df: pd.DataFrame) -> Dict:
        """生成有意义的架构对比（只对比生成方法不同的部分）"""
        comparison = {
            "personas_comparison": {},
            "mappings_comparison": {},
            "sequences_comparison": {},
            "overall_performance": {},
            "time_token_analysis": {},
            "notes": []
        }
        
        # 1. Personas对比：2 Stage vs 4 Stage（3 Stage 和 4 Stage 的 Personas 是一样的）
        two_stage_personas = df[df["architecture"] == "Two-Stage"]["num_personas"]
        four_stage_personas = df[df["architecture"] == "Four-Stage"]["num_personas"]

        if len(two_stage_personas) > 0 and len(four_stage_personas) > 0:
            comparison["personas_comparison"] = {
                "two_stage": {
                    "avg": float(two_stage_personas.mean()),
                    "std": float(two_stage_personas.std()) if len(two_stage_personas) > 1 else 0.0,
                    "count": int(len(two_stage_personas))
                },
                "four_stage": {
                    "avg": float(four_stage_personas.mean()),
                    "std": float(four_stage_personas.std()) if len(four_stage_personas) > 1 else 0.0,
                    "count": int(len(four_stage_personas))
                },
                "difference": float(two_stage_personas.mean() - four_stage_personas.mean()),
                "note": "对比有意义：2 Stage使用consolidated生成，4 Stage使用独立生成。注意：3 Stage和4 Stage的Personas相同，无需对比"
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

        # 添加时间和Token分析
        comparison["time_token_analysis"] = self.generate_time_token_analysis(df)

        # 添加说明
        comparison["notes"] = [
            "Personas对比：只对比2 Stage vs 4 Stage（3 Stage和4 Stage的Personas相同，无需对比）",
            "Mappings对比：对比2 Stage vs 3 Stage vs 4 Stage（生成方法不同）",
            "Sequences对比：对比2 Stage vs 3 Stage vs 4 Stage（生成方法不同）",
            "注意：3 Stage和4 Stage的Personas生成方法相同，所以只对比2 Stage和4 Stage",
            "注意：3 Stage和4 Stage的Products生成方法相同，无需对比"
        ]

        return comparison

    def save_results(self, df: pd.DataFrame, output_dir: Path = Path("evaluation_results")):
        """保存评估结果"""
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细数据 CSV
        csv_path = output_dir / f"detailed_metrics_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        print(f"✅ 详细指标已保存到: {csv_path}")

        # 保存详细数据 JSON（包含每个公司的详细指标）
        detailed_json_path = output_dir / f"detailed_metrics_{timestamp}.json"
        detailed_data = df.to_dict(orient='records')
        with open(detailed_json_path, 'w', encoding='utf-8') as f:
            json.dump(detailed_data, f, indent=2, ensure_ascii=False)
        print(f"✅ 详细指标 JSON 已保存到: {detailed_json_path}")

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
            "total_tokens": ["mean", "std", "min", "max"],
            "total_time_seconds": ["mean", "std", "min", "max"],
            "prompt_tokens": ["mean", "sum"],
            "completion_tokens": ["mean", "sum"],
        }).round(2)
        comparison_df.to_csv(comparison_csv_path)
        print(f"✅ 对比数据已保存到: {comparison_csv_path}")

        # 生成时间和Token详细对比CSV
        if comparison.get("time_token_analysis"):
            tta = comparison["time_token_analysis"]
            time_token_csv_path = output_dir / f"time_token_analysis_{timestamp}.csv"
            
            # 构建时间和Token对比表
            time_token_rows = []
            for arch in ["Two-Stage", "Three-Stage", "Four-Stage"]:
                if arch in tta.get("time_analysis", {}):
                    row = {
                        "Architecture": arch,
                        "Avg_Time_Seconds": tta["time_analysis"][arch]["mean_without_outliers"],
                        "Median_Time_Seconds": tta["time_analysis"][arch]["median"],
                        "Std_Time_Seconds": tta["time_analysis"][arch]["std"],
                        "Min_Time_Seconds": tta["time_analysis"][arch]["min"],
                        "Max_Time_Seconds": tta["time_analysis"][arch]["max"],
                        "Avg_Total_Tokens": tta["token_analysis"][arch]["total_tokens_mean"],
                        "Median_Total_Tokens": tta["token_analysis"][arch]["total_tokens_median"],
                        "Std_Total_Tokens": tta["token_analysis"][arch]["total_tokens_std"],
                        "Min_Total_Tokens": tta["token_analysis"][arch]["total_tokens_min"],
                        "Max_Total_Tokens": tta["token_analysis"][arch]["total_tokens_max"],
                        "Avg_Prompt_Tokens": tta["token_analysis"][arch]["prompt_tokens_mean"],
                        "Avg_Completion_Tokens": tta["token_analysis"][arch]["completion_tokens_mean"],
                        "Prompt_Ratio_Percent": tta["token_analysis"][arch]["prompt_ratio"],
                        "Completion_Ratio_Percent": tta["token_analysis"][arch]["completion_ratio"],
                        "Tokens_Per_Second": tta["efficiency_metrics"][arch]["tokens_per_second"],
                        "Mappings_Per_Token": tta["efficiency_metrics"][arch]["mappings_per_token"],
                        "Sequences_Per_Token": tta["efficiency_metrics"][arch]["sequences_per_token"],
                        "Mappings_Per_Second": tta["efficiency_metrics"][arch]["mappings_per_second"],
                        "Sequences_Per_Second": tta["efficiency_metrics"][arch]["sequences_per_second"],
                        "Time_Per_Mapping": tta["efficiency_metrics"][arch]["time_per_mapping"],
                        "Time_Per_Sequence": tta["efficiency_metrics"][arch]["time_per_sequence"],
                    }
                    
                    # 添加相对于2-Stage的变化（如果是3-Stage或4-Stage）
                    if arch in tta.get("comparison_summary", {}):
                        cs = tta["comparison_summary"][arch]
                        row["Time_Change_vs_2Stage_Seconds"] = cs["time_vs_two_stage"]["absolute_change"]
                        row["Time_Change_vs_2Stage_Percent"] = cs["time_vs_two_stage"]["percentage_change"]
                        row["Time_Multiplier_vs_2Stage"] = cs["time_vs_two_stage"]["multiplier"]
                        row["Token_Change_vs_2Stage"] = cs["tokens_vs_two_stage"]["absolute_change"]
                        row["Token_Change_vs_2Stage_Percent"] = cs["tokens_vs_two_stage"]["percentage_change"]
                        row["Token_Multiplier_vs_2Stage"] = cs["tokens_vs_two_stage"]["multiplier"]
                    else:
                        row["Time_Change_vs_2Stage_Seconds"] = 0
                        row["Time_Change_vs_2Stage_Percent"] = 0
                        row["Time_Multiplier_vs_2Stage"] = 1.0
                        row["Token_Change_vs_2Stage"] = 0
                        row["Token_Change_vs_2Stage_Percent"] = 0
                        row["Token_Multiplier_vs_2Stage"] = 1.0
                    
                    time_token_rows.append(row)
            
            time_token_df = pd.DataFrame(time_token_rows)
            time_token_df.to_csv(time_token_csv_path, index=False)
            print(f"✅ 时间和Token详细分析已保存到: {time_token_csv_path}")

        # 打印汇总统计
        self.print_summary(comparison, df)

        return output_dir

    def print_summary(self, comparison: Dict, df: pd.DataFrame):
        """打印汇总统计"""
        print("\n" + "=" * 80)
        print("评估结果汇总（只包含有意义的对比）")
        print("=" * 80)

        print("\n📊 总体统计:")
        print(f"   - 公司数量: {df['company_name'].nunique()}")
        print(f"   - 架构数量: {df['architecture'].nunique()}")
        print(f"   - 总运行次数: {len(df)}")

        # Personas对比（2 Stage vs 4 Stage）
        if comparison.get("personas_comparison"):
            pc = comparison["personas_comparison"]
            print("\n👥 Personas对比（2 Stage vs 4 Stage）:")
            print(f"   2 Stage: 平均 {pc['two_stage']['avg']:.1f} 个 (n={pc['two_stage']['count']})")
            print(f"   4 Stage: 平均 {pc['four_stage']['avg']:.1f} 个 (n={pc['four_stage']['count']})")
            print(f"   差异: {pc['difference']:.1f}")
            print(f"   说明: {pc['note']}")

        # Mappings对比（2 Stage vs 3 Stage vs 4 Stage）
        if comparison.get("mappings_comparison"):
            mc = comparison["mappings_comparison"]
            print("\n🔗 Mappings对比（2 Stage vs 3 Stage vs 4 Stage）:")
            print(f"   2 Stage: 平均 {mc['two_stage']['avg']:.1f} 个 (n={mc['two_stage']['count']})")
            print(f"   3 Stage: 平均 {mc['three_stage']['avg']:.1f} 个 (n={mc['three_stage']['count']})")
            print(f"   4 Stage: 平均 {mc['four_stage']['avg']:.1f} 个 (n={mc['four_stage']['count']})")
            print(f"   最佳: {mc['best']}")
            print(f"   说明: {mc['note']}")

        # Sequences对比（2 Stage vs 3 Stage vs 4 Stage）
        if comparison.get("sequences_comparison"):
            sc = comparison["sequences_comparison"]
            print("\n📧 Sequences对比（2 Stage vs 3 Stage vs 4 Stage）:")
            print(f"   2 Stage: 平均 {sc['two_stage']['avg']:.1f} 个 (n={sc['two_stage']['count']})")
            print(f"   3 Stage: 平均 {sc['three_stage']['avg']:.1f} 个 (n={sc['three_stage']['count']})")
            print(f"   4 Stage: 平均 {sc['four_stage']['avg']:.1f} 个 (n={sc['four_stage']['count']})")
            print(f"   最佳: {sc['best']}")
            print(f"   说明: {sc['note']}")

        # 整体性能
        if comparison.get("overall_performance"):
            print("\n⚡ 整体性能对比:")
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
                print("\n🔍 异常值检测:")
                for arch, outlier_info in comparison["outliers"].items():
                    print(f"   {arch}:")
                    for i, (company, time) in enumerate(zip(outlier_info["companies"], outlier_info["times"])):
                        print(f"      - {company}: {time:.1f}秒 (已排除)")

        # 时间和Token详细分析
        if comparison.get("time_token_analysis"):
            tta = comparison["time_token_analysis"]
            
            print("\n⏱️  时间消耗详细分析:")
            for arch in ["Two-Stage", "Three-Stage", "Four-Stage"]:
                if arch in tta.get("time_analysis", {}):
                    ta = tta["time_analysis"][arch]
                    print(f"   {arch}:")
                    print(f"      - 平均时间: {ta['mean']:.1f}秒 (排除异常值后: {ta['mean_without_outliers']:.1f}秒)")
                    print(f"      - 中位数: {ta['median']:.1f}秒")
                    print(f"      - 标准差: {ta['std']:.1f}秒")
                    print(f"      - 范围: {ta['min']:.1f} - {ta['max']:.1f}秒")
                    print(f"      - 样本数: {ta['count']} (排除异常值后: {ta['count_without_outliers']})")
            
            print("\n🔢 Token消耗详细分析:")
            for arch in ["Two-Stage", "Three-Stage", "Four-Stage"]:
                if arch in tta.get("token_analysis", {}):
                    toa = tta["token_analysis"][arch]
                    print(f"   {arch}:")
                    print(f"      - 平均总Token: {toa['total_tokens_mean']:,.0f}")
                    print(f"      - 中位数: {toa['total_tokens_median']:,.0f}")
                    print(f"      - 范围: {toa['total_tokens_min']:,.0f} - {toa['total_tokens_max']:,.0f}")
                    print(f"      - 平均Prompt Token: {toa['prompt_tokens_mean']:,.0f} ({toa['prompt_ratio']:.1f}%)")
                    print(f"      - 平均Completion Token: {toa['completion_tokens_mean']:,.0f} ({toa['completion_ratio']:.1f}%)")
            
            print("\n📊 效率指标对比:")
            for arch in ["Two-Stage", "Three-Stage", "Four-Stage"]:
                if arch in tta.get("efficiency_metrics", {}):
                    em = tta["efficiency_metrics"][arch]
                    print(f"   {arch}:")
                    print(f"      - Token/秒: {em['tokens_per_second']:.1f}")
                    print(f"      - Mappings/Token: {em['mappings_per_token']:.4f}")
                    print(f"      - Sequences/Token: {em['sequences_per_token']:.4f}")
                    print(f"      - Mappings/秒: {em['mappings_per_second']:.2f}")
                    print(f"      - Sequences/秒: {em['sequences_per_second']:.2f}")
                    print(f"      - 时间/Mapping: {em['time_per_mapping']:.2f}秒")
                    print(f"      - 时间/Sequence: {em['time_per_sequence']:.2f}秒")
            
            print("\n📈 相对于2-Stage的变化:")
            for arch in ["Three-Stage", "Four-Stage"]:
                if arch in tta.get("comparison_summary", {}):
                    cs = tta["comparison_summary"][arch]
                    print(f"   {arch}:")
                    time_change = cs["time_vs_two_stage"]
                    token_change = cs["tokens_vs_two_stage"]
                    print(f"      时间变化:")
                    print(f"         - 绝对变化: {time_change['absolute_change']:+.1f}秒")
                    print(f"         - 百分比变化: {time_change['percentage_change']:+.1f}%")
                    print(f"         - 倍数: {time_change['multiplier']:.2f}x")
                    print(f"      Token变化:")
                    print(f"         - 绝对变化: {token_change['absolute_change']:+,.0f}")
                    print(f"         - 百分比变化: {token_change['percentage_change']:+.1f}%")
                    print(f"         - 倍数: {token_change['multiplier']:.2f}x")

        # 注意事项
        if comparison.get("notes"):
            print("\n⚠️  注意事项:")
            for note in comparison["notes"]:
                print(f"   - {note}")
            if comparison.get("outliers"):
                print(f"   - Three-Stage的平均时间已排除异常值（使用IQR方法检测）")

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

