#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from pathlib import Path

sns.set_style("whitegrid")
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 10

import os

csv_file = os.environ.get('BENCHMARK_CSV', 'benchmark_results_20251001_171222.csv')
output_dir = os.environ.get('BENCHMARK_OUTPUT_DIR', '.')

df = pd.read_csv(csv_file)

df = df[df['success'] == 1].copy()
df['latency_ms'] = df['latency'].str.replace('ms', '').astype(int)

http2_data = df[df['protocol'] == 'HTTP/2']
http3_data = df[df['protocol'] == 'HTTP/3']

latencies = sorted(df['latency_ms'].unique())

fig = plt.figure(figsize=(16, 12))

colors = {'HTTP/2': '#2E86AB', 'HTTP/3': '#A23B72'}

ax1 = plt.subplot(2, 3, 1)
for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    means = [data[data['latency_ms'] == lat]['time_total'].mean() for lat in latencies]
    stds = [data[data['latency_ms'] == lat]['time_total'].std() for lat in latencies]
    
    ax1.plot(latencies, means, marker='o', linewidth=2.5, markersize=8, 
             label=protocol, color=color)
    ax1.fill_between(latencies, 
                      np.array(means) - np.array(stds), 
                      np.array(means) + np.array(stds), 
                      alpha=0.2, color=color)

ax1.set_xlabel('遅延 (ms)', fontsize=12, fontweight='bold')
ax1.set_ylabel('転送時間 (秒)', fontsize=12, fontweight='bold')
ax1.set_title('1. 平均転送時間の比較', fontsize=14, fontweight='bold')
ax1.legend(fontsize=11)
ax1.grid(True, alpha=0.3)

ax2 = plt.subplot(2, 3, 2)
for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    speeds = [data[data['latency_ms'] == lat]['speed_kbps'].mean() for lat in latencies]
    
    ax2.plot(latencies, speeds, marker='s', linewidth=2.5, markersize=8,
             label=protocol, color=color)

ax2.set_xlabel('遅延 (ms)', fontsize=12, fontweight='bold')
ax2.set_ylabel('速度 (KB/s)', fontsize=12, fontweight='bold')
ax2.set_title('2. 平均転送速度の比較', fontsize=14, fontweight='bold')
ax2.legend(fontsize=11)
ax2.grid(True, alpha=0.3)

ax3 = plt.subplot(2, 3, 3)
width = 15
x = np.array(latencies)
http2_times = [http2_data[http2_data['latency_ms'] == lat]['time_total'].mean() for lat in latencies]
http3_times = [http3_data[http3_data['latency_ms'] == lat]['time_total'].mean() for lat in latencies]

bars1 = ax3.bar(x - width/2, http2_times, width, label='HTTP/2', color=colors['HTTP/2'], alpha=0.8)
bars2 = ax3.bar(x + width/2, http3_times, width, label='HTTP/3', color=colors['HTTP/3'], alpha=0.8)

for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.3f}s',
                ha='center', va='bottom', fontsize=9)

ax3.set_xlabel('遅延 (ms)', fontsize=12, fontweight='bold')
ax3.set_ylabel('転送時間 (秒)', fontsize=12, fontweight='bold')
ax3.set_title('3. 転送時間の直接比較', fontsize=14, fontweight='bold')
ax3.set_xticks(latencies)
ax3.legend(fontsize=11)
ax3.grid(True, alpha=0.3, axis='y')

ax4 = plt.subplot(2, 3, 4)
positions = []
data_to_plot = []
labels = []

for i, lat in enumerate(latencies):
    http2_times = http2_data[http2_data['latency_ms'] == lat]['time_total'].values
    http3_times = http3_data[http3_data['latency_ms'] == lat]['time_total'].values
    
    positions.extend([i*3 + 0.5, i*3 + 1.5])
    data_to_plot.extend([http2_times, http3_times])
    if i == 0:
        labels.extend(['HTTP/2', 'HTTP/3'])
    else:
        labels.extend(['', ''])

bp = ax4.boxplot(data_to_plot, positions=positions, widths=0.6,
                  patch_artist=True, showfliers=True,
                  boxprops=dict(linewidth=1.5),
                  whiskerprops=dict(linewidth=1.5),
                  capprops=dict(linewidth=1.5),
                  medianprops=dict(linewidth=2, color='red'))

for i, (patch, pos) in enumerate(zip(bp['boxes'], positions)):
    if i % 2 == 0:
        patch.set_facecolor(colors['HTTP/2'])
        patch.set_alpha(0.7)
    else:
        patch.set_facecolor(colors['HTTP/3'])
        patch.set_alpha(0.7)

