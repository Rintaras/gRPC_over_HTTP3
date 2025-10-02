#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import matplotlib.font_manager as fm

sns.set_style("whitegrid")

plt.rcParams['font.family'] = 'sans-serif'
available_fonts = [f.name for f in fm.fontManager.ttflist]
japanese_fonts = ['Hiragino Sans', 'Hiragino Kaku Gothic Pro', 'Yu Gothic', 'Meiryo', 'MS Gothic', 'AppleGothic']
selected_font = None
for font in japanese_fonts:
    if font in available_fonts:
        selected_font = font
        break

if selected_font:
    plt.rcParams['font.sans-serif'] = [selected_font, 'DejaVu Sans']
else:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.figsize'] = (10, 7)
plt.rcParams['font.size'] = 12

import os

csv_file = os.environ.get('BENCHMARK_CSV', 'benchmark_results_20251001_171222.csv')
output_dir = os.environ.get('BENCHMARK_OUTPUT_DIR', '.')

df = pd.read_csv(csv_file)

df = df[df['success'] == 1].copy()
df['latency_ms'] = df['latency'].str.replace('ms', '').astype(int)

latencies = sorted(df['latency_ms'].unique())
colors = {'HTTP/2': '#2E86AB', 'HTTP/3': '#A23B72'}

fig, ax = plt.subplots(figsize=(10, 7))

for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    stds = [data[data['latency_ms'] == lat]['time_total'].std() for lat in latencies]
    ax.plot(latencies, stds, marker='o', linewidth=3, markersize=10,
            label=protocol, color=color)

ax.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
ax.set_ylabel('標準偏差 (秒)', fontsize=14, fontweight='bold')
ax.set_title('標準偏差の比較（安定性指標）\n低い値ほど安定', fontsize=16, fontweight='bold', pad=20)
ax.legend(fontsize=13, loc='best')
ax.grid(True, alpha=0.3)

for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    stds = [data[data['latency_ms'] == lat]['time_total'].std() for lat in latencies]
    for i, (lat, std) in enumerate(zip(latencies, stds)):
        ax.annotate(f'{std:.3f}', 
                   xy=(lat, std), 
                   xytext=(5, 5), 
                   textcoords='offset points',
                   fontsize=10,
                   color=color,
                   fontweight='bold')

ax.set_xticks(latencies)
ax.set_xticklabels([f'{lat}ms' for lat in latencies])

plt.tight_layout()
output_file = os.path.join(output_dir, 'stability_comparison.png')
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"グラフを保存しました: {output_file}")
plt.close()

print("\n=== 標準偏差サマリー ===")
for lat in latencies:
    http2_std = df[(df['protocol'] == 'HTTP/2') & (df['latency_ms'] == lat)]['time_total'].std()
    http3_std = df[(df['protocol'] == 'HTTP/3') & (df['latency_ms'] == lat)]['time_total'].std()
    ratio = http3_std / http2_std
    winner = "HTTP/2" if http2_std < http3_std else "HTTP/3"
    print(f"{lat}ms: HTTP/2={http2_std:.4f}s, HTTP/3={http3_std:.4f}s, 比={ratio:.2f}倍, 安定性: {winner}")

