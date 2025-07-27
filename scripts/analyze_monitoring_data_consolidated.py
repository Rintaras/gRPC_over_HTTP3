#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
監視データ統合分析スクリプト
5回実行の監視データを統合して分析
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import json
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.family'] = ['Hiragino Sans', 'Arial Unicode MS', 'DejaVu Sans']

class ConsolidatedMonitoringAnalyzer:
    def __init__(self):
        self.experiment_data = {}
        self.consolidated_results = {}
        
    def find_latest_experiments(self, log_dir="logs", pattern="monitored_benchmark_*"):
        """最新の監視付きベンチマーク実験を検索"""
        print("🔍 最新の監視付きベンチマーク実験を検索中...")
        
        log_path = Path(log_dir)
        experiment_dirs = []
        
        for dir_path in log_path.glob(pattern):
            if dir_path.is_dir():
                experiment_dirs.append(dir_path)
        
        # 最新の5つの実験を取得
        experiment_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_experiments = experiment_dirs[:5]
        
        print(f"✅ {len(latest_experiments)}個の実験ディレクトリを発見")
        for exp_dir in latest_experiments:
            print(f"  - {exp_dir.name}")
        
        return latest_experiments
    
    def analyze_experiment_consistency(self, experiment_dirs):
        """実験間の一貫性を分析"""
        print("\n📊 実験間の一貫性を分析中...")
        
        consistency_data = {
            'throughput': [],
            'latency': [],
            'success_rate': [],
            'execution_time': []
        }
        
        for exp_dir in experiment_dirs:
            # ベンチマークサマリーファイルを読み込み
            summary_file = exp_dir / "benchmark_summary.txt"
            if summary_file.exists():
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 実行時間を抽出（簡易版）
                    execution_time = 0
                    if "実行時間:" in content:
                        time_line = [line for line in content.split('\n') if "実行時間:" in line]
                        if time_line:
                            time_str = time_line[0].split("実行時間:")[1].strip()
                            execution_time = int(time_str.split()[0])
                    
                    consistency_data['execution_time'].append(execution_time)
                    
                except Exception as e:
                    print(f"⚠️ サマリーファイル読み込みエラー ({exp_dir.name}): {e}")
            
            # CSVファイルから性能データを抽出
            csv_files = list(exp_dir.glob("*.csv"))
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file, header=None, sep='\t')
                    if len(df.columns) >= 3:
                        df.columns = ['timestamp', 'status_code', 'response_time'] + list(df.columns[3:])
                        
                        # 性能指標を計算
                        throughput = len(df) / (df['response_time'].max() - df['response_time'].min()) * 1000000 if len(df) > 1 else 0
                        latency = df['response_time'].mean() / 1000  # μs to ms
                        success_rate = (df['status_code'] == 200).mean() * 100
                        
                        consistency_data['throughput'].append(throughput)
                        consistency_data['latency'].append(latency)
                        consistency_data['success_rate'].append(success_rate)
                        
                except Exception as e:
                    print(f"⚠️ CSVファイル読み込みエラー ({csv_file.name}): {e}")
        
        # 一貫性統計を計算
        consistency_stats = {}
        for metric, values in consistency_data.items():
            if values:
                values = np.array(values)
                consistency_stats[metric] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'cv': np.std(values) / np.mean(values) if np.mean(values) > 0 else 0,
                    'min': np.min(values),
                    'max': np.max(values),
                    'range': np.max(values) - np.min(values)
                }
        
        self.consolidated_results['consistency'] = consistency_stats
        print("✅ 実験間一貫性分析完了")
        
    def generate_consolidated_report(self, experiment_dirs):
        """統合レポートを生成"""
        print("\n📄 統合レポートを生成中...")
        
        # レポート内容
        report_content = []
        report_content.append("=" * 80)
        report_content.append("監視付きベンチマーク統合分析レポート")
        report_content.append("=" * 80)
        report_content.append(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_content.append(f"分析対象実験数: {len(experiment_dirs)}")
        report_content.append("")
        
        # 実験ディレクトリ一覧
        report_content.append("📁 分析対象実験:")
        for i, exp_dir in enumerate(experiment_dirs, 1):
            report_content.append(f"  {i}. {exp_dir.name}")
        report_content.append("")
        
        # 一貫性分析結果
        if 'consistency' in self.consolidated_results:
            report_content.append("📊 実験間一貫性分析結果")
            report_content.append("-" * 40)
            
            consistency_stats = self.consolidated_results['consistency']
            
            for metric, stats in consistency_stats.items():
                if metric == 'throughput':
                    metric_name = "スループット"
                    unit = "req/s"
                elif metric == 'latency':
                    metric_name = "レイテンシー"
                    unit = "ms"
                elif metric == 'success_rate':
                    metric_name = "成功率"
                    unit = "%"
                elif metric == 'execution_time':
                    metric_name = "実行時間"
                    unit = "秒"
                else:
                    metric_name = metric
                    unit = ""
                
                report_content.append(f"📈 {metric_name}:")
                report_content.append(f"  - 平均: {stats['mean']:.2f} {unit}")
                report_content.append(f"  - 標準偏差: {stats['std']:.2f} {unit}")
                report_content.append(f"  - 変動係数: {stats['cv']:.3f}")
                report_content.append(f"  - 範囲: {stats['min']:.2f} 〜 {stats['max']:.2f} {unit}")
                
                # 一貫性評価
                if stats['cv'] < 0.1:
                    consistency_level = "非常に高い"
                elif stats['cv'] < 0.2:
                    consistency_level = "高い"
                elif stats['cv'] < 0.3:
                    consistency_level = "中程度"
                else:
                    consistency_level = "低い"
                
                report_content.append(f"  - 一貫性レベル: {consistency_level}")
                report_content.append("")
        
        # 総合評価
        report_content.append("🎯 総合評価")
        report_content.append("-" * 40)
        
        # 平均変動係数を計算
        avg_cv = np.mean([stats['cv'] for stats in consistency_stats.values()])
        
        if avg_cv < 0.15:
            overall_consistency = "非常に高い"
            recommendation = "現在の設定で十分な一貫性が確保されています"
        elif avg_cv < 0.25:
            overall_consistency = "高い"
            recommendation = "軽微な調整で一貫性を向上できます"
        elif avg_cv < 0.35:
            overall_consistency = "中程度"
            recommendation = "設定の見直しが必要です"
        else:
            overall_consistency = "低い"
            recommendation = "根本的な改善が必要です"
        
        report_content.append(f"• 全体的な一貫性: {overall_consistency}")
        report_content.append(f"• 平均変動係数: {avg_cv:.3f}")
        report_content.append(f"• 推奨事項: {recommendation}")
        report_content.append("")
        
        # 改善提案
        report_content.append("💡 改善提案")
        report_content.append("-" * 40)
        
        improvements = []
        
        if 'latency' in consistency_stats and consistency_stats['latency']['cv'] > 0.3:
            improvements.append("• レイテンシー測定の安定化")
        
        if 'throughput' in consistency_stats and consistency_stats['throughput']['cv'] > 0.3:
            improvements.append("• スループット測定の安定化")
        
        if 'execution_time' in consistency_stats and consistency_stats['execution_time']['cv'] > 0.2:
            improvements.append("• 実行時間の一貫性確保")
        
        if not improvements:
            improvements.append("• 現在の設定で十分な安定性が確保されています")
        
        for improvement in improvements:
            report_content.append(improvement)
        
        report_content.append("")
        report_content.append("=" * 80)
        
        # レポート保存
        report_dir = Path("logs") / f"consolidated_monitoring_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = report_dir / "consolidated_monitoring_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_content))
        
        print(f"✅ 統合レポート保存完了: {report_path}")
        
        # 統合グラフを生成
        self.generate_consolidated_plots(report_dir, consistency_stats)
        
    def generate_consolidated_plots(self, report_dir, consistency_stats):
        """統合分析グラフを生成"""
        print("📊 統合分析グラフを生成中...")
        
        # 一貫性比較グラフ
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('監視付きベンチマーク統合分析結果', fontsize=16, fontweight='bold')
        
        # 変動係数比較
        ax1 = axes[0, 0]
        metrics = list(consistency_stats.keys())
        cv_values = [consistency_stats[metric]['cv'] for metric in metrics]
        metric_names = ['スループット', 'レイテンシー', '成功率', '実行時間']
        
        bars = ax1.bar(metric_names, cv_values, color=['blue', 'red', 'green', 'orange'])
        ax1.set_title('各指標の変動係数比較')
        ax1.set_ylabel('変動係数 (CV)')
        ax1.grid(True, alpha=0.3)
        
        # 値に応じて色を変更
        for bar, cv in zip(bars, cv_values):
            if cv > 0.3:
                bar.set_color('red')
            elif cv > 0.2:
                bar.set_color('orange')
            else:
                bar.set_color('green')
        
        # 範囲比較
        ax2 = axes[0, 1]
        range_values = [consistency_stats[metric]['range'] for metric in metrics]
        ax2.bar(metric_names, range_values, color=['blue', 'red', 'green', 'orange'])
        ax2.set_title('各指標の範囲比較')
        ax2.set_ylabel('範囲')
        ax2.grid(True, alpha=0.3)
        
        # 平均値と標準偏差
        ax3 = axes[1, 0]
        means = [consistency_stats[metric]['mean'] for metric in metrics]
        stds = [consistency_stats[metric]['std'] for metric in metrics]
        
        x_pos = np.arange(len(metric_names))
        ax3.bar(x_pos, means, yerr=stds, capsize=5, color=['blue', 'red', 'green', 'orange'])
        ax3.set_title('平均値と標準偏差')
        ax3.set_ylabel('値')
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(metric_names)
        ax3.grid(True, alpha=0.3)
        
        # 一貫性レベル分布
        ax4 = axes[1, 1]
        consistency_levels = []
        for metric, stats in consistency_stats.items():
            cv = stats['cv']
            if cv < 0.1:
                level = "非常に高い"
            elif cv < 0.2:
                level = "高い"
            elif cv < 0.3:
                level = "中程度"
            else:
                level = "低い"
            consistency_levels.append(level)
        
        level_counts = pd.Series(consistency_levels).value_counts()
        ax4.pie(level_counts.values, labels=level_counts.index, autopct='%1.1f%%', startangle=90)
        ax4.set_title('一貫性レベルの分布')
        
        plt.tight_layout()
        plot_path = report_dir / "consolidated_monitoring_analysis.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 統合分析グラフ保存: {plot_path}")
        
    def run_analysis(self):
        """完全な統合分析を実行"""
        print("🚀 監視データ統合分析を開始...")
        
        # 最新の実験を検索
        experiment_dirs = self.find_latest_experiments()
        
        if not experiment_dirs:
            print("❌ 分析対象の実験が見つかりませんでした")
            return
        
        # 実験間一貫性を分析
        self.analyze_experiment_consistency(experiment_dirs)
        
        # 統合レポートを生成
        self.generate_consolidated_report(experiment_dirs)
        
        print(f"\n✅ 監視データ統合分析完了！")

if __name__ == "__main__":
    analyzer = ConsolidatedMonitoringAnalyzer()
    analyzer.run_analysis() 