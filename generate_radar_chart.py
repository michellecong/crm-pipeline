#!/usr/bin/env python3
"""
生成评估结果蛛形图（雷达图）

展示 Stage 2、3、4 三个架构在各项指标上的对比
"""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.transforms as mtransforms
from matplotlib.patches import Circle
import matplotlib.patches as mpatches

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def load_summary_data(csv_file: Path):
    """加载汇总数据"""
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # 计算平均值（排除异常值）
    def remove_outliers(values):
        if not values or len(values) <= 2:
            return values
        sorted_vals = sorted(values)
        q1_idx = len(sorted_vals) // 4
        q3_idx = 3 * len(sorted_vals) // 4
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        return [v for v in values if lower_bound <= v <= upper_bound]
    
    # 提取各架构的平均值
    data = {
        "2 Stage": {},
        "3 Stage": {},
        "4 Stage": {}
    }
    
    # 先收集所有架构的 tokens 和 times，用于计算全局 min/max
    all_tokens = []
    all_times = []
    for arch_name in ["2 Stage", "3 Stage", "4 Stage"]:
        prefix = arch_name.lower().replace(" ", "_")
        tokens = [
            int(r.get(f"{prefix}_tokens", 0)) 
            for r in rows if int(r.get(f"{prefix}_tokens", 0)) > 0
        ]
        all_tokens.extend(tokens)
        
        times = remove_outliers([
            float(r.get(f"{prefix}_time_minutes", 0)) 
            for r in rows if float(r.get(f"{prefix}_time_minutes", 0)) > 0
        ])
        all_times.extend(times)
    
    # 计算全局 min/max（用于跨架构比较）
    global_min_tokens = min(all_tokens) if all_tokens else 0
    global_max_tokens = max(all_tokens) if all_tokens else 1
    global_min_time = min(all_times) if all_times else 0
    global_max_time = max(all_times) if all_times else 1
    
    for arch_name in ["2 Stage", "3 Stage", "4 Stage"]:
        prefix = arch_name.lower().replace(" ", "_")
        
        # Persona 质量
        persona_qualities = remove_outliers([
            float(r.get(f"{prefix}_persona_quality", 0)) 
            for r in rows if float(r.get(f"{prefix}_persona_quality", 0)) > 0
        ])
        data[arch_name]["Persona Quality"] = sum(persona_qualities) / len(persona_qualities) if persona_qualities else 0
        
        # Mapping 质量
        mapping_overalls = remove_outliers([
            float(r.get(f"{prefix}_mapping_overall", 0)) 
            for r in rows if float(r.get(f"{prefix}_mapping_overall", 0)) > 0
        ])
        data[arch_name]["Mapping Quality"] = sum(mapping_overalls) / len(mapping_overalls) if mapping_overalls else 0
        
        # Outreach 质量
        outreach_overalls = remove_outliers([
            float(r.get(f"{prefix}_outreach_overall", 0)) 
            for r in rows if float(r.get(f"{prefix}_outreach_overall", 0)) > 0
        ])
        data[arch_name]["Outreach Quality"] = sum(outreach_overalls) / len(outreach_overalls) if outreach_overalls else 0
        
        # Token 效率（使用全局 min/max 进行比较）
        tokens = [
            int(r.get(f"{prefix}_tokens", 0)) 
            for r in rows if int(r.get(f"{prefix}_tokens", 0)) > 0
        ]
        if tokens and global_max_tokens > global_min_tokens:
            avg_tokens = sum(tokens) / len(tokens)
            # 使用全局范围进行归一化：时间/token 越小，效率越高
            normalized = (avg_tokens - global_min_tokens) / (global_max_tokens - global_min_tokens)
            data[arch_name]["Token Efficiency"] = 1 - normalized  # 反转：效率 = 1 - 消耗比例
        elif tokens:
            # 如果所有架构的 tokens 都相同，效率设为 1.0
            data[arch_name]["Token Efficiency"] = 1.0
        else:
            data[arch_name]["Token Efficiency"] = 0
        
        # 时间效率（使用全局 min/max 进行比较）
        times = remove_outliers([
            float(r.get(f"{prefix}_time_minutes", 0)) 
            for r in rows if float(r.get(f"{prefix}_time_minutes", 0)) > 0
        ])
        if times and global_max_time > global_min_time:
            avg_time = sum(times) / len(times)
            # 使用全局范围进行归一化：时间越小，效率越高
            normalized = (avg_time - global_min_time) / (global_max_time - global_min_time)
            data[arch_name]["Time Efficiency"] = 1 - normalized  # 反转：效率 = 1 - 消耗比例
        elif times:
            # 如果所有架构的时间都相同，效率设为 1.0
            data[arch_name]["Time Efficiency"] = 1.0
        else:
            data[arch_name]["Time Efficiency"] = 0
    
    return data


