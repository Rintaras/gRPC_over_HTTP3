#!/usr/bin/env python3
"""
性能閾値分析スクリプト
より実用的な閾値設定のための分析
"""

import json
import csv
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

def load_benchmark_results(summary_dir):
    """ベンチマーク結果を読み込み"""
    results = []
    
    for i in range(1, 6):  # 5回実行
        json_file = Path(summary_dir) / f"run_{i}_results.json"
        if json_file.exists():
            with open(json_file, 'r') as f:
                run_results = json.load(f)
                for result in run_results:
                    result['run'] = i
                    # ナノ秒をミリ秒に変換
                    result['avg_latency_ms'] = result['avg_latency_ms'] / 1e6
                    result['min_latency_ms'] = result['min_latency_ms'] / 1e6
                    result['max_latency_ms'] = result['max_latency_ms'] / 1e6
                    result['p95_latency_ms'] = result['p95_latency_ms'] / 1e6
                    result['p99_latency_ms'] = result['p99_latency_ms'] / 1e6
                    results.append(result)
    
    return pd.DataFrame(results)

def calculate_thresholds(df):
    """実用的な閾値を計算"""
    thresholds = {}
    
    for delay in [0, 75, 150, 225]:
        delay_data = df[df['delay_ms'] == delay]
        
        h2_data = delay_data[delay_data['protocol'] == 'HTTP/2']['avg_latency_ms']
        h3_data = delay_data[delay_data['protocol'] == 'HTTP/3']['avg_latency_ms']
        
        if len(h2_data) > 0 and len(h3_data) > 0:
            # 統計的閾値
            h2_mean, h2_std = h2_data.mean(), h2_data.std()
            h3_mean, h3_std = h3_data.mean(), h3_data.std()
            
            # 実用的閾値（相対的な差）
            relative_diff = abs(h3_mean - h2_mean) / h2_mean * 100
            
            # ネットワーク遅延に対する相対的な影響
            network_impact = abs(h3_mean - h2_mean) / delay * 100 if delay > 0 else 0
            
            thresholds[delay] = {
                'h2_mean': h2_mean,
                'h2_std': h2_std,
                'h3_mean': h3_mean,
                'h3_std': h3_std,
                'absolute_diff_ms': abs(h3_mean - h2_mean),
                'relative_diff_percent': relative_diff,
                'network_impact_percent': network_impact,
                'significance_threshold': max(h2_std, h3_std) * 2,  # 2σ閾値
                'practical_threshold': max(h2_std, h3_std) * 3,     # 3σ閾値
            }
    
    return thresholds

def generate_threshold_report(thresholds, output_dir):
    """閾値レポートを生成"""
    report = []
    
    report.append("=" * 80)
    report.append("性能閾値分析レポート")
    report.append("=" * 80)
    report.append("")
    
    report.append("1. 統計的閾値（2σ基準）")
    report.append("-" * 40)
    for delay, thresh in thresholds.items():
        report.append(f"遅延 {delay}ms:")
        report.append(f"  HTTP/2: {thresh['h2_mean']:.6f} ± {thresh['h2_std']:.6f} ms")
        report.append(f"  HTTP/3: {thresh['h3_mean']:.6f} ± {thresh['h3_std']:.6f} ms")
        report.append(f"  統計的有意性閾値: {thresh['significance_threshold']:.6f} ms")
        report.append("")
    
    report.append("2. 実用性閾値（相対的影響）")
    report.append("-" * 40)
    for delay, thresh in thresholds.items():
        report.append(f"遅延 {delay}ms:")
        report.append(f"  絶対差: {thresh['absolute_diff_ms']:.6f} ms")
        report.append(f"  相対差: {thresh['relative_diff_percent']:.2f}%")
        if delay > 0:
            report.append(f"  ネットワーク影響: {thresh['network_impact_percent']:.3f}%")
        report.append("")
    
    report.append("3. 推奨閾値設定")
    report.append("-" * 40)
    
    # 最大の相対差を基準にした推奨閾値
    max_relative_diff = max(thresh['relative_diff_percent'] for thresh in thresholds.values())
    max_absolute_diff = max(thresh['absolute_diff_ms'] for thresh in thresholds.values())
    
    report.append(f"性能劣化検出閾値:")
    report.append(f"  相対的: {max_relative_diff * 0.5:.1f}% (現在最大の50%)")
    report.append(f"  絶対的: {max_absolute_diff * 0.5:.6f} ms")
    report.append("")
    
    report.append(f"性能劣化警告閾値:")
    report.append(f"  相対的: {max_relative_diff * 0.8:.1f}% (現在最大の80%)")
    report.append(f"  絶対的: {max_absolute_diff * 0.8:.6f} ms")
    report.append("")
    
    # レポート保存
    with open(Path(output_dir) / "threshold_analysis_report.txt", 'w') as f:
        f.write('\n'.join(report))
    
    return report

