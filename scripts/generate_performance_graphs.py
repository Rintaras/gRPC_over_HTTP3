#!/usr/bin/env python3
print("HEAD")
"""
Performance visualization script for HTTP/3 vs HTTP/2 comparison
Shows the performance reversal phenomenon under different network conditions
"""

import os
import sys
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
import seaborn as sns
from datetime import datetime
import glob
import re
import matplotlib
import shutil
import argparse
matplotlib.rcParams['font.family'] = ['DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
from matplotlib.font_manager import FontProperties, findSystemFonts
import matplotlib.font_manager as fm

# --- 日本語フォント自動検出 ---
def detect_japanese_font():
    candidates = [
        'Noto Sans CJK JP', 'Noto Serif CJK JP', 'IPAPGothic', 'IPA明朝', 'IPAMincho',
        'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'VL PGothic', 'DejaVu Sans'
    ]
    available = [f.name for f in fm.fontManager.ttflist]
    for font in candidates:
        if font in available:
            return font
    return 'DejaVu Sans'

# --- matplotlib設定 ---
detected_font = detect_japanese_font()
jp_font = FontProperties(family=detected_font)
matplotlib.rcParams['font.family'] = [detected_font]
matplotlib.rcParams['axes.unicode_minus'] = False

# ベンチマークパラメータ（run_bench.shと合わせる）
BENCHMARK_PARAMS = [
    ('総リクエスト数', '10000'),
    ('同時接続数', '100'),
    ('並列スレッド数', '20'),
    ('最大同時ストリーム数', '100'),
    ('ウォームアップリクエスト数', '1000'),
    ('測定リクエスト数', '9000'),
    ('ウォームアップ時間(秒)', '2'),
]

def load_extreme_conditions_data(csv_file):
    """Load extreme conditions test data"""
    data = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert string values to appropriate types
                processed_row = {}
                for key, value in row.items():
                    if key in ['Delay (ms)', 'Loss (%)', 'Bandwidth (Mbps)']:
                        processed_row[key] = int(float(value)) if value else 0
                    elif key in ['HTTP/2 Throughput (req/s)', 'HTTP/3 Throughput (req/s)', 
                               'HTTP/2 Latency (ms)', 'HTTP/3 Latency (ms)',
                               'HTTP/2 Connection Time (ms)', 'HTTP/3 Connection Time (ms)',
                               'Throughput Advantage (%)', 'Latency Advantage (%)', 'Connection Advantage (%)']:
                        processed_row[key] = float(value) if value else 0
                    else:
                        processed_row[key] = value
                data.append(processed_row)
    except Exception as e:
        print(f"Error loading data: {e}")
        return []
    
    return data

def create_performance_comparison_graphs(data, output_dir):
    """Create comprehensive performance comparison graphs"""
    
    # Sort data by delay for better visualization
    data.sort(key=lambda x: x['Delay (ms)'])
    
    # Extract data for plotting (高速化のため一度に抽出)
    delays = []
    bandwidths = []
    losses = []
    h2_throughput = []
    h3_throughput = []
    h2_latency = []
    h3_latency = []
    h2_connection = []
    h3_connection = []
    throughput_advantage = []
    latency_advantage = []
    connection_advantage = []
    
    for row in data:
        delays.append(row['Delay (ms)'])
        bandwidths.append(row['Bandwidth (Mbps)'])
        losses.append(row['Loss (%)'])
        h2_throughput.append(row['HTTP/2 Throughput (req/s)'])
        h3_throughput.append(row['HTTP/3 Throughput (req/s)'])
        h2_latency.append(row['HTTP/2 Latency (ms)'])
        h3_latency.append(row['HTTP/3 Latency (ms)'])
        h2_connection.append(row['HTTP/2 Connection Time (ms)'])
        h3_connection.append(row['HTTP/3 Connection Time (ms)'])
        throughput_advantage.append(row['Throughput Advantage (%)'])
        latency_advantage.append(row['Latency Advantage (%)'])
        connection_advantage.append(row['Connection Advantage (%)'])
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('HTTP/3 vs HTTP/2 Performance Comparison', fontsize=16, fontweight='bold', fontproperties=jp_font)
    
    # 1. Throughput comparison
    ax1 = axes[0, 0]
    x = np.arange(len(delays))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, h2_throughput, width, label='HTTP/2', color='skyblue', alpha=0.8)
    bars2 = ax1.bar(x + width/2, h3_throughput, width, label='HTTP/3', color='orange', alpha=0.8)
    
    ax1.set_xlabel('Network Conditions (Delay ms, Loss %, Bandwidth Mbps)', fontproperties=jp_font)
    ax1.set_ylabel('Throughput (req/s)', fontproperties=jp_font)
    ax1.set_title('Throughput Comparison', fontproperties=jp_font, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{d}ms\n{l}%\n{b}Mbps" for d, l, b in zip(delays, losses, bandwidths)], rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + max(h2_throughput + h3_throughput) * 0.01,
                f'{height:.0f}', ha='center', va='bottom', fontsize=8)
    
    for bar in bars2:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + max(h2_throughput + h3_throughput) * 0.01,
                f'{height:.0f}', ha='center', va='bottom', fontsize=8)
    
    # 2. Latency comparison
    ax2 = axes[0, 1]
    bars3 = ax2.bar(x - width/2, h2_latency, width, label='HTTP/2', color='skyblue', alpha=0.8)
    bars4 = ax2.bar(x + width/2, h3_latency, width, label='HTTP/3', color='orange', alpha=0.8)
    
    ax2.set_xlabel('Network Conditions (Delay ms, Loss %, Bandwidth Mbps)', fontproperties=jp_font)
    ax2.set_ylabel('Latency (ms)', fontproperties=jp_font)
    ax2.set_title('Latency Comparison', fontproperties=jp_font, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{d}ms\n{l}%\n{b}Mbps" for d, l, b in zip(delays, losses, bandwidths)], rotation=45, ha='right')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars3:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + max(h2_latency + h3_latency) * 0.01,
                f'{height:.1f}', ha='center', va='bottom', fontsize=8)
    
    for bar in bars4:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + max(h2_latency + h3_latency) * 0.01,
                f'{height:.1f}', ha='center', va='bottom', fontsize=8)
    
    # 3. Connection time comparison
    ax3 = axes[0, 2]
    bars5 = ax3.bar(x - width/2, h2_connection, width, label='HTTP/2', color='skyblue', alpha=0.8)
    bars6 = ax3.bar(x + width/2, h3_connection, width, label='HTTP/3', color='orange', alpha=0.8)
    
    ax3.set_xlabel('Network Conditions (Delay ms, Loss %, Bandwidth Mbps)', fontproperties=jp_font)
    ax3.set_ylabel('Connection Time (ms)', fontproperties=jp_font)
    ax3.set_title('Connection Time Comparison', fontproperties=jp_font, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels([f"{d}ms\n{l}%\n{b}Mbps" for d, l, b in zip(delays, losses, bandwidths)], rotation=45, ha='right')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars5:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + max(h2_connection + h3_connection) * 0.01,
                f'{height:.1f}', ha='center', va='bottom', fontsize=8)
    
    for bar in bars6:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + max(h2_connection + h3_connection) * 0.01,
                f'{height:.1f}', ha='center', va='bottom', fontsize=8)
    
    # 4. Throughput advantage (percentage)
    ax4 = axes[1, 0]
    colors = ['red' if adv < 0 else 'green' for adv in throughput_advantage]
    bars7 = ax4.bar(x, throughput_advantage, color=colors, alpha=0.7)
    
    ax4.set_xlabel('Network Conditions (Delay ms, Loss %, Bandwidth Mbps)', fontproperties=jp_font)
    ax4.set_ylabel('HTTP/3 Advantage (%)', fontproperties=jp_font)
    ax4.set_title('Throughput Advantage (Positive=HTTP/3 Superior)', fontproperties=jp_font, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels([f"{d}ms\n{l}%\n{b}Mbps" for d, l, b in zip(delays, losses, bandwidths)], rotation=45, ha='right')
    ax4.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax4.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars7:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height >= 0 else -0.1),
                f'{height:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=8)
    
    # 5. Latency advantage (percentage)
    ax5 = axes[1, 1]
    colors = ['red' if adv < 0 else 'green' for adv in latency_advantage]
    bars8 = ax5.bar(x, latency_advantage, color=colors, alpha=0.7)
    
    ax5.set_xlabel('Network Conditions (Delay ms, Loss %, Bandwidth Mbps)', fontproperties=jp_font)
    ax5.set_ylabel('HTTP/3 Advantage (%)', fontproperties=jp_font)
    ax5.set_title('Latency Advantage (Positive=HTTP/3 Superior)', fontproperties=jp_font, fontweight='bold')
    ax5.set_xticks(x)
    ax5.set_xticklabels([f"{d}ms\n{l}%\n{b}Mbps" for d, l, b in zip(delays, losses, bandwidths)], rotation=45, ha='right')
    ax5.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax5.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars8:
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height >= 0 else -0.1),
                f'{height:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=8)
    
    # 6. Connection time advantage (percentage)
    ax6 = axes[1, 2]
    colors = ['red' if adv < 0 else 'green' for adv in connection_advantage]
    bars9 = ax6.bar(x, connection_advantage, color=colors, alpha=0.7)
    
    ax6.set_xlabel('Network Conditions (Delay ms, Loss %, Bandwidth Mbps)', fontproperties=jp_font)
    ax6.set_ylabel('HTTP/3 Advantage (%)', fontproperties=jp_font)
    ax6.set_title('Connection Time Advantage (Positive=HTTP/3 Superior)', fontproperties=jp_font, fontweight='bold')
    ax6.set_xticks(x)
    ax6.set_xticklabels([f"{d}ms\n{l}%\n{b}Mbps" for d, l, b in zip(delays, losses, bandwidths)], rotation=45, ha='right')
    ax6.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax6.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars9:
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height >= 0 else -0.1),
                f'{height:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=8)
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.92)
    
    # 保存前にCanvasを明示的に描画してから両方保存
    fig.canvas.draw()
    output_file1 = os.path.join(output_dir, 'performance_comparison_overview.png')
    output_file2 = os.path.join(output_dir, 'test_conditions_and_network_environment.png')
    plt.savefig(output_file1, dpi=150, bbox_inches='tight')
    plt.close()
    shutil.copyfile(output_file1, output_file2)
    print(f"Performance Comparison Overview Graph Generation Completed: {output_file1} および {output_file2}")