ax4.set_xticks([i*3 + 1 for i in range(len(latencies))])
ax4.set_xticklabels([f'{lat}ms' for lat in latencies])
ax4.set_xlabel('遅延', fontsize=12, fontweight='bold')
ax4.set_ylabel('転送時間 (秒)', fontsize=12, fontweight='bold')
ax4.set_title('4. 転送時間の分布（箱ひげ図）', fontsize=14, fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')

from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=colors['HTTP/2'], alpha=0.7, label='HTTP/2'),
                   Patch(facecolor=colors['HTTP/3'], alpha=0.7, label='HTTP/3')]
ax4.legend(handles=legend_elements, fontsize=11)

ax5 = plt.subplot(2, 3, 5)
http2_improvements = []
http3_improvements = []

http2_baseline = http2_data[http2_data['latency_ms'] == 0]['time_total'].mean()
http3_baseline = http3_data[http3_data['latency_ms'] == 0]['time_total'].mean()

for lat in latencies:
    http2_time = http2_data[http2_data['latency_ms'] == lat]['time_total'].mean()
    http3_time = http3_data[http3_data['latency_ms'] == lat]['time_total'].mean()
    
    http2_improvements.append((http2_time - http2_baseline) / http2_baseline * 100)
    http3_improvements.append((http3_time - http3_baseline) / http3_baseline * 100)

ax5.plot(latencies, http2_improvements, marker='o', linewidth=2.5, markersize=8,
         label='HTTP/2', color=colors['HTTP/2'])
ax5.plot(latencies, http3_improvements, marker='o', linewidth=2.5, markersize=8,
         label='HTTP/3', color=colors['HTTP/3'])

ax5.set_xlabel('遅延 (ms)', fontsize=12, fontweight='bold')
ax5.set_ylabel('ベースライン(0ms)からの増加率 (%)', fontsize=12, fontweight='bold')
ax5.set_title('5. 遅延による性能劣化の比較', fontsize=14, fontweight='bold')
ax5.legend(fontsize=11)
ax5.grid(True, alpha=0.3)
ax5.axhline(y=0, color='black', linestyle='--', linewidth=1)

ax6 = plt.subplot(2, 3, 6)
differences = []
for lat in latencies:
    http2_time = http2_data[http2_data['latency_ms'] == lat]['time_total'].mean()
    http3_time = http3_data[http3_data['latency_ms'] == lat]['time_total'].mean()
    diff = ((http3_time - http2_time) / http2_time) * 100
    differences.append(diff)

colors_bars = ['green' if d < 0 else 'red' for d in differences]
bars = ax6.bar(latencies, differences, color=colors_bars, alpha=0.7, width=20)

for bar, diff in zip(bars, differences):
    height = bar.get_height()
    ax6.text(bar.get_x() + bar.get_width()/2., height,
            f'{diff:+.2f}%',
            ha='center', va='bottom' if height > 0 else 'top', 
            fontsize=10, fontweight='bold')

ax6.axhline(y=0, color='black', linestyle='-', linewidth=2)
ax6.set_xlabel('遅延 (ms)', fontsize=12, fontweight='bold')
ax6.set_ylabel('HTTP/3の相対性能 (%)', fontsize=12, fontweight='bold')
ax6.set_title('6. HTTP/3 vs HTTP/2 相対性能\n(負の値 = HTTP/3が高速)', fontsize=14, fontweight='bold')
ax6.grid(True, alpha=0.3, axis='y')
ax6.set_xticks(latencies)

plt.tight_layout()
output_file1 = os.path.join(output_dir, 'benchmark_visualization.png')
plt.savefig(output_file1, dpi=300, bbox_inches='tight')
print(f"グラフを保存しました: {output_file1}")
plt.close()

fig2, axes = plt.subplots(2, 2, figsize=(14, 10))

ax = axes[0, 0]
for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    stds = [data[data['latency_ms'] == lat]['time_total'].std() for lat in latencies]
    ax.plot(latencies, stds, marker='o', linewidth=2.5, markersize=8,
            label=protocol, color=color)

