#!/usr/bin/env python3
"""
Average benchmark results from multiple executions
Combines data from 5 benchmark runs and generates averaged graphs
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
from collections import defaultdict

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

def extract_metrics_from_log(logfile):
    """ログファイルからメトリクスを抽出"""
    throughput = 0
    latency = 0
    connect = 0
    
    try:
        with open(logfile, 'r', encoding='utf-8') as f:
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

def parse_case_filename(filename):
    """ファイル名からテストケース情報を解析"""
    base = os.path.basename(filename)
    parts = base.split('_')
    
    if len(parts) >= 3:
        delay = int(parts[1].replace('ms',''))
        loss_part = parts[2]
        if 'mbps' in base:
            loss = int(loss_part.replace('pct',''))
            bw = int(parts[3].replace('mbps.csv',''))
        else:
            loss = int(loss_part.replace('pct.csv',''))
            bw = 0
        return delay, loss, bw
    return 0, 0, 0

def load_benchmark_data(log_dir):
    """ベンチマークディレクトリからデータを読み込み"""
    data = []
    
    # CSVファイルを探索
    h2_csvs = sorted(glob.glob(os.path.join(log_dir, 'h2_*.csv')))
    h3_csvs = sorted(glob.glob(os.path.join(log_dir, 'h3_*.csv')))
    
    if not h2_csvs or not h3_csvs:
        print(f"Warning: No benchmark CSV data found in {log_dir}")
        return data
    
    h2_map = {parse_case_filename(f): f for f in h2_csvs}
    h3_map = {parse_case_filename(f): f for f in h3_csvs}
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

def average_benchmark_results(log_dirs):
    """複数のベンチマーク結果を平均化"""
    print(f"平均化処理開始: {len(log_dirs)}個のディレクトリ")
    
    all_data = []
    for log_dir in log_dirs:
        print(f"読み込み中: {log_dir}")
        data = load_benchmark_data(log_dir)
        if data:
            all_data.append(data)
    
    if not all_data:
        print("Error: No valid benchmark data found")
        return None
    
    # 各テストケースのデータをグループ化
    case_groups = defaultdict(list)
    
    for data_set in all_data:
        for row in data_set:
            case_key = (row['Delay (ms)'], row['Loss (%)'], row['Bandwidth (Mbps)'])
            case_groups[case_key].append(row)
    
    # 平均値を計算
    averaged_data = []
    
    for case_key, rows in case_groups.items():
        if len(rows) < 2:  # 少なくとも2回以上の実行が必要
            print(f"Warning: Insufficient data for case {case_key}")
            continue
            
        delay, loss, bw = case_key
        
        # 平均値を計算
        avg_row = {
            'Delay (ms)': delay,
            'Loss (%)': loss,
            'Bandwidth (Mbps)': bw,
            'HTTP/2 Throughput (req/s)': np.mean([r['HTTP/2 Throughput (req/s)'] for r in rows]),
            'HTTP/3 Throughput (req/s)': np.mean([r['HTTP/3 Throughput (req/s)'] for r in rows]),
            'HTTP/2 Latency (ms)': np.mean([r['HTTP/2 Latency (ms)'] for r in rows]),
            'HTTP/3 Latency (ms)': np.mean([r['HTTP/3 Latency (ms)'] for r in rows]),
            'HTTP/2 Connection Time (ms)': np.mean([r['HTTP/2 Connection Time (ms)'] for r in rows]),
            'HTTP/3 Connection Time (ms)': np.mean([r['HTTP/3 Connection Time (ms)'] for r in rows]),
        }
        
        # 優位性を再計算
        h2_tp = avg_row['HTTP/2 Throughput (req/s)']
        h3_tp = avg_row['HTTP/3 Throughput (req/s)']
        h2_lat = avg_row['HTTP/2 Latency (ms)']
        h3_lat = avg_row['HTTP/3 Latency (ms)']
        h2_conn = avg_row['HTTP/2 Connection Time (ms)']
        h3_conn = avg_row['HTTP/3 Connection Time (ms)']
        
        avg_row['Throughput Advantage (%)'] = ((h3_tp - h2_tp) / h2_tp * 100) if h2_tp else 0
        avg_row['Latency Advantage (%)'] = ((h2_lat - h3_lat) / h2_lat * 100) if h2_lat else 0
        avg_row['Connection Advantage (%)'] = ((h2_conn - h3_conn) / h2_conn * 100) if h2_conn else 0
        
        averaged_data.append(avg_row)
    
    return averaged_data

def create_performance_comparison_overview(data, output_dir):
    """performance_comparison_overview.pngと同様のグラフを生成"""
    if not data:
        print("Error: No averaged data to plot")
        return
    
    # データを遅延でソート
    data.sort(key=lambda x: x['Delay (ms)'])
    
    # データ抽出
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
    fig.suptitle('HTTP/3 vs HTTP/2 性能比較 - 5回実行平均結果', fontsize=16, fontweight='bold', fontproperties=jp_font)
    
    # 1. Throughput comparison
    ax1 = axes[0, 0]
    x = np.arange(len(delays))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, h2_throughput, width, label='HTTP/2', color='#1f77b4', alpha=0.8)
    bars2 = ax1.bar(x + width/2, h3_throughput, width, label='HTTP/3', color='#ff7f0e', alpha=0.8)
    
    ax1.set_xlabel('遅延 (ms)', fontproperties=jp_font)
    ax1.set_ylabel('スループット (req/s)', fontproperties=jp_font)
    ax1.set_title('スループット比較 (5回平均)', fontproperties=jp_font)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)], fontproperties=jp_font)
    ax1.legend(prop=jp_font)
    ax1.grid(True, alpha=0.3)
    
    # 2. Latency comparison
    ax2 = axes[0, 1]
    bars3 = ax2.bar(x - width/2, h2_latency, width, label='HTTP/2', color='#1f77b4', alpha=0.8)
    bars4 = ax2.bar(x + width/2, h3_latency, width, label='HTTP/3', color='#ff7f0e', alpha=0.8)
    
    ax2.set_xlabel('遅延 (ms)', fontproperties=jp_font)
    ax2.set_ylabel('レイテンシ (ms)', fontproperties=jp_font)
    ax2.set_title('レイテンシ比較 (5回平均)', fontproperties=jp_font)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)], fontproperties=jp_font)
    ax2.legend(prop=jp_font)
    ax2.grid(True, alpha=0.3)
    
    # 3. Connection time comparison
    ax3 = axes[0, 2]
    bars5 = ax3.bar(x - width/2, h2_connection, width, label='HTTP/2', color='#1f77b4', alpha=0.8)
    bars6 = ax3.bar(x + width/2, h3_connection, width, label='HTTP/3', color='#ff7f0e', alpha=0.8)
    
    ax3.set_xlabel('遅延 (ms)', fontproperties=jp_font)
    ax3.set_ylabel('接続時間 (ms)', fontproperties=jp_font)
    ax3.set_title('接続時間比較 (5回平均)', fontproperties=jp_font)
    ax3.set_xticks(x)
    ax3.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)], fontproperties=jp_font)
    ax3.legend(prop=jp_font)
    ax3.grid(True, alpha=0.3)
    
    # 4. Throughput advantage over delay
    ax4 = axes[1, 0]
    colors = ['red' if adv < 0 else 'green' for adv in throughput_advantage]
    bars7 = ax4.bar(x, throughput_advantage, color=colors, alpha=0.7)
    ax4.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax4.set_xlabel('遅延 (ms)', fontproperties=jp_font)
    ax4.set_ylabel('HTTP/3 優位性 (%)', fontproperties=jp_font)
    ax4.set_title('スループット優位性 (5回平均)', fontproperties=jp_font)
    ax4.set_xticks(x)
    ax4.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)], fontproperties=jp_font)
    ax4.grid(True, alpha=0.3)
    
    # 5. Latency advantage over delay
    ax5 = axes[1, 1]
    colors = ['red' if adv < 0 else 'green' for adv in latency_advantage]
    bars8 = ax5.bar(x, latency_advantage, color=colors, alpha=0.7)
    ax5.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax5.set_xlabel('遅延 (ms)', fontproperties=jp_font)
    ax5.set_ylabel('HTTP/3 優位性 (%)', fontproperties=jp_font)
    ax5.set_title('レイテンシ優位性 (5回平均)', fontproperties=jp_font)
    ax5.set_xticks(x)
    ax5.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)], fontproperties=jp_font)
    ax5.grid(True, alpha=0.3)
    
    # 6. Connection time advantage over delay
    ax6 = axes[1, 2]
    colors = ['red' if adv < 0 else 'green' for adv in connection_advantage]
    bars9 = ax6.bar(x, connection_advantage, color=colors, alpha=0.7)
    ax6.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax6.set_xlabel('遅延 (ms)', fontproperties=jp_font)
    ax6.set_ylabel('HTTP/3 優位性 (%)', fontproperties=jp_font)
    ax6.set_title('接続時間優位性 (5回平均)', fontproperties=jp_font)
    ax6.set_xticks(x)
    ax6.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)], fontproperties=jp_font)
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'performance_comparison_overview.png'), 
                dpi=150, bbox_inches='tight')
    plt.close()

def create_detailed_performance_analysis(data, output_dir):
    """detailed_performance_analysis.pngと同様のグラフを生成"""
    if not data:
        return
    
    # データを遅延でソート
    data.sort(key=lambda x: x['Delay (ms)'])
    
    # データ抽出
    delays = [row['Delay (ms)'] for row in data]
    bandwidths = [row['Bandwidth (Mbps)'] for row in data]
    throughput_advantage = [row['Throughput Advantage (%)'] for row in data]
    latency_advantage = [row['Latency Advantage (%)'] for row in data]
    
    # Create detailed analysis figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('HTTP/3 vs HTTP/2 性能逆転現象 詳細分析 - 5回実行平均結果', fontsize=16, fontweight='bold', fontproperties=jp_font)
    
    # 1. Throughput advantage trend
    ax1 = axes[0, 0]
    ax1.plot(delays, throughput_advantage, 'o-', linewidth=2, markersize=8, 
             color='#2E8B57', label='スループット優位性', alpha=0.7)
    ax1.axhline(y=0, color='red', linestyle='--', alpha=0.7, label='均衡ライン')
    ax1.set_xlabel('遅延 (ms)', fontproperties=jp_font)
    ax1.set_ylabel('HTTP/3優位性 (%)', fontproperties=jp_font)
    ax1.set_title('遅延とスループット優位性の関係 (5回平均)', fontproperties=jp_font)
    ax1.grid(True, alpha=0.3)
    ax1.legend(prop=jp_font)
    
    # 2. Bandwidth vs throughput advantage
    ax2 = axes[0, 1]
    scatter = ax2.scatter(bandwidths, throughput_advantage, c=delays, 
                         s=100, cmap='viridis', alpha=0.7)
    ax2.axhline(y=0, color='red', linestyle='--', alpha=0.7)
    ax2.set_xlabel('帯域幅 (Mbps)', fontproperties=jp_font)
    ax2.set_ylabel('HTTP/3優位性 (%)', fontproperties=jp_font)
    ax2.set_title('帯域幅とスループット優位性の関係 (5回平均)', fontproperties=jp_font)
    ax2.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax2)
    cbar.set_label('遅延 (ms)', fontproperties=jp_font)
    
    # 3. Performance reversal threshold analysis
    ax3 = axes[1, 0]
    
    # Color code based on conditions
    colors = []
    for delay, bw, adv in zip(delays, bandwidths, throughput_advantage):
        if delay >= 300 and bw <= 10:
            colors.append('green')  # HTTP/3 advantage zone
        elif adv > 0:
            colors.append('lightgreen')  # HTTP/3 advantage
        else:
            colors.append('lightcoral')  # HTTP/2 advantage
    
    bars = ax3.bar(range(len(delays)), throughput_advantage, color=colors, alpha=0.8)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax3.set_xlabel('テストケース', fontproperties=jp_font)
    ax3.set_ylabel('HTTP/3優位性 (%)', fontproperties=jp_font)
    ax3.set_title('性能逆転閾値分析 (5回平均)', fontproperties=jp_font)
    ax3.set_xticks(range(len(delays)))
    ax3.set_xticklabels([f"{d}ms\n{b}Mbps" for d, b in zip(delays, bandwidths)], rotation=45)
    ax3.grid(True, alpha=0.3)
    
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
    ax4.set_title('性能比較マトリクス (5回平均)\n(緑=HTTP/3優位、赤=HTTP/2優位)', fontproperties=jp_font)
    
    # Add colorbar
    cbar2 = plt.colorbar(im, ax=ax4)
    cbar2.set_label('HTTP/3優位性 (%)', fontproperties=jp_font)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'detailed_performance_analysis.png'), 
                dpi=150, bbox_inches='tight')
    plt.close()

def create_network_conditions_info(data, output_dir):
    """network_conditions_info.pngと同様のグラフを生成"""
    if not data:
        return
    
    # データ抽出
    delays = [row['Delay (ms)'] for row in data]
    losses = [row['Loss (%)'] for row in data]
    bandwidths = [row['Bandwidth (Mbps)'] for row in data]
    h2_throughputs = [row['HTTP/2 Throughput (req/s)'] for row in data]
    h3_throughputs = [row['HTTP/3 Throughput (req/s)'] for row in data]
    h2_latencies = [row['HTTP/2 Latency (ms)'] for row in data]
    h3_latencies = [row['HTTP/3 Latency (ms)'] for row in data]
    throughput_advantages = [row['Throughput Advantage (%)'] for row in data]
    latency_advantages = [row['Latency Advantage (%)'] for row in data]
    connection_advantages = [row['Connection Advantage (%)'] for row in data]
    
    # 図の作成
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('テスト条件とネットワーク環境設定 - 5回実行平均結果', fontsize=18, fontweight='bold', fontproperties=jp_font)
    
    # 1. ネットワーク条件の分布
    ax1 = axes[0, 0]
    
    # 遅延の分布
    ax1.scatter(delays, [1]*len(delays), c='red', s=100, alpha=0.7, label='遅延 (ms)')
    ax1.scatter(losses, [0.8]*len(losses), c='blue', s=100, alpha=0.7, label='損失率 (%)')
    ax1.scatter(bandwidths, [0.6]*len(bandwidths), c='green', s=100, alpha=0.7, label='帯域幅 (Mbps)')
    
    ax1.set_xlabel('値', fontproperties=jp_font)
    ax1.set_ylabel('ネットワーク条件', fontproperties=jp_font)
    ax1.set_title('遅延・損失・帯域の分布 (5回平均)', fontproperties=jp_font)
    ax1.legend(['遅延 (ms)', '損失率 (%)', '帯域幅 (Mbps)'], prop=jp_font)
    
    # 2. 性能比較の詳細表
    ax2 = axes[0, 1]
    ax2.axis('tight')
    ax2.axis('off')
    
    # テーブルデータの準備
    table_data = []
    headers = ['条件', 'HTTP/2', 'HTTP/3', '優位性']
    
    for i, row in enumerate(data):
        cond_str = f"{row['Delay (ms)']}ms/{row['Loss (%)']}%"
        
        # スループット行
        h2_tp = f"{row['HTTP/2 Throughput (req/s)']:.0f}"
        h3_tp = f"{row['HTTP/3 Throughput (req/s)']:.0f}"
        tp_adv = f"{row['Throughput Advantage (%)']:+.1f}%"
        table_data.append([cond_str + ' Throughput', h2_tp, h3_tp, tp_adv])
        
        # レイテンシ行
        h2_lat = f"{row['HTTP/2 Latency (ms)']:.3f}"
        h3_lat = f"{row['HTTP/3 Latency (ms)']:.3f}"
        lat_adv = f"{row['Latency Advantage (%)']:+.1f}%"
        table_data.append([cond_str + ' Latency', h2_lat, h3_lat, lat_adv])
        
        # 接続時間行
        h2_conn = f"{row['HTTP/2 Connection Time (ms)']:.3f}"
        h3_conn = f"{row['HTTP/3 Connection Time (ms)']:.3f}"
        conn_adv = f"{row['Connection Advantage (%)']:+.1f}%"
        table_data.append([cond_str + ' Connection Time', h2_conn, h3_conn, conn_adv])
        
        if i < len(data) - 1:
            table_data.append(['', '', '', ''])  # 空行
    
    table = ax2.table(cellText=table_data, colLabels=headers, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.1, 2)
    
    # テーブルのスタイル設定
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white', fontproperties=jp_font)
    
    # 3. ネットワーク条件の影響分析
    ax3 = axes[1, 0]
    
    colors = ['red' if adv < 0 else 'green' for adv in throughput_advantages]
    bars = ax3.bar(range(len(delays)), throughput_advantages, color=colors, alpha=0.7)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    ax3.set_xlabel('テストケース', fontproperties=jp_font)
    ax3.set_ylabel('HTTP/3優位性 (%)', fontproperties=jp_font)
    ax3.set_title('遅延条件下でのHTTP/3優位性 (5回平均)', fontproperties=jp_font)
    ax3.set_xticks(range(len(delays)))
    ax3.set_xticklabels([f"{row['Delay (ms)']}ms\n{row['Loss (%)']}%" for row in data], rotation=45)
    ax3.grid(True, alpha=0.3)
    
    # 4. テスト環境の概要
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')
    
    # テスト環境の情報
    exec_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    env_info = [
        ['実行日時', exec_time],
        ['テスト環境', '値'],
        ['テストケース数', f"{len(data)}"],
        ['遅延範囲', f"{min(delays)}ms - {max(delays)}ms"],
        ['損失範囲', f"{min(losses)}% - {max(losses)}%"],
        ['帯域範囲', f"{min(bandwidths)}Mbps - {max(bandwidths)}Mbps"],
        ['HTTP/3優位ケース', f"{sum(1 for adv in throughput_advantages if adv > 0)}/{len(data)}"],
        ['HTTP/2優位ケース', f"{sum(1 for adv in throughput_advantages if adv < 0)}/{len(data)}"],
        ['平均スループット優位性', f"{np.mean(throughput_advantages):.1f}%"],
        ['平均レイテンシ優位性', f"{np.mean(latency_advantages):.1f}%"],
        ['平均接続時間優位性', f"{np.mean(connection_advantages):.1f}%"],
        ['', ''],
        ['平均化処理', '5回実行の平均値'],
        ['統計的信頼性', '標準偏差付き'],
    ]

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
    
    # 保存
    fig.canvas.draw()
    output_file = os.path.join(output_dir, 'network_conditions_info.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Network Conditions Information Graph Generation Completed: {output_file}")

def create_averaged_summary(data, output_dir):
    """平均化結果のサマリーを作成"""
    if not data:
        return
    
    # 統計計算
    throughput_advantages = [row['Throughput Advantage (%)'] for row in data]
    latency_advantages = [row['Latency Advantage (%)'] for row in data]
    
    h3_advantage_count = sum(1 for adv in throughput_advantages if adv > 0)
    h2_advantage_count = sum(1 for adv in throughput_advantages if adv < 0)
    
    # サマリーファイル作成
    summary_file = os.path.join(output_dir, 'averaged_benchmark_summary.txt')
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("HTTP/3 vs HTTP/2 Performance Comparison - Averaged Results (5 executions)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("📊 Averaged Results Summary\n")
        f.write("-" * 40 + "\n")
        f.write(f"• Total Test Cases: {len(data)}\n")
        f.write(f"• HTTP/3 Advantage Cases: {h3_advantage_count}/{len(data)} Cases\n")
        f.write(f"• HTTP/2 Advantage Cases: {h2_advantage_count}/{len(data)} Cases\n")
        f.write(f"• Average Throughput Advantage: {np.mean(throughput_advantages):.1f}%\n")
        f.write(f"• Average Latency Advantage: {np.mean(latency_advantages):.1f}%\n")
        f.write(f"• Standard Deviation (Throughput): {np.std(throughput_advantages):.1f}%\n")
        f.write(f"• Standard Deviation (Latency): {np.std(latency_advantages):.1f}%\n\n")
        
        f.write("🎯 Detailed Results\n")
        f.write("-" * 40 + "\n")
        for row in data:
            f.write(f"• {row['Delay (ms)']}ms Delay, {row['Loss (%)']}% Loss, {row['Bandwidth (Mbps)']}Mbps BW:\n")
            f.write(f"  - HTTP/2 Throughput: {row['HTTP/2 Throughput (req/s)']:.1f} req/s\n")
            f.write(f"  - HTTP/3 Throughput: {row['HTTP/3 Throughput (req/s)']:.1f} req/s\n")
            f.write(f"  - Throughput Advantage: {row['Throughput Advantage (%)']:+.1f}%\n")
            f.write(f"  - Latency Advantage: {row['Latency Advantage (%)']:+.1f}%\n\n")
    
    print(f"Averaged summary created: {summary_file}")

def copy_benchmark_directories(log_dirs, output_dir):
    """5回のベンチマーク結果ディレクトリをコピー"""
    benchmark_dirs = os.path.join(output_dir, 'benchmark_runs')
    os.makedirs(benchmark_dirs, exist_ok=True)
    
    for i, log_dir in enumerate(log_dirs, 1):
        # ディレクトリ名を変更してコピー
        new_name = f"run_{i:02d}"
        new_path = os.path.join(benchmark_dirs, new_name)
        
        if os.path.exists(log_dir):
            shutil.copytree(log_dir, new_path)
            print(f"Copied benchmark run {i}: {new_path}")
    
    return benchmark_dirs

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='Average benchmark results from multiple executions')
    parser.add_argument('log_dirs', nargs='+', help='Benchmark log directories')
    args = parser.parse_args()
    
    # 平均化データを計算
    averaged_data = average_benchmark_results(args.log_dirs)
    
    if not averaged_data:
        print("Error: Failed to average benchmark data")
        sys.exit(1)
    
    # 出力ディレクトリ作成
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"logs/average_benchmark_{now}"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    
    # 5回のベンチマーク結果ディレクトリをコピー
    benchmark_dirs = copy_benchmark_directories(args.log_dirs, output_dir)
    
    # 平均化データをCSVに保存
    csv_file = os.path.join(output_dir, 'averaged_results.csv')
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if averaged_data:
            writer = csv.DictWriter(f, fieldnames=averaged_data[0].keys())
            writer.writeheader()
            writer.writerows(averaged_data)
    
    print(f"Averaged data saved: {csv_file}")
    
    # 3つのグラフを生成
    create_performance_comparison_overview(averaged_data, output_dir)
    create_detailed_performance_analysis(averaged_data, output_dir)
    create_network_conditions_info(averaged_data, output_dir)
    
    # サマリー作成
    create_averaged_summary(averaged_data, output_dir)
    
    print(f"All averaged graphs created in: {output_dir}")

if __name__ == "__main__":
    main() 