def create_radar_chart(data: dict, output_file: Path):
    """创建雷达图"""
    # 指标列表（英文）
    categories = ["Persona Quality", "Mapping Quality", "Outreach Quality", "Token Efficiency", "Time Efficiency"]
    N = len(categories)
    
    # 计算角度
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # 闭合图形
    
    # 创建图表 - 增大尺寸以适应poster
    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(projection='polar'))
    fig.patch.set_facecolor('none')  # 设置图形背景为透明
    ax.set_facecolor('none')  # 设置坐标轴背景为透明
    
    # 移除外层圆形边框
    ax.spines['polar'].set_visible(False)
    ax.set_frame_on(False)
    
    # 颜色配置（黄绿色调，更精致）
    colors = {
        "2 Stage": "#B8E994",  # 浅黄绿色
        "3 Stage": "#78E08F",  # 中黄绿色
        "4 Stage": "#38A169"   # 深黄绿色
    }
    
    # 绘制每个架构 - 增强视觉效果
    for arch_name, values in data.items():
        values_list = [values[cat] for cat in categories]
        values_list += values_list[:1]  # 闭合图形
        
        # 更粗的线条，更大的标记点 - 线条颜色更浅
        # 将颜色转换为带透明度的版本
        rgba_color = mcolors.to_rgba(colors[arch_name], alpha=0.6)  # 添加透明度使线条更浅
        ax.plot(angles, values_list, 'o-', linewidth=3.5, 
                markersize=10, label=arch_name, color=rgba_color,
                markerfacecolor=colors[arch_name], markeredgecolor='white', 
                markeredgewidth=1.5)
        # 更subtle的填充
        ax.fill(angles, values_list, alpha=0.15, color=colors[arch_name])
    
    # 设置 y 轴（0-1）- 移除外层圆
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], 
                       fontsize=24, color='#666666', fontweight='medium')
    
    # 设置角度标签 - 更大更清晰的字体
    ax.set_thetagrids(np.degrees(angles[:-1]), labels=categories,
                      fontsize=28, fontweight='medium', color='#333333')
    # 设置标签距离
    ax.tick_params(axis='x', pad=15)
    
    # 单独调整"Persona Quality"标签位置，使其更靠外（向下移动）
    for label in ax.get_xticklabels():
        if label.get_text() == "Persona Quality":
            # 使用transform调整位置，向下移动更多
            offset = mtransforms.ScaledTranslation(0, -0.35, ax.figure.dpi_scale_trans)
            label.set_transform(label.get_transform() + offset)
            break
    
    # 更精致的网格线（只保留圆形网格）- 适中的颜色
    ax.grid(True, linestyle='--', alpha=0.7, linewidth=1.2, color='#888888')
    
    # 移除径向网格线（从中心到外圈的直线），但保留标签
    # 径向线是theta方向的网格线，我们需要隐藏它们
    for line in ax.get_lines():
        xdata, ydata = line.get_data()
        # 径向线特征：x值（角度）恒定，y值（半径）从0到1
        if len(xdata) > 1 and len(ydata) > 1:
            # 检查是否是径向线：x值几乎不变，y值从接近0到接近1
            x_unique = len(set([round(x, 3) for x in xdata])) <= 2
            y_range = max(ydata) - min(ydata) > 0.5
            if x_unique and y_range and min(ydata) < 0.2:
                line.set_visible(False)
    
    # 添加图例 - 更专业的位置和样式
    plt.legend(loc='upper right', bbox_to_anchor=(1.25, 1.15), 
               fontsize=26, frameon=False, labelspacing=0.8)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=400, bbox_inches='tight', transparent=True, 
                facecolor='none', edgecolor='none')
    print(f"✅ 雷达图已保存到: {output_file}")
    plt.close()