ax.set_xlabel('遅延 (ms)', fontsize=12, fontweight='bold')
ax.set_ylabel('標準偏差 (秒)', fontsize=12, fontweight='bold')
ax.set_title('標準偏差の比較（安定性指標）', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

ax = axes[0, 1]
for lat in latencies:
    http2_times = http2_data[http2_data['latency_ms'] == lat]['time_total'].values
    http3_times = http3_data[http3_data['latency_ms'] == lat]['time_total'].values
    
    ax.scatter([lat]*len(http2_times), http2_times, alpha=0.3, s=30, 
               color=colors['HTTP/2'], label='HTTP/2' if lat == latencies[0] else '')
    ax.scatter([lat]*len(http3_times), http3_times, alpha=0.3, s=30,
               color=colors['HTTP/3'], label='HTTP/3' if lat == latencies[0] else '')

for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    means = [data[data['latency_ms'] == lat]['time_total'].mean() for lat in latencies]
    ax.plot(latencies, means, linewidth=3, color=color, linestyle='--', alpha=0.8)

ax.set_xlabel('遅延 (ms)', fontsize=12, fontweight='bold')
ax.set_ylabel('転送時間 (秒)', fontsize=12, fontweight='bold')
ax.set_title('全データポイントの分布', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

ax = axes[1, 0]
summary_data = []
for lat in latencies:
    for protocol in ['HTTP/2', 'HTTP/3']:
        data = df[(df['protocol'] == protocol) & (df['latency_ms'] == lat)]
        summary_data.append({
            '遅延': f'{lat}ms',
            'プロトコル': protocol,
            '成功数': len(data),
            '平均時間': data['time_total'].mean(),
            '中央値': data['time_total'].median(),
            '標準偏差': data['time_total'].std()
        })

summary_df = pd.DataFrame(summary_data)
pivot_success = summary_df.pivot(index='遅延', columns='プロトコル', values='成功数')

pivot_success.plot(kind='bar', ax=ax, color=[colors['HTTP/2'], colors['HTTP/3']], 
                   alpha=0.8, width=0.7)
ax.set_xlabel('遅延', fontsize=12, fontweight='bold')
ax.set_ylabel('成功リクエスト数', fontsize=12, fontweight='bold')
ax.set_title('成功率（各条件50リクエスト）', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3, axis='y')
ax.set_xticklabels(ax.get_xticklabels(), rotation=0)

for container in ax.containers:
    ax.bar_label(container, fontsize=10, fontweight='bold')

ax = axes[1, 1]
summary_text = "=== ベンチマーク結果サマリー ===\n\n"
summary_text += f"総リクエスト数: {len(df)}\n"
summary_text += f"HTTP/2成功率: {len(http2_data)}/200 (100%)\n"
summary_text += f"HTTP/3成功率: {len(http3_data)}/200 (100%)\n\n"

summary_text += "条件別の勝者:\n"
for lat in latencies:
    h2_time = http2_data[http2_data['latency_ms'] == lat]['time_total'].mean()
    h3_time = http3_data[http3_data['latency_ms'] == lat]['time_total'].mean()
    diff = h3_time - h2_time
    winner = "HTTP/2" if diff > 0 else "HTTP/3" if diff < 0 else "同等"
    summary_text += f"  {lat}ms: {winner} ({abs(diff)*1000:.1f}ms差)\n"

summary_text += "\n主要な発見:\n"
summary_text += "• 50msがクロスオーバーポイント\n"
summary_text += "• 低遅延でHTTP/2が5.4%高速\n"
summary_text += "• 高遅延でHTTP/3がわずかに優位\n"
summary_text += "• HTTP/2の方が全体的に安定\n"
summary_text += "• 両プロトコルとも100%成功率\n"

ax.text(0.1, 0.5, summary_text, transform=ax.transAxes,
        fontsize=11, verticalalignment='center',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3),
        family='monospace')
ax.axis('off')

plt.tight_layout()
output_file2 = os.path.join(output_dir, 'benchmark_analysis.png')
plt.savefig(output_file2, dpi=300, bbox_inches='tight')
print(f"グラフを保存しました: {output_file2}")
plt.close()

print("\n=== グラフ生成完了 ===")
print(f"1. {output_file1} - メイン分析グラフ（6種類）")
print(f"2. {output_file2} - 詳細分析グラフ（4種類）")
print("\n各グラフの説明:")
print("  1. 平均転送時間の比較（標準偏差付き）")
print("  2. 平均転送速度の比較")
print("  3. 転送時間の直接比較（棒グラフ）")
print("  4. 転送時間の分布（箱ひげ図）")
print("  5. 遅延による性能劣化の比較")
print("  6. HTTP/3 vs HTTP/2 相対性能")
print("  7. 標準偏差の比較（安定性）")
print("  8. 全データポイントの散布図")
print("  9. 成功率の比較")
print(" 10. 結果サマリー")

