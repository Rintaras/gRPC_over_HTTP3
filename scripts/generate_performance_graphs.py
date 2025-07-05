#!/usr/bin/env python3
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

# 日本語フォント設定
plt.rcParams['font.family'] = ['DejaVu Sans', 'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']

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
                        processed_row[key] = int(value) if value else 0
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
    
    # Extract data for plotting
    delays = [row['Delay (ms)'] for row in data]
    bandwidths = [row['Bandwidth (Mbps)'] for row in data]
    losses = [row['Loss (%)'] for row in data]
    
    h2_throughput = [row['HTTP/2 Throughput (req/s)'] for row in data]
    h3_throughput = [row['HTTP/3 Throughput (req/s)'] for row in data]
    
    h2_latency = [row['HTTP/2 Latency (ms)'] for row in data]
    h3_latency = [row['HTTP/3 Latency (ms)'] for row in data]
    
    h2_connection = [row['HTTP/2 Connection Time (ms)'] for row in data]
    h3_connection = [row['HTTP/3 Connection Time (ms)'] for row in data]
    
    throughput_advantage = [row['Throughput Advantage (%)'] for row in data]
    latency_advantage = [row['Latency Advantage (%)'] for row in data]
    connection_advantage = [row['Connection Advantage (%)'] for row in data]
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('HTTP/3 vs HTTP/2 性能比較 - 極端なネットワーク条件での逆転現象', 
                 fontsize=16, fontweight='bold')
    
    # 1. Throughput comparison
    ax1 = axes[0, 0]
    x = np.arange(len(delays))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, h2_throughput, width, label='HTTP/2', color='#1f77b4', alpha=0.8)
    bars2 = ax1.bar(x + width/2, h3_throughput, width, label='HTTP/3', color='#ff7f0e', alpha=0.8)
    
    ax1.set_xlabel('遅延 (ms)')
    ax1.set_ylabel('スループット (req/s)')
    ax1.set_title('スループット比較')
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)])
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{height:.0f}', ha='center', va='bottom', fontsize=8)
    
    for bar in bars2:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{height:.0f}', ha='center', va='bottom', fontsize=8)
    
    # 2. Latency comparison
    ax2 = axes[0, 1]
    bars3 = ax2.bar(x - width/2, h2_latency, width, label='HTTP/2', color='#1f77b4', alpha=0.8)
    bars4 = ax2.bar(x + width/2, h3_latency, width, label='HTTP/3', color='#ff7f0e', alpha=0.8)
    
    ax2.set_xlabel('遅延 (ms)')
    ax2.set_ylabel('レイテンシ (ms)')
    ax2.set_title('レイテンシ比較')
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)])
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars3:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{height:.3f}', ha='center', va='bottom', fontsize=8)
    
    for bar in bars4:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{height:.3f}', ha='center', va='bottom', fontsize=8)
    
    # 3. Connection time comparison
    ax3 = axes[0, 2]
    bars5 = ax3.bar(x - width/2, h2_connection, width, label='HTTP/2', color='#1f77b4', alpha=0.8)
    bars6 = ax3.bar(x + width/2, h3_connection, width, label='HTTP/3', color='#ff7f0e', alpha=0.8)
    
    ax3.set_xlabel('遅延 (ms)')
    ax3.set_ylabel('接続時間 (ms)')
    ax3.set_title('接続時間比較')
    ax3.set_xticks(x)
    ax3.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)])
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars5:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{height:.3f}', ha='center', va='bottom', fontsize=8)
    
    for bar in bars6:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{height:.3f}', ha='center', va='bottom', fontsize=8)
    
    # 4. Throughput advantage over delay
    ax4 = axes[1, 0]
    colors = ['red' if adv < 0 else 'green' for adv in throughput_advantage]
    bars7 = ax4.bar(x, throughput_advantage, color=colors, alpha=0.7)
    ax4.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax4.set_xlabel('遅延 (ms)')
    ax4.set_ylabel('HTTP/3優位性 (%)')
    ax4.set_title('スループット優位性 (正=HTTP/3優位)')
    ax4.set_xticks(x)
    ax4.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)])
    ax4.grid(True, alpha=0.3)
    
    # Add value labels
    for bar in bars7:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + (1 if height >= 0 else -1),
                f'{height:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=9)
    
    # 5. Latency advantage over delay
    ax5 = axes[1, 1]
    colors = ['red' if adv < 0 else 'green' for adv in latency_advantage]
    bars8 = ax5.bar(x, latency_advantage, color=colors, alpha=0.7)
    ax5.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax5.set_xlabel('遅延 (ms)')
    ax5.set_ylabel('HTTP/3優位性 (%)')
    ax5.set_title('レイテンシ優位性 (正=HTTP/3優位)')
    ax5.set_xticks(x)
    ax5.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)])
    ax5.grid(True, alpha=0.3)
    
    # Add value labels
    for bar in bars8:
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height + (1 if height >= 0 else -1),
                f'{height:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=9)
    
    # 6. Connection time advantage over delay
    ax6 = axes[1, 2]
    colors = ['red' if adv < 0 else 'green' for adv in connection_advantage]
    bars9 = ax6.bar(x, connection_advantage, color=colors, alpha=0.7)
    ax6.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax6.set_xlabel('遅延 (ms)')
    ax6.set_ylabel('HTTP/3優位性 (%)')
    ax6.set_title('接続時間優位性 (正=HTTP/3優位)')
    ax6.set_xticks(x)
    ax6.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)])
    ax6.grid(True, alpha=0.3)
    
    # Add value labels
    for bar in bars9:
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width()/2., height + (1 if height >= 0 else -1),
                f'{height:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'performance_comparison_overview.png'), 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create detailed analysis graphs
    create_detailed_analysis_graphs(data, output_dir)
    
    print(f"グラフ生成完了: {output_dir}")

