#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データのばらつき原因分析スクリプト v2
CSVファイルの実際の形式に対応
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

class VarianceAnalyzerV2:
    def __init__(self):
        self.experiment_data = {}
        self.variance_sources = {}
        self.analysis_results = {}
        
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
                    # カラム名なしのCSVファイルを読み込み
                    df = pd.read_csv(csv_path, header=None)
                    # カラム名を設定（タイムスタンプ、ステータスコード、レスポンス時間）
                    df.columns = ['timestamp', 'status_code', 'response_time']
                    exp_data[csv_file] = df
                    print(f"  ✅ {csv_file}: {len(df)} 行")
                except Exception as e:
                    print(f"  ❌ {csv_file}: 読み込みエラー - {e}")
            
            self.experiment_data[exp_dir] = exp_data
        
        print(f"✅ データ読み込み完了: {len(self.experiment_data)} 実験")
        
    def analyze_performance_variance(self):
        """性能のばらつきを分析"""
        print("\n📈 性能ばらつき分析を開始...")
        
        variance_data = {
            'throughput': [],
            'latency': [],
            'success_rate': [],
            'experiment': [],
            'protocol': [],
            'network_condition': []
        }
        
        for exp_name, exp_data in self.experiment_data.items():
            for csv_name, df in exp_data.items():
                if len(df) == 0:
                    continue
                
                # プロトコルとネットワーク条件を抽出
                if 'h2_' in csv_name:
                    protocol = 'HTTP/2'
                elif 'h3_' in csv_name:
                    protocol = 'HTTP/3'
                else:
                    continue
                
                # ネットワーク条件を抽出
                network_match = re.search(r'(\d+)ms_(\d+)pct', csv_name)
                if network_match:
                    delay = int(network_match.group(1))
                    loss = int(network_match.group(2))
                    network_condition = f"{delay}ms_{loss}%"
                else:
                    network_condition = "unknown"
                
                # 性能指標を抽出
                try:
                    # レスポンス時間（マイクロ秒からミリ秒に変換）
                    latency = df['response_time'].mean() / 1000  # μs to ms
                    
                    # 成功率
                    success_count = len(df[df['status_code'] == 200])
                    total_count = len(df)
                    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
                    
                    # スループット（成功したリクエスト数 / 総時間）
                    if len(df) > 1:
                        # 最初と最後のタイムスタンプから時間を計算
                        start_time = df['timestamp'].min()
                        end_time = df['timestamp'].max()
                        duration_seconds = (end_time - start_time) / 1e9  # ナノ秒から秒に変換
                        if duration_seconds > 0:
                            throughput = success_count / duration_seconds
                        else:
                            throughput = np.nan
                    else:
                        throughput = np.nan
                    
                    variance_data['throughput'].append(throughput)
                    variance_data['latency'].append(latency)
                    variance_data['success_rate'].append(success_rate)
                    variance_data['experiment'].append(exp_name)
                    variance_data['protocol'].append(protocol)
                    variance_data['network_condition'].append(network_condition)
                    
                except Exception as e:
                    print(f"  ⚠️ データ抽出エラー ({csv_name}): {e}")
        
        self.variance_df = pd.DataFrame(variance_data)
        print(f"✅ 性能データ抽出完了: {len(self.variance_df)} データポイント")
        
        # データの概要を表示
        print("\n📊 データ概要:")
        print(f"  スループット: {len(self.variance_df[self.variance_df['throughput'].notna()])} データポイント")
        print(f"  レイテンシー: {len(self.variance_df[self.variance_df['latency'].notna()])} データポイント")
        print(f"  成功率: {len(self.variance_df[self.variance_df['success_rate'].notna()])} データポイント")
        
    def identify_variance_sources(self):
        """ばらつきの原因を特定"""
        print("\n🔍 ばらつき原因の特定を開始...")
        
        if len(self.variance_df) == 0:
            print("❌ 分析可能なデータがありません")
            return
        
        # 各指標の変動係数を計算
        variance_sources = {}
        
        for metric in ['throughput', 'latency', 'success_rate']:
            metric_data = self.variance_df[metric].dropna()
            if len(metric_data) > 0:
                cv = metric_data.std() / metric_data.mean() if metric_data.mean() != 0 else np.inf
                variance_sources[metric] = {
                    'mean': metric_data.mean(),
                    'std': metric_data.std(),
                    'cv': cv,
                    'min': metric_data.min(),
                    'max': metric_data.max(),
                    'range': metric_data.max() - metric_data.min()
                }
        
        # プロトコル別のばらつき
        protocol_variance = {}
        for protocol in self.variance_df['protocol'].unique():
            protocol_data = self.variance_df[self.variance_df['protocol'] == protocol]
            for metric in ['throughput', 'latency', 'success_rate']:
                metric_data = protocol_data[metric].dropna()
                if len(metric_data) > 0:
                    cv = metric_data.std() / metric_data.mean() if metric_data.mean() != 0 else np.inf
                    protocol_variance[f"{protocol}_{metric}"] = cv
        
        # ネットワーク条件別のばらつき
        network_variance = {}
        for condition in self.variance_df['network_condition'].unique():
            condition_data = self.variance_df[self.variance_df['network_condition'] == condition]
            for metric in ['throughput', 'latency', 'success_rate']:
                metric_data = condition_data[metric].dropna()
                if len(metric_data) > 0:
                    cv = metric_data.std() / metric_data.mean() if metric_data.mean() != 0 else np.inf
                    network_variance[f"{condition}_{metric}"] = cv
        
        # 実験間のばらつき
        experiment_variance = {}
        for exp in self.variance_df['experiment'].unique():
            exp_data = self.variance_df[self.variance_df['experiment'] == exp]
            for metric in ['throughput', 'latency', 'success_rate']:
                metric_data = exp_data[metric].dropna()
                if len(metric_data) > 0:
                    cv = metric_data.std() / metric_data.mean() if metric_data.mean() != 0 else np.inf
                    experiment_variance[f"{exp}_{metric}"] = cv
        
        self.variance_sources = {
            'overall': variance_sources,
            'protocol': protocol_variance,
            'network': network_variance,
            'experiment': experiment_variance
        }
        
        print("✅ ばらつき原因の特定完了")
        
    def generate_variance_report(self):
        """ばらつき分析レポートを生成"""
        print("\n📄 ばらつき分析レポートを生成中...")
        
        # レポートディレクトリ作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = f"logs/variance_analysis_v2_{timestamp}"
        os.makedirs(report_dir, exist_ok=True)
        
        # レポート内容
        report_content = []
        report_content.append("=" * 80)
        report_content.append("データばらつき原因分析レポート v2")
        report_content.append("=" * 80)
        report_content.append(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_content.append("")
        
        # 全体のばらつき状況
        report_content.append("📊 全体のばらつき状況")
        report_content.append("-" * 40)
        if 'overall' in self.variance_sources:
            for metric, stats in self.variance_sources['overall'].items():
                report_content.append(f"• {metric.upper()}:")
                report_content.append(f"  - 平均: {stats['mean']:.2f}")
                report_content.append(f"  - 標準偏差: {stats['std']:.2f}")
                report_content.append(f"  - 変動係数: {stats['cv']:.3f}")
                report_content.append(f"  - 範囲: {stats['min']:.2f} 〜 {stats['max']:.2f}")
                report_content.append("")
        
        # プロトコル別のばらつき
        report_content.append("🌐 プロトコル別のばらつき")
        report_content.append("-" * 40)
        if 'protocol' in self.variance_sources:
            for key, cv in self.variance_sources['protocol'].items():
                report_content.append(f"• {key}: 変動係数 {cv:.3f}")
            report_content.append("")
        
        # ネットワーク条件別のばらつき
        report_content.append("📡 ネットワーク条件別のばらつき")
        report_content.append("-" * 40)
        if 'network' in self.variance_sources:
            for key, cv in self.variance_sources['network'].items():
                report_content.append(f"• {key}: 変動係数 {cv:.3f}")
            report_content.append("")
        
        # 実験間のばらつき
        report_content.append("🧪 実験間のばらつき")
        report_content.append("-" * 40)
        if 'experiment' in self.variance_sources:
            for key, cv in self.variance_sources['experiment'].items():
                report_content.append(f"• {key}: 変動係数 {cv:.3f}")
            report_content.append("")
        
        # ばらつきの原因分析
        report_content.append("🔍 ばらつきの原因分析")
        report_content.append("-" * 40)
        
        # 最もばらつきの大きい要因を特定
        all_cvs = []
        if 'protocol' in self.variance_sources:
            all_cvs.extend(self.variance_sources['protocol'].items())
        if 'network' in self.variance_sources:
            all_cvs.extend(self.variance_sources['network'].items())
        if 'experiment' in self.variance_sources:
            all_cvs.extend(self.variance_sources['experiment'].items())
        
        if all_cvs:
            # 変動係数でソート
            all_cvs.sort(key=lambda x: x[1], reverse=True)
            
            report_content.append("📈 最もばらつきの大きい要因（上位5つ）:")
            for i, (factor, cv) in enumerate(all_cvs[:5]):
                report_content.append(f"  {i+1}. {factor}: {cv:.3f}")
            report_content.append("")
        
        # 推奨事項
        report_content.append("💡 推奨事項")
        report_content.append("-" * 40)
        
        # 変動係数が高い場合の対策
        high_variance_threshold = 0.5
        high_variance_factors = [item for item in all_cvs if item[1] > high_variance_threshold]
        
        if high_variance_factors:
            report_content.append("⚠️ 高いばらつきが検出されました:")
            for factor, cv in high_variance_factors:
                report_content.append(f"  • {factor}: {cv:.3f}")
            report_content.append("")
            report_content.append("🔧 対策:")
            report_content.append("  1. システムリソースの安定化")
            report_content.append("  2. ネットワーク条件の一貫性確保")
            report_content.append("  3. 測定回数の増加")
            report_content.append("  4. 外れ値の除去")
            report_content.append("  5. ベンチマークパラメータの調整")
        else:
            report_content.append("✅ ばらつきは許容範囲内です")
        
        # レポート保存
        report_path = os.path.join(report_dir, "variance_analysis_report.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_content))
        
        print(f"✅ レポート保存完了: {report_path}")
        
        # ばらつき可視化グラフを生成
        self.generate_variance_plots(report_dir)
        
        return report_dir
        
    def generate_variance_plots(self, report_dir):
        """ばらつきの可視化グラフを生成"""
        print("📊 ばらつき可視化グラフを生成中...")
        
        if len(self.variance_df) == 0:
            print("❌ グラフ生成に必要なデータがありません")
            return
        
        # 1. プロトコル別のばらつき比較
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('データばらつき分析 v2', fontsize=16, fontweight='bold')
        
        # スループットのばらつき
        ax1 = axes[0, 0]
        throughput_data = self.variance_df[self.variance_df['throughput'].notna()]
        if len(throughput_data) > 0:
            sns.boxplot(data=throughput_data, x='protocol', y='throughput', ax=ax1)
            ax1.set_title('スループットのばらつき')
            ax1.set_ylabel('スループット (req/s)')
        
        # レイテンシーのばらつき
        ax2 = axes[0, 1]
        latency_data = self.variance_df[self.variance_df['latency'].notna()]
        if len(latency_data) > 0:
            sns.boxplot(data=latency_data, x='protocol', y='latency', ax=ax2)
            ax2.set_title('レイテンシーのばらつき')
            ax2.set_ylabel('レイテンシー (ms)')
        
        # ネットワーク条件別のばらつき
        ax3 = axes[1, 0]
        if len(throughput_data) > 0:
            sns.boxplot(data=throughput_data, x='network_condition', y='throughput', ax=ax3)
            ax3.set_title('ネットワーク条件別スループットばらつき')
            ax3.set_ylabel('スループット (req/s)')
            ax3.tick_params(axis='x', rotation=45)
        
        # 成功率のばらつき
        ax4 = axes[1, 1]
        success_data = self.variance_df[self.variance_df['success_rate'].notna()]
        if len(success_data) > 0:
            sns.boxplot(data=success_data, x='protocol', y='success_rate', ax=ax4)
            ax4.set_title('成功率のばらつき')
            ax4.set_ylabel('成功率 (%)')
        
        plt.tight_layout()
        plot_path = os.path.join(report_dir, "variance_analysis.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ グラフ保存完了: {plot_path}")
        
    def run_analysis(self):
        """完全なばらつき分析を実行"""
        print("🚀 データばらつき原因分析 v2 を開始...")
        
        self.load_experiment_data()
        self.analyze_performance_variance()
        self.identify_variance_sources()
        report_dir = self.generate_variance_report()
        
        print(f"\n✅ ばらつき分析完了！")
        print(f"📁 結果保存先: {report_dir}")
        
        return report_dir

if __name__ == "__main__":
    analyzer = VarianceAnalyzerV2()
    analyzer.run_analysis() 