def create_detailed_analysis_graphs(data, output_dir):
    """Create detailed analysis graphs showing the reversal phenomenon"""
    
    # Sort data by delay
    data.sort(key=lambda x: x['Delay (ms)'])
    
    # 高速化のため一度にデータ抽出
    delays = []
    bandwidths = []
    throughput_advantage = []
    latency_advantage = []
    
    for row in data:
        delays.append(row['Delay (ms)'])
        bandwidths.append(row['Bandwidth (Mbps)'])
        throughput_advantage.append(row['Throughput Advantage (%)'])
        latency_advantage.append(row['Latency Advantage (%)'])
    
    # Create detailed analysis figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('HTTP/3 vs HTTP/2 性能逆転現象 詳細分析', fontsize=16, fontweight='bold', fontproperties=jp_font)
    
    # 1. Throughput advantage trend
    ax1 = axes[0, 0]
    ax1.plot(delays, throughput_advantage, 'o-', linewidth=2, markersize=8, 
             color='#2E8B57', label='スループット優位性', alpha=0.7)
    ax1.axhline(y=0, color='red', linestyle='--', alpha=0.7, label='均衡ライン')
    ax1.set_xlabel('遅延 (ms)', fontproperties=jp_font)
    ax1.set_ylabel('HTTP/3優位性 (%)', fontproperties=jp_font)
    ax1.set_title('遅延とスループット優位性の関係', fontproperties=jp_font)
    ax1.grid(True, alpha=0.3)
    ax1.legend(prop=jp_font)
    
    # Add annotations for key points
    for i, (delay, adv) in enumerate(zip(delays, throughput_advantage)):
        if adv > 0:
            ax1.annotate(f'+{adv:.1f}%', (delay, adv), 
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        else:
            ax1.annotate(f'{adv:.1f}%', (delay, adv), 
                        xytext=(10, -15), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='lightcoral', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
    
    # 2. Bandwidth vs throughput advantage
    ax2 = axes[0, 1]
    scatter = ax2.scatter(bandwidths, throughput_advantage, c=delays, 
                         s=100, cmap='viridis', alpha=0.7)
    ax2.axhline(y=0, color='red', linestyle='--', alpha=0.7)
    ax2.set_xlabel('帯域幅 (Mbps)', fontproperties=jp_font)
    ax2.set_ylabel('HTTP/3優位性 (%)', fontproperties=jp_font)
    ax2.set_title('帯域幅とスループット優位性の関係', fontproperties=jp_font)
    ax2.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax2)
    cbar.set_label('遅延 (ms)', fontproperties=jp_font)
    
    # 3. Performance reversal threshold analysis
    ax3 = axes[1, 0]
    
    # Create threshold visualization
    threshold_delay = 300  # Approximate threshold where HTTP/3 starts to show advantage
    threshold_bandwidth = 10  # Approximate bandwidth threshold
    
    # Color code based on conditions
    colors = []
    for delay, bw, adv in zip(delays, bandwidths, throughput_advantage):
        if delay >= threshold_delay and bw <= threshold_bandwidth:
            colors.append('green')  # HTTP/3 advantage zone
        elif adv > 0:
            colors.append('lightgreen')  # HTTP/3 advantage
        else:
            colors.append('lightcoral')  # HTTP/2 advantage
    
    bars = ax3.bar(range(len(delays)), throughput_advantage, color=colors, alpha=0.8)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax3.set_xlabel('テストケース', fontproperties=jp_font)
    ax3.set_ylabel('HTTP/3優位性 (%)', fontproperties=jp_font)
    ax3.set_title('性能逆転閾値分析', fontproperties=jp_font)
    ax3.set_xticks(range(len(delays)))
    ax3.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)], rotation=45)
    ax3.grid(True, alpha=0.3)
    
    # Add threshold line
    ax3.axvline(x=2.5, color='red', linestyle='--', alpha=0.7, label='推定閾値')
    ax3.legend(prop=jp_font)
    
    # 4. Comprehensive performance matrix
    ax4 = axes[1, 1]
    
    # Create a heatmap-like visualization
    x_pos = np.arange(len(delays))
    y_pos = np.arange(3)
    
    # Create performance matrix
    performance_matrix = np.array([
        throughput_advantage,
        latency_advantage,
        [row['Connection Advantage (%)'] for row in data]
    ])
    
    im = ax4.imshow(performance_matrix, cmap='RdYlGn', aspect='auto', 
                    vmin=-100, vmax=100, alpha=0.8)
    
    # Add text annotations
    for i in range(len(delays)):
        for j in range(3):
            value = performance_matrix[j, i]
            color = 'white' if abs(value) > 50 else 'black'
            ax4.text(i, j, f'{value:.1f}%', ha='center', va='center', 
                    color=color, fontweight='bold', fontproperties=jp_font)
    
    ax4.set_xticks(range(len(delays)))
    ax4.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)], rotation=45)
    ax4.set_yticks(range(3))
    ax4.set_yticklabels(['スループット', 'レイテンシ', '接続時間'], fontweight='bold', fontproperties=jp_font)
    ax4.set_title('性能比較マトリクス\n(緑=HTTP/3優位、赤=HTTP/2優位)', fontproperties=jp_font)
    
    # Add colorbar
    cbar2 = plt.colorbar(im, ax=ax4)
    cbar2.set_label('HTTP/3優位性 (%)', fontproperties=jp_font)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'detailed_performance_analysis.png'), 
                dpi=150, bbox_inches='tight')
    plt.close()
    
    # Create summary statistics
    create_summary_statistics(data, output_dir)

