#!/usr/bin/env python3

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime

def load_0rtt_data(csv_file):
    """0-RTTテスト結果のCSVファイルを読み込み"""
    try:
        df = pd.read_csv(csv_file)
        return df
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return None

def create_connection_time_comparison(df, output_dir):
    """接続時間比較グラフを作成"""
    
    plt.figure(figsize=(12, 8))
    
    # プロトコル別にデータを分離
    h2_data = df[df['Protocol'] == 'HTTP/2']
    h3_data = df[df['Protocol'] == 'HTTP/3']
    
    # 接続時間の比較
    protocols = ['HTTP/2', 'HTTP/3']
    avg_times = [h2_data['Connect_Time'].mean(), h3_data['Connect_Time'].mean()]
    std_times = [h2_data['Connect_Time'].std(), h3_data['Connect_Time'].std()]
    
    # バープロット
    bars = plt.bar(protocols, avg_times, yerr=std_times, capsize=5, 
                   color=['#1f77b4', '#ff7f0e'], alpha=0.7)
    
    # 値のラベルを追加
    for bar, avg, std in zip(bars, avg_times, std_times):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + std + 0.1,
                f'{avg:.3f}s\n±{std:.3f}s', ha='center', va='bottom')
    
    plt.title('HTTP/2 vs HTTP/3 Connection Time Comparison (0-RTT Test)', 
              fontsize=16, fontweight='bold')
    plt.ylabel('Connection Time (seconds)', fontsize=12)
    plt.xlabel('Protocol', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # 統計情報を追加
    advantage = ((avg_times[0] - avg_times[1]) / avg_times[0] * 100) if avg_times[0] > 0 else 0
    plt.figtext(0.5, 0.02, f'HTTP/3 Advantage: {advantage:.1f}%', 
                ha='center', fontsize=10, style='italic')
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, '0rtt_connection_time_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Connection time comparison graph saved: {output_file}")
    return output_file

def create_detailed_analysis(df, output_dir):
    """詳細分析グラフを作成"""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. テストタイプ別の接続時間
    test_types = df['Test_Type'].unique()
    for protocol in ['HTTP/2', 'HTTP/3']:
        protocol_data = df[df['Protocol'] == protocol]
        times = [protocol_data[protocol_data['Test_Type'] == test_type]['Connect_Time'].mean() 
                for test_type in test_types]
        ax1.bar([f"{protocol}\n{tt}" for tt in test_types], times, alpha=0.7, 
                label=protocol)
    
    ax1.set_title('Connection Time by Test Type', fontweight='bold')
    ax1.set_ylabel('Connection Time (seconds)')
    ax1.legend()
    ax1.tick_params(axis='x', rotation=45)
    
    # 2. プロトコル別の分布
    for protocol in ['HTTP/2', 'HTTP/3']:
        protocol_data = df[df['Protocol'] == protocol]['Connect_Time']
        ax2.hist(protocol_data, alpha=0.7, label=protocol, bins=10)
    
    ax2.set_title('Connection Time Distribution', fontweight='bold')
    ax2.set_xlabel('Connection Time (seconds)')
    ax2.set_ylabel('Frequency')
    ax2.legend()
    
    # 3. ボックスプロット
    df.boxplot(column='Connect_Time', by='Protocol', ax=ax3)
    ax3.set_title('Connection Time Box Plot', fontweight='bold')
    ax3.set_xlabel('Protocol')
    ax3.set_ylabel('Connection Time (seconds)')
    
    # 4. パフォーマンス比率
    h2_avg = df[df['Protocol'] == 'HTTP/2']['Connect_Time'].mean()
    h3_avg = df[df['Protocol'] == 'HTTP/3']['Connect_Time'].mean()
    ratio = h3_avg / h2_avg if h2_avg > 0 else 0
    
    ax4.pie([h2_avg, h3_avg], labels=['HTTP/2', 'HTTP/3'], autopct='%1.1f%%', 
             colors=['#1f77b4', '#ff7f0e'])
    ax4.set_title(f'Performance Ratio: {ratio:.2f}x', fontweight='bold')
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, '0rtt_detailed_analysis.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Detailed analysis graph saved: {output_file}")
    return output_file

def create_summary_statistics(df, output_dir):
    """統計サマリーグラフを作成"""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 1. 統計サマリー
    stats_data = []
    for protocol in ['HTTP/2', 'HTTP/3']:
        protocol_data = df[df['Protocol'] == protocol]['Connect_Time']
        stats_data.append({
            'Protocol': protocol,
            'Mean': protocol_data.mean(),
            'Std': protocol_data.std(),
            'Min': protocol_data.min(),
            'Max': protocol_data.max(),
            'Count': len(protocol_data)
        })
    
    stats_df = pd.DataFrame(stats_data)
    
    # 統計情報をテーブルとして表示
    ax1.axis('tight')
    ax1.axis('off')
    table = ax1.table(cellText=stats_df.values, colLabels=stats_df.columns, 
                      cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)
    ax1.set_title('Connection Time Statistics', fontweight='bold', pad=20)
    
    # 2. パフォーマンス比較
    h2_avg = df[df['Protocol'] == 'HTTP/2']['Connect_Time'].mean()
    h3_avg = df[df['Protocol'] == 'HTTP/3']['Connect_Time'].mean()
    
    metrics = ['Average', 'Minimum', 'Maximum']
    h2_values = [h2_avg, df[df['Protocol'] == 'HTTP/2']['Connect_Time'].min(), 
                 df[df['Protocol'] == 'HTTP/2']['Connect_Time'].max()]
    h3_values = [h3_avg, df[df['Protocol'] == 'HTTP/3']['Connect_Time'].min(), 
                 df[df['Protocol'] == 'HTTP/3']['Connect_Time'].max()]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    ax2.bar(x - width/2, h2_values, width, label='HTTP/2', alpha=0.7)
    ax2.bar(x + width/2, h3_values, width, label='HTTP/3', alpha=0.7)
    
    ax2.set_xlabel('Metrics')
    ax2.set_ylabel('Connection Time (seconds)')
    ax2.set_title('Performance Comparison', fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, '0rtt_summary_statistics.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Summary statistics graph saved: {output_file}")
    return output_file

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 generate_0rtt_graphs.py <log_directory>")
        sys.exit(1)
    
    log_dir = sys.argv[1]
    csv_file = os.path.join(log_dir, "0rtt_benchmark_results.csv")
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found: {csv_file}")
        print("Please run convert_0rtt_to_benchmark.py first")
        sys.exit(1)
    
    print(f"Generating 0-RTT graphs from: {csv_file}")
    
    # データを読み込み
    df = load_0rtt_data(csv_file)
    if df is None:
        sys.exit(1)
    
    print(f"Loaded {len(df)} data points")
    
    # グラフを生成
    create_connection_time_comparison(df, log_dir)
    create_detailed_analysis(df, log_dir)
    create_summary_statistics(df, log_dir)
    
    print("All 0-RTT graphs generated successfully!")
    print(f"Graphs saved in: {log_dir}")

if __name__ == "__main__":
    main() 