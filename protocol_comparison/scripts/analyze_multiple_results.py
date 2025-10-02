#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from datetime import datetime

# 日本語フォント設定
plt.rcParams['font.family'] = ['Hiragino Sans', 'DejaVu Sans', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def load_and_analyze_data(csv_files):
    """複数のCSVファイルを読み込んで分析"""
    all_data = []
    
    for i, csv_file in enumerate(csv_files):
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            df['experiment'] = f'実験{i+1}'
            all_data.append(df)
            print(f"実験{i+1}: {len(df)} レコード読み込み完了")
        else:
            print(f"警告: {csv_file} が見つかりません")
    
    return pd.concat(all_data, ignore_index=True) if all_data else None

def calculate_statistics(df):
    """統計値を計算"""
    stats = []
    
    for experiment in df['experiment'].unique():
        for protocol in df['protocol'].unique():
            for latency in df['latency'].unique():
                subset = df[(df['experiment'] == experiment) & 
                           (df['protocol'] == protocol) & 
                           (df['latency'] == latency)]
                
                if len(subset) > 0:
                    stats.append({
                        'experiment': experiment,
                        'protocol': protocol,
                        'latency': latency,
                        'count': len(subset),
                        'mean_time': subset['time_total'].mean(),
                        'std_time': subset['time_total'].std(),
                        'mean_speed': subset['speed_kbps'].mean(),
                        'std_speed': subset['speed_kbps'].std(),
                        'min_time': subset['time_total'].min(),
                        'max_time': subset['time_total'].max(),
                        'median_time': subset['time_total'].median(),
                        'q25_time': subset['time_total'].quantile(0.25),
                        'q75_time': subset['time_total'].quantile(0.75)
                    })
    
    return pd.DataFrame(stats)

def create_comparison_plots(df, stats, output_dir):
    """比較グラフを作成"""
    
    # 1. 平均応答時間の比較（実験別）
    plt.figure(figsize=(15, 10))
    
    # 実験別の平均応答時間
    plt.subplot(2, 3, 1)
    for experiment in df['experiment'].unique():
        exp_data = stats[stats['experiment'] == experiment]
        for protocol in ['HTTP/2', 'HTTP/3']:
            protocol_data = exp_data[exp_data['protocol'] == protocol]
            latencies = [0, 25, 50, 75, 100, 125, 150, 175, 200]
            times = [protocol_data[protocol_data['latency'] == f'{l}ms']['mean_time'].iloc[0] 
                    if len(protocol_data[protocol_data['latency'] == f'{l}ms']) > 0 else 0 
                    for l in latencies]
            plt.plot(latencies, times, marker='o', label=f'{protocol} ({experiment})', linewidth=2)
    
    plt.xlabel('遅延 (ms)')
    plt.ylabel('平均応答時間 (秒)')
    plt.title('実験別平均応答時間比較')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    
    # 2. 標準偏差の比較
    plt.subplot(2, 3, 2)
    for experiment in df['experiment'].unique():
        exp_data = stats[stats['experiment'] == experiment]
        for protocol in ['HTTP/2', 'HTTP/3']:
            protocol_data = exp_data[exp_data['protocol'] == protocol]
            latencies = [0, 25, 50, 75, 100, 125, 150, 175, 200]
            stds = [protocol_data[protocol_data['latency'] == f'{l}ms']['std_time'].iloc[0] 
                   if len(protocol_data[protocol_data['latency'] == f'{l}ms']) > 0 else 0 
                   for l in latencies]
            plt.plot(latencies, stds, marker='s', label=f'{protocol} ({experiment})', linewidth=2)
    
    plt.xlabel('遅延 (ms)')
    plt.ylabel('標準偏差 (秒)')
    plt.title('実験別安定性比較')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    
    # 3. 平均速度の比較
    plt.subplot(2, 3, 3)
    for experiment in df['experiment'].unique():
        exp_data = stats[stats['experiment'] == experiment]
        for protocol in ['HTTP/2', 'HTTP/3']:
            protocol_data = exp_data[exp_data['protocol'] == protocol]
            latencies = [0, 25, 50, 75, 100, 125, 150, 175, 200]
            speeds = [protocol_data[protocol_data['latency'] == f'{l}ms']['mean_speed'].iloc[0] 
                     if len(protocol_data[protocol_data['latency'] == f'{l}ms']) > 0 else 0 
                     for l in latencies]
            plt.plot(latencies, speeds, marker='^', label=f'{protocol} ({experiment})', linewidth=2)
    
    plt.xlabel('遅延 (ms)')
    plt.ylabel('平均速度 (KB/s)')
    plt.title('実験別平均速度比較')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    
    # 4. 実験間の一貫性（0ms遅延）
    plt.subplot(2, 3, 4)
    zero_latency = stats[stats['latency'] == '0ms']
    protocols = ['HTTP/2', 'HTTP/3']
    experiments = sorted(zero_latency['experiment'].unique())
    
    x = np.arange(len(experiments))
    width = 0.35
    
    for i, protocol in enumerate(protocols):
        protocol_data = zero_latency[zero_latency['protocol'] == protocol]
        times = [protocol_data[protocol_data['experiment'] == exp]['mean_time'].iloc[0] 
                if len(protocol_data[protocol_data['experiment'] == exp]) > 0 else 0 
                for exp in experiments]
        plt.bar(x + i*width, times, width, label=protocol, alpha=0.8)
    
    plt.xlabel('実験')
    plt.ylabel('平均応答時間 (秒)')
    plt.title('0ms遅延での実験間一貫性')
    plt.xticks(x + width/2, experiments)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 5. 変動係数（CV）の比較
    plt.subplot(2, 3, 5)
    cv_data = []
    for experiment in df['experiment'].unique():
        for protocol in ['HTTP/2', 'HTTP/3']:
            for latency in ['0ms', '25ms', '50ms', '75ms', '100ms', '125ms', '150ms', '175ms', '200ms']:
                subset = stats[(stats['experiment'] == experiment) & 
                              (stats['protocol'] == protocol) & 
                              (stats['latency'] == latency)]
                if len(subset) > 0:
                    cv = subset['std_time'].iloc[0] / subset['mean_time'].iloc[0] * 100
                    cv_data.append({
                        'experiment': experiment,
                        'protocol': protocol,
                        'latency': latency,
                        'cv': cv
                    })
    
    cv_df = pd.DataFrame(cv_data)
    for experiment in cv_df['experiment'].unique():
        exp_cv = cv_df[cv_df['experiment'] == experiment]
        for protocol in ['HTTP/2', 'HTTP/3']:
            protocol_cv = exp_cv[exp_cv['protocol'] == protocol]
            latencies = [0, 25, 50, 75, 100, 125, 150, 175, 200]
            cvs = [protocol_cv[protocol_cv['latency'] == f'{l}ms']['cv'].iloc[0] 
                  if len(protocol_cv[protocol_cv['latency'] == f'{l}ms']) > 0 else 0 
                  for l in latencies]
            plt.plot(latencies, cvs, marker='d', label=f'{protocol} ({experiment})', linewidth=2)
    
    plt.xlabel('遅延 (ms)')
    plt.ylabel('変動係数 (%)')
    plt.title('実験別変動係数比較')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    
    # 6. 全実験の平均値比較
    plt.subplot(2, 3, 6)
    overall_stats = stats.groupby(['protocol', 'latency']).agg({
        'mean_time': 'mean',
        'std_time': 'mean',
        'mean_speed': 'mean'
    }).reset_index()
    
    for protocol in ['HTTP/2', 'HTTP/3']:
        protocol_data = overall_stats[overall_stats['protocol'] == protocol]
        latencies = [0, 50, 100, 150]
        times = [protocol_data[protocol_data['latency'] == f'{l}ms']['mean_time'].iloc[0] 
                if len(protocol_data[protocol_data['latency'] == f'{l}ms']) > 0 else 0 
                for l in latencies]
        stds = [protocol_data[protocol_data['latency'] == f'{l}ms']['std_time'].iloc[0] 
               if len(protocol_data[protocol_data['latency'] == f'{l}ms']) > 0 else 0 
               for l in latencies]
        plt.errorbar(latencies, times, yerr=stds, marker='o', label=protocol, 
                    capsize=5, capthick=2, linewidth=2)
    
    plt.xlabel('遅延 (ms)')
    plt.ylabel('平均応答時間 (秒)')
    plt.title('全実験平均値比較（エラーバー付き）')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/multiple_experiments_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_detailed_analysis(stats, output_dir):
    """詳細分析レポートを作成"""
    
    # 統計サマリー
    summary = []
    
    for experiment in stats['experiment'].unique():
        exp_data = stats[stats['experiment'] == experiment]
        
        for protocol in ['HTTP/2', 'HTTP/3']:
            protocol_data = exp_data[exp_data['protocol'] == protocol]
            
            # 0ms遅延での性能
            zero_latency = protocol_data[protocol_data['latency'] == '0ms']
            if len(zero_latency) > 0:
                zero_time = zero_latency['mean_time'].iloc[0]
                zero_speed = zero_latency['mean_speed'].iloc[0]
                zero_std = zero_latency['std_time'].iloc[0]
            else:
                zero_time = zero_speed = zero_std = 0
            
            # 200ms遅延での性能
            high_latency = protocol_data[protocol_data['latency'] == '200ms']
            if len(high_latency) > 0:
                high_time = high_latency['mean_time'].iloc[0]
                high_speed = high_latency['mean_speed'].iloc[0]
                high_std = high_latency['std_time'].iloc[0]
            else:
                high_time = high_speed = high_std = 0
            
            # 性能劣化率
            degradation = ((high_time - zero_time) / zero_time * 100) if zero_time > 0 else 0
            
            summary.append({
                'experiment': experiment,
                'protocol': protocol,
                '0ms_time': zero_time,
                '0ms_speed': zero_speed,
                '0ms_std': zero_std,
                '200ms_time': high_time,
                '200ms_speed': high_speed,
                '200ms_std': high_std,
                'degradation_pct': degradation
            })
    
    summary_df = pd.DataFrame(summary)
    
    # レポート生成
    report = f"""
# 複数実験結果分析レポート
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 実験概要
- 実験数: {len(stats['experiment'].unique())}
- 各実験の条件: 帯域5Mbps、遅延0-200ms、パケット損失0%、データサイズ1MB、25回試行

## 主要結果

### 0ms遅延での性能比較
"""
    
    for experiment in summary_df['experiment'].unique():
        exp_summary = summary_df[summary_df['experiment'] == experiment]
        report += f"\n#### {experiment}\n"
        
        for protocol in ['HTTP/2', 'HTTP/3']:
            protocol_summary = exp_summary[exp_summary['protocol'] == protocol]
            if len(protocol_summary) > 0:
                data = protocol_summary.iloc[0]
                report += f"- **{protocol}**: {data['0ms_time']:.3f}秒 ± {data['0ms_std']:.3f}秒, {data['0ms_speed']:.1f} KB/s\n"
    
    report += "\n### 遅延影響分析\n"
    
    for experiment in summary_df['experiment'].unique():
        exp_summary = summary_df[summary_df['experiment'] == experiment]
        report += f"\n#### {experiment}\n"
        
        for protocol in ['HTTP/2', 'HTTP/3']:
            protocol_summary = exp_summary[exp_summary['protocol'] == protocol]
            if len(protocol_summary) > 0:
                data = protocol_summary.iloc[0]
                report += f"- **{protocol}**: 性能劣化率 {data['degradation_pct']:.1f}%\n"
    
    # 一貫性分析
    report += "\n### 実験間一貫性分析\n"
    
    for protocol in ['HTTP/2', 'HTTP/3']:
        protocol_data = summary_df[summary_df['protocol'] == protocol]
        if len(protocol_data) > 0:
            zero_times = protocol_data['0ms_time'].values
            zero_speeds = protocol_data['0ms_speed'].values
            
            time_cv = np.std(zero_times) / np.mean(zero_times) * 100
            speed_cv = np.std(zero_speeds) / np.mean(zero_speeds) * 100
            
            report += f"- **{protocol}**:\n"
            report += f"  - 応答時間の変動係数: {time_cv:.2f}%\n"
            report += f"  - 速度の変動係数: {speed_cv:.2f}%\n"
    
    # レポート保存
    with open(f'{output_dir}/multiple_experiments_analysis.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("詳細分析レポートを生成しました")
    return summary_df

def main():
    # 実験結果ファイル
    csv_files = [
        '/Users/root1/Documents/Research/gRPC_over_HTTP3/protocol_comparison/logs/20251002_104746/benchmark_results.csv',
        '/Users/root1/Documents/Research/gRPC_over_HTTP3/protocol_comparison/logs/20251001_211526/benchmark_results.csv',
        '/Users/root1/Documents/Research/gRPC_over_HTTP3/protocol_comparison/logs/20251001_184348/benchmark_results.csv'
    ]
    
    # 出力ディレクトリ
    output_dir = '/Users/root1/Documents/Research/gRPC_over_HTTP3/protocol_comparison/logs/multiple_analysis'
    os.makedirs(output_dir, exist_ok=True)
    
    print("複数実験結果の分析を開始します...")
    
    # データ読み込み
    df = load_and_analyze_data(csv_files)
    if df is None:
        print("データの読み込みに失敗しました")
        return
    
    print(f"総レコード数: {len(df)}")
    print(f"実験数: {df['experiment'].nunique()}")
    print(f"プロトコル: {df['protocol'].unique()}")
    print(f"遅延条件: {df['latency'].unique()}")
    
    # 統計計算
    stats = calculate_statistics(df)
    print(f"統計計算完了: {len(stats)} レコード")
    
    # グラフ生成
    print("比較グラフを生成中...")
    create_comparison_plots(df, stats, output_dir)
    
    # 詳細分析
    print("詳細分析を実行中...")
    summary_df = create_detailed_analysis(stats, output_dir)
    
    # 結果表示
    print("\n=== 分析結果サマリー ===")
    print(summary_df.to_string(index=False))
    
    print(f"\n分析完了！結果は {output_dir} に保存されました")

if __name__ == "__main__":
    main()