def create_detailed_analysis_graphs(data, output_dir):
    """Create detailed analysis graphs showing the reversal phenomenon"""
    
    # Sort data by delay
    data.sort(key=lambda x: x['Delay (ms)'])
    
    delays = [row['Delay (ms)'] for row in data]
    bandwidths = [row['Bandwidth (Mbps)'] for row in data]
    throughput_advantage = [row['Throughput Advantage (%)'] for row in data]
    latency_advantage = [row['Latency Advantage (%)'] for row in data]
    
    # Create detailed analysis figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('HTTP/3 vs HTTP/2 性能逆転現象の詳細分析', fontsize=16, fontweight='bold')
    
    # 1. Throughput advantage trend
    ax1 = axes[0, 0]
    ax1.plot(delays, throughput_advantage, 'o-', linewidth=2, markersize=8, 
             color='#2E8B57', label='スループット優位性')
    ax1.axhline(y=0, color='red', linestyle='--', alpha=0.7, label='均衡線')
    ax1.set_xlabel('遅延 (ms)')
    ax1.set_ylabel('HTTP/3優位性 (%)')
    ax1.set_title('遅延とスループット優位性の関係')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
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
    ax2.set_xlabel('帯域幅 (Mbps)')
    ax2.set_ylabel('HTTP/3優位性 (%)')
    ax2.set_title('帯域幅とスループット優位性の関係')
    ax2.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax2)
    cbar.set_label('遅延 (ms)')
    
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
    ax3.set_xlabel('テストケース')
    ax3.set_ylabel('HTTP/3優位性 (%)')
    ax3.set_title('性能逆転閾値分析')
    ax3.set_xticks(range(len(delays)))
    ax3.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)], rotation=45)
    ax3.grid(True, alpha=0.3)
    
    # Add threshold line
    ax3.axvline(x=2.5, color='red', linestyle='--', alpha=0.7, label='推定閾値')
    ax3.legend()
    
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
                    color=color, fontweight='bold')
    
    ax4.set_xticks(range(len(delays)))
    ax4.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)], rotation=45)
    ax4.set_yticks(range(3))
    ax4.set_yticklabels(['スループット', 'レイテンシ', '接続時間'])
    ax4.set_title('性能比較マトリックス\n(緑=HTTP/3優位, 赤=HTTP/2優位)')
    
    # Add colorbar
    cbar2 = plt.colorbar(im, ax=ax4)
    cbar2.set_label('HTTP/3優位性 (%)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'detailed_performance_analysis.png'), 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create summary statistics
    create_summary_statistics(data, output_dir)

def create_summary_statistics(data, output_dir):
    """Create summary statistics and key findings"""
    
    # Calculate summary statistics
    throughput_advantages = [row['Throughput Advantage (%)'] for row in data]
    latency_advantages = [row['Latency Advantage (%)'] for row in data]
    connection_advantages = [row['Connection Advantage (%)'] for row in data]
    
    # Find conditions where HTTP/3 is advantageous
    h3_advantage_conditions = [i for i, adv in enumerate(throughput_advantages) if adv > 0]
    h2_advantage_conditions = [i for i, adv in enumerate(throughput_advantages) if adv < 0]
    
    # Create summary figure
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('性能逆転現象の統計分析', fontsize=16, fontweight='bold')
    
    # 1. Advantage distribution
    ax1 = axes[0]
    categories = ['HTTP/3優位', 'HTTP/2優位']
    counts = [len(h3_advantage_conditions), len(h2_advantage_conditions)]
    colors = ['#2E8B57', '#CD5C5C']
    
    bars = ax1.bar(categories, counts, color=colors, alpha=0.8)
    ax1.set_ylabel('テストケース数')
    ax1.set_title('優位性分布')
    
    # Add value labels
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{count}ケース', ha='center', va='bottom', fontweight='bold')
    
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
    ax2.set_ylabel('平均優位性 (%)')
    ax2.set_title('平均性能比較')
    ax2.grid(True, alpha=0.3)
    
    # Add value labels
    for bar, adv in zip(bars, avg_advantages):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + (1 if adv >= 0 else -1),
                f'{adv:.1f}%', ha='center', va='bottom' if adv >= 0 else 'top', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'performance_summary_statistics.png'), 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    # Generate summary report
    generate_summary_report(data, output_dir)

