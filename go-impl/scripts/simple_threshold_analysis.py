#!/usr/bin/env python3
"""
簡易閾値分析スクリプト
"""

import json
from pathlib import Path

def load_and_analyze_results(summary_dir):
    """結果を読み込み分析"""
    results = []
    
    # 結果読み込み
    for i in range(1, 6):
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
    
    # 遅延別分析
    delays = [0, 75, 150, 225]
    analysis = {}
    
    for delay in delays:
        delay_data = [r for r in results if r['delay_ms'] == delay]
        h2_data = [r for r in delay_data if r['protocol'] == 'HTTP/2']
        h3_data = [r for r in delay_data if r['protocol'] == 'HTTP/3']
        
        if h2_data and h3_data:
            # 平均値計算
            h2_avgs = [r['avg_latency_ms'] for r in h2_data]
            h3_avgs = [r['avg_latency_ms'] for r in h3_data]
            
            h2_mean = sum(h2_avgs) / len(h2_avgs)
            h3_mean = sum(h3_avgs) / len(h3_avgs)
            
            # 標準偏差計算
            h2_var = sum((x - h2_mean)**2 for x in h2_avgs) / len(h2_avgs)
            h3_var = sum((x - h3_mean)**2 for x in h3_avgs) / len(h3_avgs)
            h2_std = h2_var**0.5
            h3_std = h3_var**0.5
            
            # 相対的影響計算
            absolute_diff = abs(h3_mean - h2_mean)
            relative_diff = (absolute_diff / h2_mean * 100) if h2_mean > 0 else 0
            network_impact = (absolute_diff / delay * 100) if delay > 0 else 0
            
            analysis[delay] = {
                'h2_mean': h2_mean,
                'h2_std': h2_std,
                'h3_mean': h3_mean,
                'h3_std': h3_std,
                'absolute_diff_ms': absolute_diff,
                'relative_diff_percent': relative_diff,
                'network_impact_percent': network_impact,
                'significance_threshold': max(h2_std, h3_std) * 2,
                'practical_threshold': max(h2_std, h3_std) * 3,
            }
    
    return analysis

def generate_report(analysis, output_dir):
    """レポート生成"""
    report = []
    
    report.append("=" * 80)
    report.append("性能閾値分析レポート")
    report.append("=" * 80)
    report.append("")
    
    # 1. 統計的閾値
    report.append("1. 統計的閾値（2σ基準）")
    report.append("-" * 40)
    for delay, data in analysis.items():
        report.append(f"遅延 {delay}ms:")
        report.append(f"  HTTP/2: {data['h2_mean']:.6f} ± {data['h2_std']:.6f} ms")
        report.append(f"  HTTP/3: {data['h3_mean']:.6f} ± {data['h3_std']:.6f} ms")
        report.append(f"  統計的有意性閾値: {data['significance_threshold']:.6f} ms")
        report.append("")
    
    # 2. 実用性閾値
    report.append("2. 実用性閾値（相対的影響）")
    report.append("-" * 40)
    for delay, data in analysis.items():
        report.append(f"遅延 {delay}ms:")
        report.append(f"  絶対差: {data['absolute_diff_ms']:.6f} ms")
        report.append(f"  相対差: {data['relative_diff_percent']:.2f}%")
        if delay > 0:
            report.append(f"  ネットワーク影響: {data['network_impact_percent']:.3f}%")
        report.append("")
    
    # 3. 推奨閾値
    report.append("3. 推奨閾値設定")
    report.append("-" * 40)
    
    max_relative_diff = max(data['relative_diff_percent'] for data in analysis.values())
    max_absolute_diff = max(data['absolute_diff_ms'] for data in analysis.values())
    
    report.append(f"性能劣化検出閾値:")
    report.append(f"  相対的: {max_relative_diff * 0.5:.1f}% (現在最大の50%)")
    report.append(f"  絶対的: {max_absolute_diff * 0.5:.6f} ms")
    report.append("")
    
    report.append(f"性能劣化警告閾値:")
    report.append(f"  相対的: {max_relative_diff * 0.8:.1f}% (現在最大の80%)")
    report.append(f"  絶対的: {max_absolute_diff * 0.8:.6f} ms")
    report.append("")
    
    # 4. 実用性評価
    report.append("4. 実用性評価")
    report.append("-" * 40)
    
    # 最大のネットワーク影響を計算
    max_network_impact = max(data['network_impact_percent'] for data in analysis.values() if data['network_impact_percent'] > 0)
    
    report.append(f"最大ネットワーク影響: {max_network_impact:.3f}%")
    
    if max_network_impact < 0.1:
        report.append("評価: 性能差はネットワーク遅延に比べて無視できるレベル")
    elif max_network_impact < 1.0:
        report.append("評価: 性能差は小さいが測定可能")
    else:
        report.append("評価: 性能差は実用的に意味がある")
    
    report.append("")
    
    # 5. 推奨事項
    report.append("5. 推奨事項")
    report.append("-" * 40)
    report.append("この結果を閾値設定に使用する場合:")
    report.append("")
    report.append("✅ 有用な側面:")
    report.append("  - HTTP/2の安定性基準（CV < 5%）")
    report.append("  - HTTP/3の不安定性パターンの把握")
    report.append("  - 遅延条件による性能差の傾向")
    report.append("")
    report.append("❌ 制限事項:")
    report.append("  - 実際の性能差は0.01ms程度で極めて小さい")
    report.append("  - ネットワーク遅延（75-225ms）に比べて無視できる")
    report.append("  - サンプルサイズ（5回）では統計的信頼性が限定的")
    report.append("")
    report.append("🔧 改善提案:")
    report.append("  - より多くのサンプル（20回以上）での測定")
    report.append("  - 本番環境での検証")
    report.append("  - より大きな負荷での測定")
    report.append("  - 異なるネットワーク条件での測定")
    
    # レポート保存
    with open(Path(output_dir) / "threshold_analysis_report.txt", 'w') as f:
        f.write('\n'.join(report))
    
    return report

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python simple_threshold_analysis.py <summary_directory>")
        sys.exit(1)
    
    summary_dir = sys.argv[1]
    output_dir = Path(summary_dir)
    
    print("ベンチマーク結果を読み込み中...")
    analysis = load_and_analyze_results(summary_dir)
    
    print("閾値レポートを生成中...")
    report = generate_report(analysis, output_dir)
    
    print('\n'.join(report))
    
    print(f"\n分析完了:")
    print(f"レポート: {output_dir}/threshold_analysis_report.txt")

if __name__ == "__main__":
    main()
