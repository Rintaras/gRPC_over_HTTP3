#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5回の実験結果を統合分析するスクリプト
HTTP/2 vs HTTP/3 パフォーマンス比較の再現性と統計的安定性を評価
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
import matplotlib.font_manager as fm
import matplotlib as mpl

japanese_fonts = [
    'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', 'Meiryo', 
    'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP', 
    'Source Han Sans JP', 'Noto Sans JP', 'M PLUS 1p', 'Kosugi Maru',
    'Hiragino Maru Gothic ProN', 'Yu Gothic UI', 'MS Gothic', 'MS Mincho'
]

available_fonts = [f.name for f in fm.fontManager.ttflist]
font_found = False
selected_font = None

for font in japanese_fonts:
    if font in available_fonts:
        selected_font = font
        font_found = True
        print(f"✅ 日本語フォント設定成功: {font}")
        break

if font_found:
    font_family = [selected_font, 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
    plt.rcParams.update({
        'font.family': font_family,
        'font.sans-serif': font_family,
        'axes.unicode_minus': False,
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9
    })
    mpl.rcParams.update({
        'font.family': font_family,
        'font.sans-serif': font_family,
        'axes.unicode_minus': False
    })
else:
    fallback_fonts = ['DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
    plt.rcParams.update({
        'font.family': fallback_fonts,
        'font.sans-serif': fallback_fonts,
        'axes.unicode_minus': False,
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9
    })
    mpl.rcParams.update({
        'font.family': fallback_fonts,
        'font.sans-serif': fallback_fonts,
        'axes.unicode_minus': False
    })
    print("⚠️ 日本語フォントが見つかりません。フォールバック設定を使用します。")

class FiveExperimentAnalyzer:
    def __init__(self, logs_dir="logs"):
        self.logs_dir = Path(logs_dir)
        self.experiments = []
        self.consolidated_data = []
        
    def find_japanese_benchmark_experiments(self):
        """最新の5回の日本語ベンチマーク実験を検索"""
        japanese_dirs = []
        for item in self.logs_dir.iterdir():
            if item.is_dir() and item.name.startswith('japanese_benchmark_'):
                japanese_dirs.append(item)
        
        # 最新の5つを取得
        japanese_dirs.sort(key=lambda x: x.name, reverse=True)
        return japanese_dirs[:5]
    
    def parse_summary_file(self, summary_file):
        """サマリーファイルを解析"""
        with open(summary_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 実験時刻を抽出
        time_match = re.search(r'Generated Time: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', content)
        experiment_time = time_match.group(1) if time_match else "Unknown"
        
        # 主要な指標を抽出
        h3_advantage_match = re.search(r'HTTP/3 Advantage Cases: (\d+)/(\d+) Cases', content)
        h2_advantage_match = re.search(r'HTTP/2 Advantage Cases: (\d+)/(\d+) Cases', content)
        
        h3_advantage = int(h3_advantage_match.group(1)) if h3_advantage_match else 0
        total_cases = int(h3_advantage_match.group(2)) if h3_advantage_match else 0
        
        # 平均性能差を抽出
        throughput_match = re.search(r'Average Throughput Advantage: ([+-]?\d+\.?\d*)%', content)
        latency_match = re.search(r'Average Latency Advantage: ([+-]?\d+\.?\d*)%', content)
        connection_match = re.search(r'Average Connection Time Advantage: ([+-]?\d+\.?\d*)%', content)
        
        throughput_adv = float(throughput_match.group(1)) if throughput_match else 0.0
        latency_adv = float(latency_match.group(1)) if latency_match else 0.0
        connection_adv = float(connection_match.group(1)) if connection_match else 0.0
        
        # 最大性能差を抽出
        max_throughput_match = re.search(r'Maximum Throughput Advantage: ([+-]?\d+\.?\d*)%', content)
        max_throughput = float(max_throughput_match.group(1)) if max_throughput_match else 0.0
        
        # HTTP/3優位条件を抽出
        h3_conditions = []
        for line in content.split('\n'):
            if 'Delay,' in line and 'Loss →' in line:
                condition_match = re.search(r'(\d+)ms Delay, (\d+)Mbps Bandwidth, (\d+\.?\d*)% Loss → ([+-]?\d+\.?\d*)%', line)
                if condition_match:
                    h3_conditions.append({
                        'delay': int(condition_match.group(1)),
                        'bandwidth': int(condition_match.group(2)),
                        'loss': float(condition_match.group(3)),
                        'advantage': float(condition_match.group(4))
                    })
        
        return {
            'experiment_time': experiment_time,
            'h3_advantage_cases': h3_advantage,
            'total_cases': total_cases,
            'h3_advantage_ratio': h3_advantage / total_cases if total_cases > 0 else 0,
            'avg_throughput_advantage': throughput_adv,
            'avg_latency_advantage': latency_adv,
            'avg_connection_advantage': connection_adv,
            'max_throughput_advantage': max_throughput,
            'h3_advantage_conditions': h3_conditions
        }
    
    def load_experiment_data(self):
        """実験データを読み込み"""
        experiment_dirs = self.find_japanese_benchmark_experiments()
        
        print(f"📊 検出された実験数: {len(experiment_dirs)}")
        
        for i, exp_dir in enumerate(experiment_dirs, 1):
            print(f"🔍 実験 {i}: {exp_dir.name}")
            
            summary_file = exp_dir / "performance_reversal_summary.txt"
            if summary_file.exists():
                exp_data = self.parse_summary_file(summary_file)
                exp_data['experiment_id'] = i
                exp_data['experiment_dir'] = exp_dir.name
                self.experiments.append(exp_data)
            else:
                print(f"⚠️ サマリーファイルが見つかりません: {summary_file}")
        
        print(f"✅ 読み込み完了: {len(self.experiments)} 実験")
    
    def analyze_consistency(self):
        """実験結果の一貫性を分析"""
        if not self.experiments:
            print("❌ 実験データがありません")
            return
        
        print("\n" + "="*80)
        print("📈 5回実験結果の一貫性分析")
        print("="*80)
        
        # 基本統計
        df = pd.DataFrame(self.experiments)
        
        print(f"\n📊 実験概要:")
        print(f"• 実験期間: {df['experiment_time'].min()} 〜 {df['experiment_time'].max()}")
        print(f"• 総実験数: {len(df)}")
        
        print(f"\n🎯 HTTP/3優位ケース分析:")
        print(f"• 平均優位ケース数: {df['h3_advantage_cases'].mean():.1f}/{df['total_cases'].iloc[0]}")
        print(f"• 優位率の範囲: {df['h3_advantage_ratio'].min():.1%} 〜 {df['h3_advantage_ratio'].max():.1%}")
        print(f"• 標準偏差: {df['h3_advantage_ratio'].std():.1%}")
        
        print(f"\n⚡ スループット性能差分析:")
        print(f"• 平均: {df['avg_throughput_advantage'].mean():.1f}%")
        print(f"• 範囲: {df['avg_throughput_advantage'].min():.1f}% 〜 {df['avg_throughput_advantage'].max():.1f}%")
        print(f"• 標準偏差: {df['avg_throughput_advantage'].std():.1f}%")
        
        print(f"\n⏱️ レイテンシー性能差分析:")
        print(f"• 平均: {df['avg_latency_advantage'].mean():.1f}%")
        print(f"• 範囲: {df['avg_latency_advantage'].min():.1f}% 〜 {df['avg_latency_advantage'].max():.1f}%")
        print(f"• 標準偏差: {df['avg_latency_advantage'].std():.1f}%")
        
        print(f"\n🔗 接続時間性能差分析:")
        print(f"• 平均: {df['avg_connection_advantage'].mean():.1f}%")
        print(f"• 範囲: {df['avg_connection_advantage'].min():.1f}% 〜 {df['avg_connection_advantage'].max():.1f}%")
        print(f"• 標準偏差: {df['avg_connection_advantage'].std():.1f}%")
        
        # 一貫性評価
        print(f"\n🔍 一貫性評価:")
        
        # スループットの変動係数
        throughput_cv = abs(df['avg_throughput_advantage'].std() / df['avg_throughput_advantage'].mean()) if df['avg_throughput_advantage'].mean() != 0 else float('inf')
        print(f"• スループット変動係数: {throughput_cv:.3f} ({'高安定' if throughput_cv < 0.1 else '中安定' if throughput_cv < 0.3 else '低安定'})")
        
        # HTTP/3優位の一貫性
        h3_consistent = df['h3_advantage_cases'].std() == 0
        print(f"• HTTP/3優位ケース一貫性: {'✅ 完全一貫' if h3_consistent else '⚠️ 変動あり'}")
        
        # 最大性能差の一貫性
        max_throughput_cv = abs(df['max_throughput_advantage'].std() / df['max_throughput_advantage'].mean()) if df['max_throughput_advantage'].mean() != 0 else float('inf')
        print(f"• 最大性能差変動係数: {max_throughput_cv:.3f}")
        
        return df
    
    def analyze_network_conditions_impact(self):
        """ネットワーク条件の影響を分析"""
        print(f"\n🌐 ネットワーク条件影響分析:")
        
        # 各実験のHTTP/3優位条件を集計
        all_conditions = []
        for exp in self.experiments:
            for condition in exp['h3_advantage_conditions']:
                condition['experiment_id'] = exp['experiment_id']
                all_conditions.append(condition)
        
        if not all_conditions:
            print("• HTTP/3優位条件: 検出されませんでした")
            return
        
        conditions_df = pd.DataFrame(all_conditions)
        
        print(f"• HTTP/3優位条件総数: {len(conditions_df)}")
        print(f"• 平均性能向上: {conditions_df['advantage'].mean():.1f}%")
        print(f"• 最大性能向上: {conditions_df['advantage'].max():.1f}%")
        
        # 遅延条件別分析
        delay_groups = conditions_df.groupby('delay')
        print(f"\n📊 遅延条件別分析:")
        for delay, group in delay_groups:
            print(f"• {delay}ms遅延: {len(group)}回検出, 平均性能向上: {group['advantage'].mean():.1f}%")
        
        return conditions_df
    
    def generate_consistency_graphs(self, df):
        """一貫性分析グラフを生成"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('5回実験結果の一貫性分析', fontsize=16, fontweight='bold')
        
        # 1. HTTP/3優位ケース数の推移
        ax1 = axes[0, 0]
        ax1.plot(df['experiment_id'], df['h3_advantage_cases'], 'bo-', linewidth=2, markersize=8)
        ax1.set_xlabel('実験回数')
        ax1.set_ylabel('HTTP/3優位ケース数')
        ax1.set_title('HTTP/3優位ケース数の推移')
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks(df['experiment_id'])
        
        # 2. 平均スループット性能差の推移
        ax2 = axes[0, 1]
        ax2.plot(df['experiment_id'], df['avg_throughput_advantage'], 'ro-', linewidth=2, markersize=8)
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax2.set_xlabel('実験回数')
        ax2.set_ylabel('平均スループット性能差 (%)')
        ax2.set_title('平均スループット性能差の推移')
        ax2.grid(True, alpha=0.3)
        ax2.set_xticks(df['experiment_id'])
        
        # 3. 性能差の分布（箱ひげ図）
        ax3 = axes[1, 0]
        performance_metrics = ['avg_throughput_advantage', 'avg_latency_advantage', 'avg_connection_advantage']
        labels = ['スループット', 'レイテンシー', '接続時間']
        
        data_for_box = [df[metric] for metric in performance_metrics]
        bp = ax3.boxplot(data_for_box, labels=labels, patch_artist=True)
        
        # 色分け
        colors = ['lightblue', 'lightcoral', 'lightgreen']
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
        
        ax3.set_ylabel('性能差 (%)')
        ax3.set_title('性能差の分布')
        ax3.grid(True, alpha=0.3)
        ax3.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        
        # 4. 最大性能差の推移
        ax4 = axes[1, 1]
        ax4.plot(df['experiment_id'], df['max_throughput_advantage'], 'go-', linewidth=2, markersize=8)
        ax4.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax4.set_xlabel('実験回数')
        ax4.set_ylabel('最大スループット性能差 (%)')
        ax4.set_title('最大スループット性能差の推移')
        ax4.grid(True, alpha=0.3)
        ax4.set_xticks(df['experiment_id'])
        
        plt.tight_layout()
        
        # 保存
        output_dir = Path("logs") / f"five_experiment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir.mkdir(exist_ok=True)
        
        plt.savefig(output_dir / "consistency_analysis.png", dpi=300, bbox_inches='tight')
        print(f"📊 一貫性分析グラフ保存: {output_dir / 'consistency_analysis.png'}")
        
        return output_dir
    
    def generate_detailed_report(self, df, conditions_df, output_dir):
        """詳細レポートを生成"""
        report_file = output_dir / "five_experiment_analysis_report.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("5回実験結果統合分析レポート\n")
            f.write("="*80 + "\n")
            f.write(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("📊 実験概要\n")
            f.write("-" * 40 + "\n")
            f.write(f"• 実験期間: {df['experiment_time'].min()} 〜 {df['experiment_time'].max()}\n")
            f.write(f"• 総実験数: {len(df)}\n")
            f.write(f"• 実験間隔: 約{self._calculate_interval(df)}分\n\n")
            
            f.write("🎯 主要発見事項\n")
            f.write("-" * 40 + "\n")
            
            # HTTP/3優位の一貫性
            h3_advantage_std = df['h3_advantage_cases'].std()
            if h3_advantage_std == 0:
                f.write("• HTTP/3優位ケース: 完全に一貫した結果\n")
            else:
                f.write(f"• HTTP/3優位ケース: 変動あり (標準偏差: {h3_advantage_std:.1f})\n")
            
            # スループット性能の安定性
            throughput_cv = abs(df['avg_throughput_advantage'].std() / df['avg_throughput_advantage'].mean()) if df['avg_throughput_advantage'].mean() != 0 else float('inf')
            f.write(f"• スループット性能安定性: 変動係数 {throughput_cv:.3f}\n")
            
            # 最大性能差の傾向
            max_throughput_trend = "向上" if df['max_throughput_advantage'].iloc[-1] > df['max_throughput_advantage'].iloc[0] else "低下"
            f.write(f"• 最大性能差傾向: {max_throughput_trend}\n\n")
            
            f.write("📈 統計的安定性評価\n")
            f.write("-" * 40 + "\n")
            
            metrics = [
                ('avg_throughput_advantage', 'スループット'),
                ('avg_latency_advantage', 'レイテンシー'),
                ('avg_connection_advantage', '接続時間')
            ]
            
            for metric, name in metrics:
                mean_val = df[metric].mean()
                std_val = df[metric].std()
                cv = abs(std_val / mean_val) if mean_val != 0 else float('inf')
                
                stability = "高安定" if cv < 0.1 else "中安定" if cv < 0.3 else "低安定"
                f.write(f"• {name}: 平均{mean_val:.1f}%, 標準偏差{std_val:.1f}%, 変動係数{cv:.3f} ({stability})\n")
            
            f.write("\n🔍 実用的な推奨事項\n")
            f.write("-" * 40 + "\n")
            
            # 一貫性に基づく推奨
            if h3_advantage_std == 0:
                f.write("• 実験結果は高い再現性を示している\n")
                f.write("• ネットワーク条件に応じたプロトコル選択が可能\n")
            else:
                f.write("• 実験結果に変動があるため、複数回測定を推奨\n")
                f.write("• 統計的検定による有意性確認が必要\n")
            
            # 性能差の実用性
            avg_throughput = df['avg_throughput_advantage'].mean()
            if abs(avg_throughput) < 5:
                f.write("• 平均的な性能差は5%未満で、実用上は同等\n")
            else:
                f.write(f"• 平均的な性能差は{abs(avg_throughput):.1f}%で、実用的な差がある\n")
            
            f.write("\n📁 生成ファイル\n")
            f.write("-" * 40 + "\n")
            f.write("• consistency_analysis.png - 一貫性分析グラフ\n")
            f.write("• five_experiment_analysis_report.txt - このレポート\n")
        
        print(f"📄 詳細レポート保存: {report_file}")
    
    def _calculate_interval(self, df):
        """実験間隔を計算"""
        if len(df) < 2:
            return 0
        
        times = pd.to_datetime(df['experiment_time'])
        intervals = []
        for i in range(1, len(times)):
            interval = (times.iloc[i] - times.iloc[i-1]).total_seconds() / 60
            intervals.append(interval)
        
        return sum(intervals) / len(intervals)
    
    def run_analysis(self):
        """完全な分析を実行"""
        print("🚀 5回実験結果統合分析を開始...")
        
        # データ読み込み
        self.load_experiment_data()
        
        if not self.experiments:
            print("❌ 分析可能な実験データが見つかりません")
            return
        
        # 一貫性分析
        df = self.analyze_consistency()
        
        # ネットワーク条件影響分析
        conditions_df = self.analyze_network_conditions_impact()
        
        # グラフ生成
        output_dir = self.generate_consistency_graphs(df)
        
        # 詳細レポート生成
        self.generate_detailed_report(df, conditions_df, output_dir)
        
        print(f"\n✅ 分析完了！結果は {output_dir} に保存されました")

if __name__ == "__main__":
    analyzer = FiveExperimentAnalyzer()
    analyzer.run_analysis() 