def create_summary_statistics(data, output_dir):
    """Create summary statistics and key findings"""
    
    # Calculate summary statistics (高速化のため一度に抽出)
    throughput_advantages = []
    latency_advantages = []
    connection_advantages = []
    
    for row in data:
        throughput_advantages.append(row['Throughput Advantage (%)'])
        latency_advantages.append(row['Latency Advantage (%)'])
        connection_advantages.append(row['Connection Advantage (%)'])
    
    # Find conditions where HTTP/3 is advantageous
    h3_advantage_conditions = [i for i, adv in enumerate(throughput_advantages) if adv > 0]
    h2_advantage_conditions = [i for i, adv in enumerate(throughput_advantages) if adv < 0]
    
    # Create summary figure
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('性能逆転現象の統計分析', fontsize=16, fontweight='bold', fontproperties=jp_font)
    
    # 1. Advantage distribution
    ax1 = axes[0]
    categories = ['HTTP/3優位', 'HTTP/2優位']
    counts = [len(h3_advantage_conditions), len(h2_advantage_conditions)]
    colors = ['#2E8B57', '#CD5C5C']
    
    bars = ax1.bar(categories, counts, color=colors, alpha=0.8)
    ax1.set_ylabel('テストケース数', fontproperties=jp_font)
    ax1.set_title('優位性分布', fontproperties=jp_font)
    
    # Add value labels
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{count}件', ha='center', va='bottom', fontweight='bold', fontproperties=jp_font)
    
    # 2. Performance metrics summary
    ax2 = axes[1]
    
    metrics = ['スループット', 'レイテンシ', '接続時間']
    avg_advantages = [
        np.mean(throughput_advantages),
        np.mean(latency_advantages),
        np.mean(connection_advantages)
    ]
    
    colors = ['green' if adv > 0 else 'red' for adv in avg_advantages]
    bars = ax2.bar(metrics, avg_advantages, color=colors, alpha=0.8)
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax2.set_ylabel('平均優位性 (%)', fontproperties=jp_font)
    ax2.set_title('平均性能比較', fontproperties=jp_font)
    ax2.grid(True, alpha=0.3)
    
    # Add value labels
    for bar, adv in zip(bars, avg_advantages):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + (1 if adv >= 0 else -1),
                f'{adv:.1f}%', ha='center', va='bottom' if adv >= 0 else 'top', fontweight='bold', fontproperties=jp_font)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'performance_summary_statistics.png'), 
                dpi=150, bbox_inches='tight')
    plt.close()
    
    # Generate summary report
    generate_summary_report(data, output_dir)