def create_threshold_visualization(df, thresholds, output_dir):
    """閾値可視化を作成"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Performance Threshold Analysis', fontsize=16)
    
    # 1. 絶対的レイテンシ比較
    ax1 = axes[0, 0]
    for protocol in ['HTTP/2', 'HTTP/3']:
        data = df[df['protocol'] == protocol]
        ax1.errorbar(data['delay_ms'], data['avg_latency_ms'], 
                    yerr=data.groupby('delay_ms')['avg_latency_ms'].std(),
                    label=protocol, marker='o', capsize=5)
    ax1.set_xlabel('Network Delay (ms)')
    ax1.set_ylabel('Average Latency (ms)')
    ax1.set_title('Absolute Latency Comparison')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 相対的性能差
    ax2 = axes[0, 1]
    delays = []
    relative_diffs = []
    for delay, thresh in thresholds.items():
        delays.append(delay)
        relative_diffs.append(thresh['relative_diff_percent'])
    
    ax2.bar(delays, relative_diffs, alpha=0.7, color='red')
    ax2.axhline(y=max(relative_diffs) * 0.5, color='orange', linestyle='--', 
                label=f'Detection Threshold ({max(relative_diffs) * 0.5:.1f}%)')
    ax2.axhline(y=max(relative_diffs) * 0.8, color='red', linestyle='--', 
                label=f'Warning Threshold ({max(relative_diffs) * 0.8:.1f}%)')
    ax2.set_xlabel('Network Delay (ms)')
    ax2.set_ylabel('Relative Performance Difference (%)')
    ax2.set_title('Performance Degradation Thresholds')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 安定性（CV）比較
    ax3 = axes[1, 0]
    protocols = ['HTTP/2', 'HTTP/3']
    delays = [0, 75, 150, 225]
    
    cv_data = {protocol: [] for protocol in protocols}
    for delay in delays:
        for protocol in protocols:
            delay_protocol_data = df[(df['delay_ms'] == delay) & (df['protocol'] == protocol)]['avg_latency_ms']
            cv = delay_protocol_data.std() / delay_protocol_data.mean() * 100 if delay_protocol_data.mean() > 0 else 0
            cv_data[protocol].append(cv)
    
    x = np.arange(len(delays))
    width = 0.35
    
    ax3.bar(x - width/2, cv_data['HTTP/2'], width, label='HTTP/2', alpha=0.7)
    ax3.bar(x + width/2, cv_data['HTTP/3'], width, label='HTTP/3', alpha=0.7)
    ax3.set_xlabel('Network Delay (ms)')
    ax3.set_ylabel('Coefficient of Variation (%)')
    ax3.set_title('Stability Comparison (CV)')
    ax3.set_xticks(x)
    ax3.set_xticklabels(delays)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. ネットワーク影響率
    ax4 = axes[1, 1]
    network_impacts = [thresh['network_impact_percent'] for thresh in thresholds.values() if thresh['network_impact_percent'] > 0]
    network_delays = [delay for delay, thresh in thresholds.items() if thresh['network_impact_percent'] > 0]
    
    ax4.bar(network_delays, network_impacts, alpha=0.7, color='purple')
    ax4.set_xlabel('Network Delay (ms)')
    ax4.set_ylabel('Impact on Network Delay (%)')
    ax4.set_title('Performance Impact on Network Delay')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(Path(output_dir) / "threshold_analysis.png", dpi=300, bbox_inches='tight')
    plt.close()

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python threshold_analysis.py <summary_directory>")
        sys.exit(1)
    
    summary_dir = sys.argv[1]
    output_dir = Path(summary_dir)
    
    # データ読み込み
    print("ベンチマーク結果を読み込み中...")
    df = load_benchmark_results(summary_dir)
    
    # 閾値計算
    print("閾値を計算中...")
    thresholds = calculate_thresholds(df)
    
    # レポート生成
    print("閾値レポートを生成中...")
    report = generate_threshold_report(thresholds, output_dir)
    
    # 可視化
    print("閾値可視化を作成中...")
    create_threshold_visualization(df, thresholds, output_dir)
    
    # 結果表示
    print('\n'.join(report))
    
    print(f"\n分析完了:")
    print(f"レポート: {output_dir}/threshold_analysis_report.txt")
    print(f"グラフ: {output_dir}/threshold_analysis.png")

if __name__ == "__main__":
    main()