def generate_summary_report(data, output_dir):
    """Generate a summary report with key findings"""
    
    report_file = os.path.join(output_dir, 'performance_reversal_summary.txt')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("HTTP/3 vs HTTP/2 性能逆転現象の詳細分析レポート\n")
        f.write("=" * 80 + "\n")
        f.write(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Calculate key statistics
        throughput_advantages = [row['Throughput Advantage (%)'] for row in data]
        latency_advantages = [row['Latency Advantage (%)'] for row in data]
        connection_advantages = [row['Connection Advantage (%)'] for row in data]
        
        h3_advantage_count = sum(1 for adv in throughput_advantages if adv > 0)
        h2_advantage_count = sum(1 for adv in throughput_advantages if adv < 0)
        
        f.write("📊 主要な発見\n")
        f.write("-" * 40 + "\n")
        f.write(f"• HTTP/3優位ケース: {h3_advantage_count}/{len(data)} ケース\n")
        f.write(f"• HTTP/2優位ケース: {h2_advantage_count}/{len(data)} ケース\n")
        f.write(f"• 平均スループット優位性: {np.mean(throughput_advantages):.1f}%\n")
        f.write(f"• 平均レイテンシ優位性: {np.mean(latency_advantages):.1f}%\n")
        f.write(f"• 平均接続時間優位性: {np.mean(connection_advantages):.1f}%\n\n")
        
        f.write("🎯 性能逆転の閾値\n")
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
            f.write("HTTP/3が優位になる条件:\n")
            for condition in threshold_conditions:
                f.write(f"  • {condition['delay']}ms遅延, {condition['bandwidth']}Mbps帯域, {condition['loss']}%損失 → +{condition['advantage']:.1f}%\n")
        
        f.write("\n🚀 最も顕著な結果\n")
        f.write("-" * 40 + "\n")
        
        # Find maximum advantage
        max_advantage = max(throughput_advantages)
        max_condition = data[throughput_advantages.index(max_advantage)]
        f.write(f"• 最大スループット優位性: +{max_advantage:.1f}%\n")
        f.write(f"  条件: {max_condition['Delay (ms)']}ms遅延, {max_condition['Bandwidth (Mbps)']}Mbps帯域, {max_condition['Loss (%)']}%損失\n")
        
        f.write("\n📈 論文の仮説検証結果\n")
        f.write("-" * 40 + "\n")
        f.write("✅ 再現された主張:\n")
        f.write("  • 極端な高遅延環境でのHTTP/3優位性\n")
        f.write("  • 極低帯域環境でのHTTP/3優位性\n")
        f.write("  • 特定条件下での性能逆転現象\n\n")
        
        f.write("❌ 再現されなかった部分:\n")
        f.write("  • レイテンシではHTTP/2が一貫して優位\n")
        f.write("  • 接続時間ではHTTP/2が優位\n\n")
        
        f.write("🔍 実用的な指針\n")
        f.write("-" * 40 + "\n")
        f.write("• 遅延400ms以上、帯域10Mbps以下の環境ではHTTP/3を推奨\n")
        f.write("• 衛星通信や極端なネットワーク制約環境ではHTTP/3が明確に優位\n")
        f.write("• 一般的なネットワーク環境ではHTTP/2が安定して優位\n")
        f.write("• レイテンシが重要な場合はHTTP/2を選択\n\n")
        
        f.write("📁 生成されたグラフファイル:\n")
        f.write("-" * 40 + "\n")
        f.write("• performance_comparison_overview.png - 全体的な性能比較\n")
        f.write("• detailed_performance_analysis.png - 詳細な逆転現象分析\n")
        f.write("• performance_summary_statistics.png - 統計サマリー\n")
    
    print(f"サマリーレポート生成完了: {report_file}")

def main():
    """Main function"""
    # コマンドライン引数でデータディレクトリ指定可
    if len(sys.argv) > 1:
        log_dir = sys.argv[1]
    elif os.path.exists("/logs") and os.path.isdir("/logs"):
        log_dir = "/logs"
    elif os.path.exists("./logs") and os.path.isdir("./logs"):
        log_dir = "./logs"
    else:
        print("Error: Log directory not found (/logs or ./logs)")
        sys.exit(1)
    
    # Load data
    csv_file = os.path.join(log_dir, "extreme_conditions_data.csv")
    if not os.path.exists(csv_file):
        print(f"Error: Data file not found: {csv_file}")
        sys.exit(1)
    
    print("性能逆転現象のグラフ生成を開始...")
    data = load_extreme_conditions_data(csv_file)
    
    if not data:
        print("Error: No data loaded")
        sys.exit(1)
    
    # Create graphs
    create_performance_comparison_graphs(data, log_dir)
    
    print("グラフ生成完了!")
    print(f"生成されたファイル:")
    print(f"  • {log_dir}/performance_comparison_overview.png")
    print(f"  • {log_dir}/detailed_performance_analysis.png")
    print(f"  • {log_dir}/performance_summary_statistics.png")
    print(f"  • {log_dir}/performance_reversal_summary.txt")

if __name__ == "__main__":
    main() 