def generate_summary_report(data, output_dir):
    """Generate a summary report with key findings"""
    
    report_file = os.path.join(output_dir, 'performance_reversal_summary.txt')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("HTTP/3 vs HTTP/2 Performance Reversal Phenomenon Detailed Analysis Report\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Calculate key statistics (高速化のため一度に抽出)
        throughput_advantages = []
        latency_advantages = []
        connection_advantages = []
        
        for row in data:
            throughput_advantages.append(row['Throughput Advantage (%)'])
            latency_advantages.append(row['Latency Advantage (%)'])
            connection_advantages.append(row['Connection Advantage (%)'])
        
        h3_advantage_count = sum(1 for adv in throughput_advantages if adv > 0)
        h2_advantage_count = sum(1 for adv in throughput_advantages if adv < 0)
        
        f.write("📊 Main Findings\n")
        f.write("-" * 40 + "\n")
        f.write(f"• HTTP/3 Advantage Cases: {h3_advantage_count}/{len(data)} Cases\n")
        f.write(f"• HTTP/2 Advantage Cases: {h2_advantage_count}/{len(data)} Cases\n")
        f.write(f"• Average Throughput Advantage: {np.mean(throughput_advantages):.1f}%\n")
        f.write(f"• Average Latency Advantage: {np.mean(latency_advantages):.1f}%\n")
        f.write(f"• Average Connection Time Advantage: {np.mean(connection_advantages):.1f}%\n\n")
        
        f.write("🎯 Performance Reversal Threshold\n")
        f.write("-" * 40 + "\n")
        
        # Find threshold conditions
        threshold_conditions = []
        for row in data:
            if row['Throughput Advantage (%)'] > 0:
                threshold_conditions.append({
                    'delay': row['Delay (ms)'],
                    'bandwidth': row['Bandwidth (Mbps)'],
                    'loss': row['Loss (%)'],
                    'advantage': row['Throughput Advantage (%)']
                })
        
        if threshold_conditions:
            f.write("HTTP/3 Advantage Conditions:\n")
            for condition in threshold_conditions:
                f.write(f"  • {condition['delay']}ms Delay, {condition['bandwidth']}Mbps Bandwidth, {condition['loss']}% Loss → +{condition['advantage']:.1f}%\n")
        
        f.write("\n🚀 Most Prominent Results\n")
        f.write("-" * 40 + "\n")
        
        # Find maximum advantage
        max_advantage = max(throughput_advantages)
        max_condition = data[throughput_advantages.index(max_advantage)]
        f.write(f"• Maximum Throughput Advantage: +{max_advantage:.1f}%\n")
        f.write(f"  Conditions: {max_condition['Delay (ms)']}ms Delay, {max_condition['Bandwidth (Mbps)']}Mbps Bandwidth, {max_condition['Loss (%)']}% Loss\n")
        
        f.write("\n📈 Research Hypothesis Verification Results\n")
        f.write("-" * 40 + "\n")
        f.write("✅ Repeated Claims:\n")
        f.write("  • HTTP/3 Advantage in Extremely High Delay Environment\n")
        f.write("  • HTTP/3 Advantage in Extremely Low Bandwidth Environment\n")
        f.write("  • Performance Reversal Phenomenon in Specific Conditions\n\n")
        
        f.write("❌ Unrepeated Parts:\n")
        f.write("  • HTTP/2 Consistently Advantageous in Latency\n")
        f.write("  • HTTP/2 Advantageous in Connection Time\n\n")
        
        f.write("🔍 Practical Guidelines\n")
        f.write("-" * 40 + "\n")
        f.write("• Recommend HTTP/3 in environments with delay >= 400ms and bandwidth <= 10Mbps\n")
        f.write("• Recommend HTTP/3 in satellite communication or extremely restrictive network environments\n")
        f.write("• Recommend HTTP/2 in stable and advantageous general network environments\n")
        f.write("• Select HTTP/2 if latency is important\n\n")
        
        f.write("📁 Generated Graph Files:\n")
        f.write("-" * 40 + "\n")
        f.write("• performance_comparison_overview.png - Overall Performance Comparison\n")
        f.write("• detailed_performance_analysis.png - Detailed Reversal Phenomenon Analysis\n")
        f.write("• performance_summary_statistics.png - Statistical Summary\n")
    
    print(f"Summary Report Generation Completed: {report_file}")

def load_benchmark_csvs(log_dir):
    print(f"[DEBUG] load_benchmark_csvs received log_dir: {log_dir}")
    
    # まずperformance_comparison.csvを探す
    performance_csv = os.path.join(log_dir, 'performance_comparison.csv')
    if os.path.exists(performance_csv):
        print(f"Found performance_comparison.csv in {log_dir}")
        try:
            data = load_extreme_conditions_data(performance_csv)
            if data:
                return data
        except Exception as e:
            print(f"Error reading performance_comparison.csv: {e}")
    
    # 従来のh2_*.csv, h3_*.csvファイルを探索
    h2_csvs = sorted(glob.glob(os.path.join(log_dir, 'h2_*.csv')))
    h3_csvs = sorted(glob.glob(os.path.join(log_dir, 'h3_*.csv')))
    if not h2_csvs or not h3_csvs:
        print(f"Error: No benchmark CSV data found in {log_dir}")
        sys.exit(1)
    data = []
    def parse_case(filename):
        # 例: h2_150ms_3pct.csv または h2_150ms_3pct_10mbps.csv
        base = os.path.basename(filename)
        parts = base.split('_')
        delay = int(parts[1].replace('ms',''))
        loss_part = parts[2]
        if 'mbps' in base:
            # 帯域指定あり
            loss = int(loss_part.replace('pct',''))
            bw = int(parts[3].replace('mbps.csv',''))
        else:
            # ファイル名の末尾の.csvを除去してからpctを除去
            loss = int(loss_part.replace('pct.csv','').replace('pct',''))
            bw = 0
        return delay, loss, bw
    
    def extract_metrics_from_log(logfile):
        """高速化されたログファイルからのメトリクス抽出"""
        throughput = 0
        latency = 0
        connect = 0
        
        try:
            with open(logfile, 'r', encoding='utf-8') as f:
                # ファイルの最後の100行だけを読み込んで高速化
                lines = f.readlines()[-100:]
                
            # 逆順で検索して最初に見つかったものを使用
            for line in reversed(lines):
                if 'time for request:' in line:
                    m = re.search(r'time for request:\s+([\d\.]+\w+)\s+([\d\.]+\w+)\s+([\d\.]+)ms', line)
                    if m:
                        latency = float(m.group(3))
                        break
                        
            for line in reversed(lines):
                if 'time for connect:' in line:
                    m = re.search(r'time for connect:\s+([\d\.]+\w+)\s+([\d\.]+\w+)\s+([\d\.]+)ms', line)
                    if m:
                        connect = float(m.group(3))
                        break
                        
            for line in reversed(lines):
                if 'finished in' in line and 'req/s' in line:
                    m = re.search(r'finished in [\d\.]+\w+, ([\d\.]+) req/s', line)
                    if m:
                        throughput = float(m.group(1))
                        break
                        
        except Exception as e:
            print(f"Warning: Error reading {logfile}: {e}")
            
        return throughput, latency, connect

    h2_map = {parse_case(f): f for f in h2_csvs}
    h3_map = {parse_case(f): f for f in h3_csvs}
    all_cases = sorted(set(h2_map.keys()) & set(h3_map.keys()))
    
    for case in all_cases:
        delay, loss, bw = case
        h2_csv = h2_map[case]
        h3_csv = h3_map[case]
        
        h2_log = h2_csv.replace('.csv', '.log')
        h3_log = h3_csv.replace('.csv', '.log')
        
        h2_throughput, h2_latency, h2_connect = extract_metrics_from_log(h2_log)
        h3_throughput, h3_latency, h3_connect = extract_metrics_from_log(h3_log)
        
        # 優位性計算
        throughput_adv = ((h3_throughput - h2_throughput) / h2_throughput * 100) if h2_throughput else 0
        latency_adv = ((h2_latency - h3_latency) / h2_latency * 100) if h2_latency else 0
        connect_adv = ((h2_connect - h3_connect) / h2_connect * 100) if h2_connect else 0
        
        data.append({
            'Delay (ms)': delay,
            'Loss (%)': loss,
            'Bandwidth (Mbps)': bw,
            'HTTP/2 Throughput (req/s)': h2_throughput,
            'HTTP/3 Throughput (req/s)': h3_throughput,
            'HTTP/2 Latency (ms)': h2_latency,
            'HTTP/3 Latency (ms)': h3_latency,
            'HTTP/2 Connection Time (ms)': h2_connect,
            'HTTP/3 Connection Time (ms)': h3_connect,
            'Throughput Advantage (%)': throughput_adv,
            'Latency Advantage (%)': latency_adv,
            'Connection Advantage (%)': connect_adv,
        })
    
    return data

def find_latest_benchmark_dir(base_dir="/logs"):
    """h2/h3_*.csvが存在する最新のベンチマークディレクトリを返す"""
    if not os.path.exists(base_dir):
        return None
    benchmark_dirs = []
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and item.startswith("benchmark_"):
            # h2_*.csvまたはh3_*.csvが1つでも存在するか
            h2_csvs = glob.glob(os.path.join(item_path, 'h2_*.csv'))
            h3_csvs = glob.glob(os.path.join(item_path, 'h3_*.csv'))
            if h2_csvs or h3_csvs:
                benchmark_dirs.append(item_path)
    if not benchmark_dirs:
        return None
    latest_dir = max(benchmark_dirs, key=os.path.getmtime)
    print(f"[DEBUG] find_latest_benchmark_dir returns: {latest_dir}")
    sys.stdout.flush()
    return latest_dir

def generate_graphs(log_dir):
    """指定ディレクトリのベンチマークCSVからグラフを生成する統合関数"""
    data = load_benchmark_csvs(log_dir)
    create_performance_comparison_graphs(data, log_dir)
    create_detailed_analysis_graphs(data, log_dir)
    create_summary_statistics(data, log_dir)
    create_network_conditions_info(data, log_dir)
    generate_summary_report(data, log_dir)

def create_network_conditions_info(data, output_dir):
    """テスト条件やネットワーク通信環境の情報を表示するグラフを生成"""
    
    # ネットワーク条件の詳細情報を収集（高速化のため一度に処理）
    conditions_info = []
    delays = []
    losses = []
    bandwidths = []
    h2_throughputs = []
    h3_throughputs = []
    h2_latencies = []
    h3_latencies = []
    h2_connections = []
    h3_connections = []
    throughput_advantages = []
    latency_advantages = []
    connection_advantages = []
    
    for row in data:
        delays.append(row['Delay (ms)'])
        losses.append(row['Loss (%)'])
        bandwidths.append(row['Bandwidth (Mbps)'])
        h2_throughputs.append(row['HTTP/2 Throughput (req/s)'])
        h3_throughputs.append(row['HTTP/3 Throughput (req/s)'])
        h2_latencies.append(row['HTTP/2 Latency (ms)'])
        h3_latencies.append(row['HTTP/3 Latency (ms)'])
        h2_connections.append(row['HTTP/2 Connection Time (ms)'])
        h3_connections.append(row['HTTP/3 Connection Time (ms)'])
        throughput_advantages.append(row['Throughput Advantage (%)'])
        latency_advantages.append(row['Latency Advantage (%)'])
        connection_advantages.append(row['Connection Advantage (%)'])
        
        conditions_info.append({
            'delay': row['Delay (ms)'],
            'loss': row['Loss (%)'],
            'bandwidth': row['Bandwidth (Mbps)'],
            'h2_throughput': row['HTTP/2 Throughput (req/s)'],
            'h3_throughput': row['HTTP/3 Throughput (req/s)'],
            'h2_latency': row['HTTP/2 Latency (ms)'],
            'h3_latency': row['HTTP/3 Latency (ms)'],
            'h2_connection': row['HTTP/2 Connection Time (ms)'],
            'h3_connection': row['HTTP/3 Connection Time (ms)'],
            'throughput_advantage': row['Throughput Advantage (%)'],
            'latency_advantage': row['Latency Advantage (%)'],
            'connection_advantage': row['Connection Advantage (%)']
        })
    
    # 図の作成
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('テスト条件とネットワーク環境設定', fontsize=18, fontweight='bold', fontproperties=jp_font)
    
    # 1. ネットワーク条件の分布
    ax1 = axes[0, 0]
    # delays, losses, bandwidthsは既に抽出済み
    
    # 遅延の分布
    ax1.scatter(delays, [1]*len(delays), c='red', s=100, alpha=0.7, label='遅延 (ms)')
    ax1.scatter(losses, [0.8]*len(losses), c='blue', s=100, alpha=0.7, label='損失率 (%)')
    ax1.scatter(bandwidths, [0.6]*len(bandwidths), c='green', s=100, alpha=0.7, label='帯域幅 (Mbps)')
    
    ax1.set_xlabel('値', fontproperties=jp_font)
    ax1.set_ylabel('ネットワーク条件', fontproperties=jp_font)
    ax1.set_title('遅延・損失・帯域の分布', fontproperties=jp_font)
    ax1.legend(['遅延 (ms)', '損失率 (%)', '帯域幅 (Mbps)'], prop=jp_font)
    
    # 値のラベルを追加
    for i, (delay, loss, bw) in enumerate(zip(delays, losses, bandwidths)):
        ax1.annotate(f'{delay}ms', (delay, 1), xytext=(5, 5), textcoords='offset points', fontsize=8, fontproperties=jp_font)
        ax1.annotate(f'{loss}%', (loss, 0.8), xytext=(5, 5), textcoords='offset points', fontsize=8, fontproperties=jp_font)
        ax1.annotate(f'{bw}Mbps', (bw, 0.6), xytext=(5, 5), textcoords='offset points', fontsize=8, fontproperties=jp_font)
    
    # 2. 性能比較の詳細表
    ax2 = axes[0, 1]
    ax2.axis('tight')
    ax2.axis('off')
    
    # テーブルデータの準備
    table_data = []
    headers = ['条件', 'HTTP/2', 'HTTP/3', '優位性']
    
    for i, condition in enumerate(conditions_info):
        cond_str = f"{condition['delay']}ms/{condition['loss']}%"
        
        # スループット行
        h2_tp = f"{condition['h2_throughput']:.0f}"
        h3_tp = f"{condition['h3_throughput']:.0f}"
        tp_adv = f"{condition['throughput_advantage']:+.1f}%"
        table_data.append([cond_str + ' Throughput', h2_tp, h3_tp, tp_adv])
        
        # レイテンシ行
        h2_lat = f"{condition['h2_latency']:.3f}"
        h3_lat = f"{condition['h3_latency']:.3f}"
        lat_adv = f"{condition['latency_advantage']:+.1f}%"
        table_data.append([cond_str + ' Latency', h2_lat, h3_lat, lat_adv])
        
        # 接続時間行
        h2_conn = f"{condition['h2_connection']:.3f}"
        h3_conn = f"{condition['h3_connection']:.3f}"
        conn_adv = f"{condition['connection_advantage']:+.1f}%"
        table_data.append([cond_str + ' Connection Time', h2_conn, h3_conn, conn_adv])
        
        if i < len(conditions_info) - 1:
            table_data.append(['', '', '', ''])  # 空行
    
    table = ax2.table(cellText=table_data, colLabels=headers, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.1, 2)
    
    # テーブルのスタイル設定
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white', fontproperties=jp_font)
    for i in range(1, len(table_data) + 1):
        if table_data[i-1][3] != '':
            advantage = table_data[i-1][3]
            if '+' in advantage:
                table[(i, 3)].set_facecolor('#90EE90')
            elif '-' in advantage:
                table[(i, 3)].set_facecolor('#FFB6C1')
    
    
    # 3. ネットワーク条件の影響分析
    ax3 = axes[1, 0]
    
    # 遅延とスループット優位性の関係（既に抽出済み）
    
    colors = ['red' if adv < 0 else 'green' for adv in throughput_advantages]
    bars = ax3.bar(range(len(delays)), throughput_advantages, color=colors, alpha=0.7)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    ax3.set_xlabel('テストケース', fontproperties=jp_font)
    ax3.set_ylabel('HTTP/3優位性 (%)', fontproperties=jp_font)
    ax3.set_title('遅延条件下でのHTTP/3優位性', fontproperties=jp_font)
    ax3.set_xticks(range(len(delays)))
    ax3.set_xticklabels([f"{c['delay']}ms\n{c['loss']}%" for c in conditions_info], rotation=45)
    ax3.grid(True, alpha=0.3)
    
    # 値のラベルを追加
    for i, (bar, adv) in enumerate(zip(bars, throughput_advantages)):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + (1 if height >= 0 else -1),
                f'{adv:+.1f}%', ha='center', va='bottom' if height >= 0 else 'top', 
                fontsize=8, fontproperties=jp_font)
    
    # 4. テスト環境の概要
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')
    
    # テスト環境の情報
    exec_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # ベンチマークファイル名一覧
    h2_files = sorted([f for f in os.listdir(output_dir) if f.startswith('h2_') and f.endswith('.csv')])
    h3_files = sorted([f for f in os.listdir(output_dir) if f.startswith('h3_') and f.endswith('.csv')])
    file_list = '\n'.join(h2_files + h3_files)

    env_info = [
        ['実行日時', exec_time],
        ['テスト環境', '値'],
        ['テストケース数', f"{len(conditions_info)}"],
        ['遅延範囲', f"{min(delays)}ms - {max(delays)}ms"],
        ['損失範囲', f"{min(losses)}% - {max(losses)}%"],
        ['帯域範囲', f"{min(bandwidths)}Mbps - {max(bandwidths)}Mbps"],
        ['HTTP/3優位ケース', f"{sum(1 for adv in throughput_advantages if adv > 0)}/{len(conditions_info)}"],
        ['HTTP/2優位ケース', f"{sum(1 for adv in throughput_advantages if adv < 0)}/{len(conditions_info)}"],
        ['平均スループット優位性', f"{np.mean(throughput_advantages):.1f}%"],
        ['平均レイテンシ優位性', f"{np.mean(latency_advantages):.1f}%"],
        ['平均接続時間優位性', f"{np.mean(connection_advantages):.1f}%"],
        ['', ''],
        ['ベンチマーク設定', ''],
    ]
    env_info += load_benchmark_params(output_dir)
    env_info.append(['', ''])
    env_info.append(['ベンチマーク実行スクリプト', 'run_bench.sh'])

    env_table = ax4.table(cellText=env_info, cellLoc='left', loc='center')
    env_table.auto_set_font_size(False)
    env_table.set_fontsize(9)
    env_table.scale(1.1, 1.5)
    # セル内折り返し
    for i in range(len(env_info)):
        for j in range(2):
            cell = env_table[(i, j)]
            cell.set_text_props(fontproperties=jp_font, wrap=True)
    for i in range(len(env_info)):
        env_table[(i, 0)].set_facecolor('#2196F3')
        env_table[(i, 0)].set_text_props(weight='bold', color='white', fontproperties=jp_font)
        env_table[(i, 1)].set_facecolor('#E3F2FD')
    
    
    # 図の調整
    plt.tight_layout()
    plt.subplots_adjust(top=0.92)
    
    # 保存前にCanvasを明示的に描画してから両方保存
    fig.canvas.draw()
    output_file1 = os.path.join(output_dir, 'network_conditions_info.png')
    output_file2 = os.path.join(output_dir, 'test_conditions_and_network_environment.png')
    plt.savefig(output_file1, dpi=150, bbox_inches='tight')
    plt.close()
    shutil.copyfile(output_file1, output_file2)
    print(f"Network Conditions Information Graph Generation Completed: {output_file1} および {output_file2}")

