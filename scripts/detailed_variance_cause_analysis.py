#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ばらつきの原因を詳細に分析するスクリプト
極端なデータのばらつきの根本原因を特定
"""

import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.family'] = ['Hiragino Sans', 'Arial Unicode MS', 'DejaVu Sans']

class DetailedVarianceCauseAnalyzer:
    def __init__(self):
        self.experiment_data = {}
        self.variance_causes = {}
        
    def load_experiment_data(self, log_dir="logs"):
        """実験データを読み込み"""
        print("🔍 実験データを読み込み中...")
        
        # 最新の5回実験を検索
        experiment_dirs = []
        for item in os.listdir(log_dir):
            if item.startswith("japanese_benchmark_") and os.path.isdir(os.path.join(log_dir, item)):
                experiment_dirs.append(item)
        
        # 最新の5つを取得
        experiment_dirs.sort(reverse=True)
        latest_experiments = experiment_dirs[:5]
        
        print(f"📊 検出された実験数: {len(latest_experiments)}")
        
        for exp_dir in latest_experiments:
            exp_path = os.path.join(log_dir, exp_dir)
            print(f"🔍 実験: {exp_dir}")
            
            # CSVファイルを読み込み
            csv_files = [f for f in os.listdir(exp_path) if f.endswith('.csv')]
            
            exp_data = {}
            for csv_file in csv_files:
                csv_path = os.path.join(exp_path, csv_file)
                try:
                    # タブ区切りのCSVファイルを読み込み
                    df = pd.read_csv(csv_path, header=None, sep='\t')
                    df.columns = ['timestamp', 'status_code', 'response_time']
                    exp_data[csv_file] = df
                    print(f"  ✅ {csv_file}: {len(df)} 行")
                except Exception as e:
                    print(f"  ❌ {csv_file}: 読み込みエラー - {e}")
            
            self.experiment_data[exp_dir] = exp_data
        
        print(f"✅ データ読み込み完了: {len(self.experiment_data)} 実験")
        
    def analyze_outliers(self):
        """外れ値の分析"""
        print("\n🔍 外れ値分析を開始...")
        
        outlier_analysis = {}
        
        for exp_name, exp_data in self.experiment_data.items():
            exp_outliers = {}
            
            for csv_name, df in exp_data.items():
                if len(df) == 0:
                    continue
                
                # レスポンス時間の外れ値検出
                response_times = df['response_time'] / 1000  # μs to ms
                
                # 3σルールで外れ値を検出
                mean_rt = response_times.mean()
                std_rt = response_times.std()
                upper_bound = mean_rt + 3 * std_rt
                lower_bound = mean_rt - 3 * std_rt
                
                outliers = response_times[(response_times > upper_bound) | (response_times < lower_bound)]
                outlier_percentage = (len(outliers) / len(response_times)) * 100
                
                # 極端な外れ値（5σ以上）
                extreme_upper = mean_rt + 5 * std_rt
                extreme_lower = mean_rt - 5 * std_rt
                extreme_outliers = response_times[(response_times > extreme_upper) | (response_times < extreme_lower)]
                extreme_percentage = (len(extreme_outliers) / len(response_times)) * 100
                
                exp_outliers[csv_name] = {
                    'total_requests': len(response_times),
                    'outliers_3sigma': len(outliers),
                    'outlier_percentage_3sigma': outlier_percentage,
                    'extreme_outliers_5sigma': len(extreme_outliers),
                    'extreme_percentage_5sigma': extreme_percentage,
                    'mean_response_time': mean_rt,
                    'std_response_time': std_rt,
                    'max_response_time': response_times.max(),
                    'min_response_time': response_times.min(),
                    'outlier_times': outliers.tolist()[:10]  # 最初の10個
                }
            
            outlier_analysis[exp_name] = exp_outliers
        
        self.outlier_analysis = outlier_analysis
        print("✅ 外れ値分析完了")
        
    def analyze_timing_patterns(self):
        """タイミングパターンの分析"""
        print("\n⏰ タイミングパターン分析を開始...")
        
        timing_analysis = {}
        
        for exp_name, exp_data in self.experiment_data.items():
            exp_timing = {}
            
            for csv_name, df in exp_data.items():
                if len(df) == 0:
                    continue
                
                # タイムスタンプの分析
                timestamps = df['timestamp']
                response_times = df['response_time'] / 1000  # μs to ms
                
                # 時間間隔の計算
                time_intervals = timestamps.diff().dropna() / 1e9  # ナノ秒から秒に変換
                
                # パフォーマンスの時間的変化
                window_size = 1000  # 1000リクエストごとのウィンドウ
                performance_windows = []
                
                for i in range(0, len(response_times), window_size):
                    window_data = response_times.iloc[i:i+window_size]
                    if len(window_data) > 0:
                        performance_windows.append({
                            'window_start': i,
                            'window_end': min(i + window_size, len(response_times)),
                            'mean_response_time': window_data.mean(),
                            'std_response_time': window_data.std(),
                            'request_count': len(window_data)
                        })
                
                exp_timing[csv_name] = {
                    'total_duration': (timestamps.max() - timestamps.min()) / 1e9,
                    'mean_interval': time_intervals.mean(),
                    'std_interval': time_intervals.std(),
                    'performance_windows': performance_windows,
                    'response_time_trend': response_times.tolist()[:100]  # 最初の100個
                }
            
            timing_analysis[exp_name] = exp_timing
        
        self.timing_analysis = timing_analysis
        print("✅ タイミングパターン分析完了")
        
    def analyze_network_impact(self):
        """ネットワーク条件の影響分析"""
        print("\n📡 ネットワーク条件影響分析を開始...")
        
        network_analysis = {}
        
        for exp_name, exp_data in self.experiment_data.items():
            exp_network = {}
            
            for csv_name, df in exp_data.items():
                if len(df) == 0:
                    continue
                
                # ネットワーク条件を抽出
                network_match = re.search(r'(\d+)ms_(\d+)pct', csv_name)
                if network_match:
                    delay = int(network_match.group(1))
                    loss = int(network_match.group(2))
                else:
                    delay = 0
                    loss = 0
                
                response_times = df['response_time'] / 1000  # μs to ms
                
                # ネットワーク条件別の統計
                exp_network[csv_name] = {
                    'delay_ms': delay,
                    'loss_percent': loss,
                    'mean_response_time': response_times.mean(),
                    'std_response_time': response_times.std(),
                    'cv_response_time': response_times.std() / response_times.mean() if response_times.mean() > 0 else np.inf,
                    'p95_response_time': response_times.quantile(0.95),
                    'p99_response_time': response_times.quantile(0.99),
                    'max_response_time': response_times.max(),
                    'min_response_time': response_times.min()
                }
            
            network_analysis[exp_name] = exp_network
        
        self.network_analysis = network_analysis
        print("✅ ネットワーク条件影響分析完了")
        
    def identify_variance_causes(self):
        """ばらつきの原因を特定"""
        print("\n🔍 ばらつき原因の特定を開始...")
        
        causes = {
            'outlier_impact': {},
            'timing_instability': {},
            'network_variability': {},
            'experiment_consistency': {},
            'protocol_differences': {}
        }
        
        # 外れ値の影響
        total_outliers = 0
        total_requests = 0
        for exp_name, exp_outliers in self.outlier_analysis.items():
            for csv_name, outlier_data in exp_outliers.items():
                total_outliers += outlier_data['outliers_3sigma']
                total_requests += outlier_data['total_requests']
        
        outlier_percentage = (total_outliers / total_requests) * 100 if total_requests > 0 else 0
        causes['outlier_impact'] = {
            'total_outliers': total_outliers,
            'total_requests': total_requests,
            'outlier_percentage': outlier_percentage,
            'is_significant': outlier_percentage > 5  # 5%以上を有意とする
        }
        
        # タイミングの不安定性
        timing_instabilities = []
        for exp_name, exp_timing in self.timing_analysis.items():
            for csv_name, timing_data in exp_timing.items():
                if timing_data['std_interval'] > 0:
                    cv_interval = timing_data['std_interval'] / timing_data['mean_interval']
                    timing_instabilities.append(cv_interval)
        
        causes['timing_instability'] = {
            'mean_cv_interval': np.mean(timing_instabilities) if timing_instabilities else 0,
            'max_cv_interval': np.max(timing_instabilities) if timing_instabilities else 0,
            'is_significant': np.mean(timing_instabilities) > 0.1 if timing_instabilities else False
        }
        
        # ネットワーク変動性
        network_cvs = []
        for exp_name, exp_network in self.network_analysis.items():
            for csv_name, network_data in exp_network.items():
                if network_data['cv_response_time'] != np.inf:
                    network_cvs.append(network_data['cv_response_time'])
        
        causes['network_variability'] = {
            'mean_cv_response_time': np.mean(network_cvs) if network_cvs else 0,
            'max_cv_response_time': np.max(network_cvs) if network_cvs else 0,
            'is_significant': np.mean(network_cvs) > 0.5 if network_cvs else False
        }
        
        # 実験間の一貫性
        experiment_throughputs = []
        experiment_latencies = []
        
        for exp_name, exp_data in self.experiment_data.items():
            exp_throughputs = []
            exp_latencies = []
            
            for csv_name, df in exp_data.items():
                if len(df) > 0:
                    response_times = df['response_time'] / 1000
                    exp_latencies.append(response_times.mean())
                    
                    # スループット計算
                    timestamps = df['timestamp']
                    duration = (timestamps.max() - timestamps.min()) / 1e9
                    if duration > 0:
                        throughput = len(df) / duration
                        exp_throughputs.append(throughput)
            
            if exp_throughputs:
                experiment_throughputs.append(np.mean(exp_throughputs))
            if exp_latencies:
                experiment_latencies.append(np.mean(exp_latencies))
        
        causes['experiment_consistency'] = {
            'throughput_cv': np.std(experiment_throughputs) / np.mean(experiment_throughputs) if experiment_throughputs and np.mean(experiment_throughputs) > 0 else 0,
            'latency_cv': np.std(experiment_latencies) / np.mean(experiment_latencies) if experiment_latencies and np.mean(experiment_latencies) > 0 else 0,
            'is_significant': (np.std(experiment_throughputs) / np.mean(experiment_throughputs) > 0.3) if experiment_throughputs and np.mean(experiment_throughputs) > 0 else False
        }
        
        self.variance_causes = causes
        print("✅ ばらつき原因の特定完了")
        
    def generate_detailed_report(self):
        """詳細なばらつき原因レポートを生成"""
        print("\n📄 詳細ばらつき原因レポートを生成中...")
        
        # レポートディレクトリ作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = f"logs/detailed_variance_cause_analysis_{timestamp}"
        os.makedirs(report_dir, exist_ok=True)
        
        # レポート内容
        report_content = []
        report_content.append("=" * 80)
        report_content.append("詳細ばらつき原因分析レポート")
        report_content.append("=" * 80)
        report_content.append(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_content.append("")
        
        # 外れ値の影響
        report_content.append("🔍 外れ値の影響分析")
        report_content.append("-" * 40)
        outlier_impact = self.variance_causes['outlier_impact']
        report_content.append(f"• 総外れ値数: {outlier_impact['total_outliers']:,}")
        report_content.append(f"• 総リクエスト数: {outlier_impact['total_requests']:,}")
        report_content.append(f"• 外れ値率: {outlier_impact['outlier_percentage']:.2f}%")
        report_content.append(f"• 影響度: {'高' if outlier_impact['is_significant'] else '低'}")
        report_content.append("")
        
        # タイミングの不安定性
        report_content.append("⏰ タイミングの不安定性分析")
        report_content.append("-" * 40)
        timing_instability = self.variance_causes['timing_instability']
        report_content.append(f"• 平均間隔変動係数: {timing_instability['mean_cv_interval']:.3f}")
        report_content.append(f"• 最大間隔変動係数: {timing_instability['max_cv_interval']:.3f}")
        report_content.append(f"• 不安定性: {'高' if timing_instability['is_significant'] else '低'}")
        report_content.append("")
        
        # ネットワーク変動性
        report_content.append("📡 ネットワーク変動性分析")
        report_content.append("-" * 40)
        network_variability = self.variance_causes['network_variability']
        report_content.append(f"• 平均レスポンス時間変動係数: {network_variability['mean_cv_response_time']:.3f}")
        report_content.append(f"• 最大レスポンス時間変動係数: {network_variability['max_cv_response_time']:.3f}")
        report_content.append(f"• 変動性: {'高' if network_variability['is_significant'] else '低'}")
        report_content.append("")
        
        # 実験間の一貫性
        report_content.append("🧪 実験間の一貫性分析")
        report_content.append("-" * 40)
        experiment_consistency = self.variance_causes['experiment_consistency']
        report_content.append(f"• スループット変動係数: {experiment_consistency['throughput_cv']:.3f}")
        report_content.append(f"• レイテンシー変動係数: {experiment_consistency['latency_cv']:.3f}")
        report_content.append(f"• 一貫性: {'低' if experiment_consistency['is_significant'] else '高'}")
        report_content.append("")
        
        # 主要な原因の特定
        report_content.append("🎯 主要なばらつき原因の特定")
        report_content.append("-" * 40)
        
        significant_causes = []
        if outlier_impact['is_significant']:
            significant_causes.append(f"外れ値の影響 ({outlier_impact['outlier_percentage']:.2f}%)")
        if timing_instability['is_significant']:
            significant_causes.append(f"タイミングの不安定性 (CV: {timing_instability['mean_cv_interval']:.3f})")
        if network_variability['is_significant']:
            significant_causes.append(f"ネットワーク変動性 (CV: {network_variability['mean_cv_response_time']:.3f})")
        if experiment_consistency['is_significant']:
            significant_causes.append(f"実験間の不整合 (スループットCV: {experiment_consistency['throughput_cv']:.3f})")
        
        if significant_causes:
            report_content.append("⚠️ 検出された主要な原因:")
            for i, cause in enumerate(significant_causes, 1):
                report_content.append(f"  {i}. {cause}")
        else:
            report_content.append("✅ 主要な原因は検出されませんでした")
        report_content.append("")
        
        # 推奨対策
        report_content.append("💡 推奨対策")
        report_content.append("-" * 40)
        
        recommendations = []
        
        if outlier_impact['is_significant']:
            recommendations.append("• 外れ値の除去または統計的フィルタリングの実装")
            recommendations.append("• システムリソースの安定化")
        
        if timing_instability['is_significant']:
            recommendations.append("• ベンチマーク実行の同期化")
            recommendations.append("• システム負荷の制御")
        
        if network_variability['is_significant']:
            recommendations.append("• ネットワーク条件の一貫性確保")
            recommendations.append("• ネットワークエミュレーションの安定化")
        
        if experiment_consistency['is_significant']:
            recommendations.append("• 実験環境の標準化")
            recommendations.append("• 測定回数の増加")
        
        if recommendations:
            for rec in recommendations:
                report_content.append(rec)
        else:
            report_content.append("• 現在の設定で十分な安定性が確保されています")
        
        report_content.append("")
        report_content.append("=" * 80)
        
        # レポート保存
        report_path = os.path.join(report_dir, "detailed_variance_cause_report.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_content))
        
        print(f"✅ レポート保存完了: {report_path}")
        
        # 詳細グラフを生成
        self.generate_detailed_plots(report_dir)
        
        return report_dir
        
    def generate_detailed_plots(self, report_dir):
        """詳細な分析グラフを生成"""
        print("📊 詳細分析グラフを生成中...")
        
        # 1. 外れ値分布
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('詳細ばらつき原因分析', fontsize=16, fontweight='bold')
        
        # 外れ値の分布
        ax1 = axes[0, 0]
        outlier_percentages = []
        experiment_names = []
        
        for exp_name, exp_outliers in self.outlier_analysis.items():
            for csv_name, outlier_data in exp_outliers.items():
                outlier_percentages.append(outlier_data['outlier_percentage_3sigma'])
                experiment_names.append(f"{exp_name[-8:]}_{csv_name[:10]}")
        
        if outlier_percentages:
            ax1.bar(range(len(outlier_percentages)), outlier_percentages)
            ax1.set_title('外れ値率の分布')
            ax1.set_ylabel('外れ値率 (%)')
            ax1.tick_params(axis='x', rotation=45)
        
        # レスポンス時間の分布
        ax2 = axes[0, 1]
        all_response_times = []
        all_protocols = []
        
        for exp_name, exp_data in self.experiment_data.items():
            for csv_name, df in exp_data.items():
                if len(df) > 0:
                    response_times = df['response_time'] / 1000
                    all_response_times.extend(response_times.tolist())
                    
                    if 'h2_' in csv_name:
                        all_protocols.extend(['HTTP/2'] * len(response_times))
                    elif 'h3_' in csv_name:
                        all_protocols.extend(['HTTP/3'] * len(response_times))
        
        if all_response_times:
            response_df = pd.DataFrame({
                'response_time': all_response_times,
                'protocol': all_protocols
            })
            sns.histplot(data=response_df, x='response_time', hue='protocol', bins=50, ax=ax2)
            ax2.set_title('レスポンス時間分布')
            ax2.set_xlabel('レスポンス時間 (ms)')
        
        # ネットワーク条件別の変動
        ax3 = axes[1, 0]
        network_cvs = []
        network_conditions = []
        
        for exp_name, exp_network in self.network_analysis.items():
            for csv_name, network_data in exp_network.items():
                if network_data['cv_response_time'] != np.inf:
                    network_cvs.append(network_data['cv_response_time'])
                    network_conditions.append(network_data['delay_ms'])
        
        if network_cvs:
            ax3.scatter(network_conditions, network_cvs, alpha=0.6)
            ax3.set_title('ネットワーク遅延 vs 変動係数')
            ax3.set_xlabel('ネットワーク遅延 (ms)')
            ax3.set_ylabel('レスポンス時間変動係数')
        
        # 実験間の一貫性
        ax4 = axes[1, 1]
        experiment_cvs = []
        exp_names = []
        
        for exp_name, exp_data in self.experiment_data.items():
            exp_response_times = []
            for csv_name, df in exp_data.items():
                if len(df) > 0:
                    response_times = df['response_time'] / 1000
                    exp_response_times.extend(response_times.tolist())
            
            if exp_response_times:
                cv = np.std(exp_response_times) / np.mean(exp_response_times)
                experiment_cvs.append(cv)
                exp_names.append(exp_name[-8:])
        
        if experiment_cvs:
            ax4.bar(exp_names, experiment_cvs)
            ax4.set_title('実験間の一貫性')
            ax4.set_ylabel('変動係数')
            ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plot_path = os.path.join(report_dir, "detailed_variance_analysis.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ グラフ保存完了: {plot_path}")
        
    def run_analysis(self):
        """完全な詳細ばらつき原因分析を実行"""
        print("🚀 詳細ばらつき原因分析を開始...")
        
        self.load_experiment_data()
        self.analyze_outliers()
        self.analyze_timing_patterns()
        self.analyze_network_impact()
        self.identify_variance_causes()
        report_dir = self.generate_detailed_report()
        
        print(f"\n✅ 詳細ばらつき原因分析完了！")
        print(f"📁 結果保存先: {report_dir}")
        
        return report_dir

if __name__ == "__main__":
    analyzer = DetailedVarianceCauseAnalyzer()
    analyzer.run_analysis() 