def create_comparison_bar_chart(data: dict, output_file: Path):
    """创建对比柱状图作为补充"""
    categories = ["Persona Quality", "Mapping Quality", "Outreach Quality", "Token Efficiency", "Time Efficiency"]
    # 将标签分成两行显示，避免重合
    category_labels = ["Persona\nQuality", "Mapping\nQuality", "Outreach\nQuality", 
                      "Token\nEfficiency", "Time\nEfficiency"]
    
    x = np.arange(len(categories))
    width = 0.28  # 稍微加宽柱子
    
    # 增大尺寸以适应poster
    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor('none')  # 设置图形背景为透明
    ax.set_facecolor('none')  # 设置坐标轴背景为透明
    
    # 移除顶部和右侧边框，更简洁
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    
    colors = {
        "2 Stage": "#B8E994",  # 浅黄绿色
        "3 Stage": "#78E08F",  # 中黄绿色
        "4 Stage": "#38A169"   # 深黄绿色
    }
    
    for i, (arch_name, values) in enumerate(data.items()):
        values_list = [values[cat] for cat in categories]
        offset = (i - 1) * width
        # 添加边框使柱子更精致
        ax.bar(x + offset, values_list, width, label=arch_name, 
               color=colors[arch_name], alpha=0.85, 
               edgecolor='white', linewidth=1.5)
    
    ax.set_ylabel('Score (0-1)', fontsize=26, fontweight='medium', color='#333333', labelpad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(category_labels, fontsize=26, fontweight='medium', color='#333333')
    ax.set_ylim(0, 1.1)
    
    # 优化y轴标签
    ax.tick_params(axis='y', labelsize=24, colors='#666666')
    ax.tick_params(axis='x', labelsize=26, colors='#333333')
    
    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.15), 
              fontsize=26, frameon=False, labelspacing=0.8)
    # 更subtle的网格线
    ax.grid(True, axis='y', linestyle='--', alpha=0.25, linewidth=0.8, color='#CCCCCC')
    ax.set_axisbelow(True)  # 网格线在柱子后面
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=400, bbox_inches='tight', transparent=True,
                facecolor='none', edgecolor='none')
    print(f"✅ 柱状图已保存到: {output_file}")
    plt.close()


def main():
    """主函数"""
    # 找到最新的汇总文件
    summary_files = sorted(Path("evaluation_results").glob("comprehensive_evaluation_summary_*.csv"), reverse=True)
    
    if not summary_files:
        print("❌ 未找到汇总文件")
        return
    
    csv_file = summary_files[0]
    print(f"📊 加载数据: {csv_file.name}")
    
    # 加载数据
    data = load_summary_data(csv_file)
    
    # 打印数据摘要
    print("\n数据摘要:")
    for arch_name, values in data.items():
        print(f"\n{arch_name}:")
        for category, value in values.items():
            print(f"  {category}: {value:.3f}")
    
    # 生成图表
    output_dir = Path("evaluation_results")
    
    # 雷达图
    radar_file = output_dir / "architecture_comparison_radar.png"
    create_radar_chart(data, radar_file)
    
    # 柱状图
    bar_file = output_dir / "architecture_comparison_bar.png"
    create_comparison_bar_chart(data, bar_file)
    
    print("\n✅ 所有图表已生成完成！")


if __name__ == "__main__":
    main()