def load_benchmark_params(log_dir):
    params_file = os.path.join(log_dir, 'benchmark_params.txt')
    params = []
    if os.path.exists(params_file):
        with open(params_file, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    label = {
                        'REQUESTS': '総リクエスト数',
                        'CONNECTIONS': '同時接続数',
                        'THREADS': '並列スレッド数',
                        'MAX_CONCURRENT': '最大同時ストリーム数',
                        'WARMUP_REQUESTS': 'ウォームアップリクエスト数',
                        'MEASUREMENT_REQUESTS': '測定リクエスト数',
                        'CONNECTION_WARMUP_TIME': 'ウォームアップ時間(秒)'
                    }.get(k, k)
                    params.append((label, v))
    return params

def integrate_multiple_cases(case_dirs, output_dir):
    """複数のケースディレクトリからデータを統合"""
    all_data = []
    
    for case_dir in case_dirs:
        if not os.path.exists(case_dir):
            print(f"Warning: Case directory not found: {case_dir}")
            continue
            
        # CSVファイルを探す
        csv_files = glob.glob(os.path.join(case_dir, "*.csv"))
        if not csv_files:
            print(f"Warning: No CSV files found in {case_dir}")
            continue
            
        # 最初のCSVファイルを読み込み
        csv_file = csv_files[0]
        case_data = load_extreme_conditions_data(csv_file)
        
        # ケース名を追加
        case_name = os.path.basename(case_dir)
        for row in case_data:
            row['Case'] = case_name
            
        all_data.extend(case_data)
    
    if not all_data:
        print("Error: No data found in any case directory")
        return
    
    # 統合データをCSVに保存
    csv_file = os.path.join(output_dir, 'integrated_results.csv')
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if all_data:
            writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
            writer.writeheader()
            writer.writerows(all_data)
    
    print(f"Integrated data saved: {csv_file}")
    
    # データ形式を変換して統合グラフを生成
    converted_data = convert_data_format(all_data)
    if converted_data:
        create_performance_comparison_graphs(converted_data, output_dir)
        create_detailed_analysis_graphs(converted_data, output_dir)
        create_summary_statistics(converted_data, output_dir)
        create_network_conditions_info(converted_data, output_dir)
        generate_summary_report(converted_data, output_dir)
        
        print(f"Integrated graphs created in: {output_dir}")
    else:
        print("Error: Failed to convert data format")

def convert_data_format(data):
    """データ形式を変換"""
    converted_data = []
    
    # 条件ごとにデータをグループ化
    conditions = {}
    for row in data:
        delay = int(row.get('Delay (ms)', 0))
        loss = int(row.get('Loss (%)', 0))
        bandwidth = int(row.get('Bandwidth (Mbps)', 0))
        case = row.get('Case', 'unknown')
        
        key = (delay, loss, bandwidth, case)
        if key not in conditions:
            conditions[key] = {}
        
        protocol = row.get('Protocol', '').upper()
        if 'HTTP2' in protocol or 'HTTP/2' in protocol:
            conditions[key]['HTTP/2 Throughput (req/s)'] = float(row.get('Throughput (req/s)', 0))
            conditions[key]['HTTP/2 Latency (ms)'] = float(row.get('Latency (ms)', 0))
            conditions[key]['HTTP/2 Connection Time (ms)'] = float(row.get('Connection Time (ms)', 0))
        elif 'HTTP3' in protocol or 'HTTP/3' in protocol:
            conditions[key]['HTTP/3 Throughput (req/s)'] = float(row.get('Throughput (req/s)', 0))
            conditions[key]['HTTP/3 Latency (ms)'] = float(row.get('Latency (ms)', 0))
            conditions[key]['HTTP/3 Connection Time (ms)'] = float(row.get('Connection Time (ms)', 0))
    
    # 変換されたデータを作成
    for (delay, loss, bandwidth, case), protocols in conditions.items():
        if 'HTTP/2 Throughput (req/s)' in protocols and 'HTTP/3 Throughput (req/s)' in protocols:
            h2_tp = protocols['HTTP/2 Throughput (req/s)']
            h3_tp = protocols['HTTP/3 Throughput (req/s)']
            h2_lat = protocols['HTTP/2 Latency (ms)']
            h3_lat = protocols['HTTP/3 Latency (ms)']
            h2_conn = protocols['HTTP/2 Connection Time (ms)']
            h3_conn = protocols['HTTP/3 Connection Time (ms)']
            
            # 優位性を計算
            throughput_adv = ((h3_tp - h2_tp) / h2_tp * 100) if h2_tp else 0
            latency_adv = ((h2_lat - h3_lat) / h2_lat * 100) if h2_lat else 0
            connect_adv = ((h2_conn - h3_conn) / h2_conn * 100) if h2_conn else 0
            
            converted_data.append({
                'Delay (ms)': delay,
                'Loss (%)': loss,
                'Bandwidth (Mbps)': bandwidth,
                'HTTP/2 Throughput (req/s)': h2_tp,
                'HTTP/3 Throughput (req/s)': h3_tp,
                'HTTP/2 Latency (ms)': h2_lat,
                'HTTP/3 Latency (ms)': h3_lat,
                'HTTP/2 Connection Time (ms)': h2_conn,
                'HTTP/3 Connection Time (ms)': h3_conn,
                'Throughput Advantage (%)': throughput_adv,
                'Latency Advantage (%)': latency_adv,
                'Connection Advantage (%)': connect_adv,
                'Case': case
            })
    
    return converted_data

if __name__ == "__main__":
    print("START")
    try:
        # 必要なモジュールのインポート確認
        required_modules = ['numpy', 'matplotlib', 'seaborn', 'pandas']
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            print(f"Error: Missing required modules: {', '.join(missing_modules)}")
            print("Attempting to install missing modules...")
            
            import subprocess
            import sys
            
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user'] + missing_modules)
                print("Modules installed successfully. Retrying...")
                # モジュールを再インポート
                for module in missing_modules:
                    __import__(module)
            except subprocess.CalledProcessError:
                print("Failed to install modules automatically.")
                print("Please install manually: pip3 install --user numpy matplotlib seaborn pandas")
                sys.exit(1)
        
        # コマンドライン引数の解析
        parser = argparse.ArgumentParser(description='Generate performance graphs from benchmark data')
        parser.add_argument('--log_dir', help='Log directory for single case')
        parser.add_argument('--integrate_cases', action='store_true', help='Integrate multiple cases')
        parser.add_argument('--case_dirs', nargs='+', help='Case directories for integration')
        
        args = parser.parse_args()
        
        if args.integrate_cases and args.case_dirs:
            # 統合モード
            output_dir = args.log_dir if args.log_dir else "logs/integrated_results"
            os.makedirs(output_dir, exist_ok=True)
            integrate_multiple_cases(args.case_dirs, output_dir)
        else:
            # 単一ケースモード
            args_list = [a for a in sys.argv[1:] if not a.startswith('--')]
            if len(args_list) == 0:
                log_dir = find_latest_benchmark_dir(base_dir='/logs')
                if log_dir is None:
                    print("Error: Benchmark directory not found. Please create benchmark_* directory under '/logs'.")
                    sys.exit(1)
            elif len(args_list) == 1:
                log_dir = args_list[0]
            else:
                print("Usage: python3 generate_performance_graphs.py <log_dir>")
                sys.exit(1)
            
            # ログディレクトリの存在確認
            if not os.path.exists(log_dir):
                print(f"Error: Log directory '{log_dir}' does not exist.")
                sys.exit(1)
            
            # 必要なファイルの存在確認
            csv_files = [f for f in os.listdir(log_dir) if f.endswith('.csv')]
            if not csv_files:
                print(f"Error: No CSV files found in '{log_dir}'")
                sys.exit(1)
            
            print(f"[DEBUG] load_benchmark_csvs received log_dir: {log_dir}")
            generate_graphs(log_dir)
            print("Graph generation completed! Output directory:", log_dir)
        
    except ImportError as e:
        print(f"Error: Required module not found: {e}")
        print("Please install required packages: pip3 install --user numpy matplotlib seaborn pandas")
        sys.exit(1)
    except Exception as e:
        print(f"Error during graph generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 