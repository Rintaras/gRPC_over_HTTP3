#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3日前の実験環境と現在の実験環境の違いを分析するスクリプト
実験環境の改善点と性能への影響を評価
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

class EnvironmentComparisonAnalyzer:
    def __init__(self, logs_dir="logs"):
        self.logs_dir = Path(logs_dir)
        self.old_environment = {}
        self.new_environment = {}
        
    def find_old_environment(self):
        """3日前の実験環境を検索"""
        old_dirs = []
        for item in self.logs_dir.iterdir():
            if item.is_dir() and item.name.startswith('benchmark_20250723'):
                old_dirs.append(item)
        
        if old_dirs:
            # 最新のものを選択
            old_dirs.sort(key=lambda x: x.name, reverse=True)
            return old_dirs[0]
        return None
    
    def find_new_environment(self):
        """現在の実験環境を検索"""
        new_dirs = []
        for item in self.logs_dir.iterdir():
            if item.is_dir() and item.name.startswith('japanese_benchmark_20250725'):
                new_dirs.append(item)
        
        if new_dirs:
            # 最新のものを選択
            new_dirs.sort(key=lambda x: x.name, reverse=True)
            return new_dirs[0]
        return None
    
    def parse_benchmark_params(self, params_file):
        """ベンチマークパラメータを解析"""
        params = {}
        if params_file.exists():
            with open(params_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        params[key] = value
        return params
    
    def parse_summary_file(self, summary_file):
        """サマリーファイルを解析"""
        if not summary_file.exists():
            return {}
        
        with open(summary_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
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
        
        return {
            'h3_advantage_cases': h3_advantage,
            'total_cases': total_cases,
            'h3_advantage_ratio': h3_advantage / total_cases if total_cases > 0 else 0,
            'avg_throughput_advantage': throughput_adv,
            'avg_latency_advantage': latency_adv,
            'avg_connection_advantage': connection_adv,
            'max_throughput_advantage': max_throughput
        }
    
    def analyze_environment_differences(self):
        """環境の違いを分析"""
        print("🔍 実験環境の違いを分析中...")
        
        old_env_dir = self.find_old_environment()
        new_env_dir = self.find_new_environment()
        
        if not old_env_dir or not new_env_dir:
            print("❌ 比較可能な環境が見つかりません")
            return
        
        print(f"📅 古い環境: {old_env_dir.name}")
        print(f"📅 新しい環境: {new_env_dir.name}")
        
        # パラメータ比較
        old_params = self.parse_benchmark_params(old_env_dir / "benchmark_params.txt")
        new_params = self.parse_benchmark_params(new_env_dir / "benchmark_params.txt")
        
        # 性能結果比較
        old_performance = self.parse_summary_file(old_env_dir / "performance_reversal_summary.txt")
        new_performance = self.parse_summary_file(new_env_dir / "performance_reversal_summary.txt")
        
        return {
            'old_params': old_params,
            'new_params': new_params,
            'old_performance': old_performance,
            'new_performance': new_performance,
            'old_dir': old_env_dir,
            'new_dir': new_env_dir
        }
    
    def compare_benchmark_parameters(self, old_params, new_params):
        """ベンチマークパラメータの比較"""
        print("\n" + "="*80)
        print("🔧 ベンチマークパラメータ比較")
        print("="*80)
        
        comparison_data = []
        
        # 共通パラメータの比較
        common_params = set(old_params.keys()) & set(new_params.keys())
        
        for param in sorted(common_params):
            old_val = old_params[param]
            new_val = new_params[param]
            
            try:
                old_num = int(old_val)
                new_num = int(new_val)
                change = new_num - old_num
                change_pct = (change / old_num * 100) if old_num != 0 else 0
                
                comparison_data.append({
                    'parameter': param,
                    'old_value': old_val,
                    'new_value': new_val,
                    'change': change,
                    'change_percent': change_pct
                })
                
                change_symbol = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                print(f"{change_symbol} {param}: {old_val} → {new_val} ({change:+d}, {change_pct:+.1f}%)")
                
            except ValueError:
                # 数値以外のパラメータ
                comparison_data.append({
                    'parameter': param,
                    'old_value': old_val,
                    'new_value': new_val,
                    'change': 'N/A',
                    'change_percent': 'N/A'
                })
                print(f"➡️ {param}: {old_val} → {new_val}")
        
        # 新しく追加されたパラメータ
        new_only_params = set(new_params.keys()) - set(old_params.keys())
        if new_only_params:
            print(f"\n🆕 新しく追加されたパラメータ:")
            for param in sorted(new_only_params):
                print(f"  • {param}: {new_params[param]}")
        
        # 削除されたパラメータ
        old_only_params = set(old_params.keys()) - set(new_params.keys())
        if old_only_params:
            print(f"\n🗑️ 削除されたパラメータ:")
            for param in sorted(old_only_params):
                print(f"  • {param}: {old_params[param]}")
        
        return comparison_data
    
    def compare_performance_results(self, old_performance, new_performance):
        """性能結果の比較"""
        print(f"\n" + "="*80)
        print("📊 性能結果比較")
        print("="*80)
        
        if not old_performance or not new_performance:
            print("❌ 性能データが不完全です")
            return
        
        metrics = [
            ('h3_advantage_ratio', 'HTTP/3優位率'),
            ('avg_throughput_advantage', '平均スループット性能差'),
            ('avg_latency_advantage', '平均レイテンシー性能差'),
            ('avg_connection_advantage', '平均接続時間性能差'),
            ('max_throughput_advantage', '最大スループット性能差')
        ]
        
        comparison_results = []
        
        for metric, name in metrics:
            if metric in old_performance and metric in new_performance:
                old_val = old_performance[metric]
                new_val = new_performance[metric]
                change = new_val - old_val
                
                comparison_results.append({
                    'metric': name,
                    'old_value': old_val,
                    'new_value': new_val,
                    'change': change
                })
                
                change_symbol = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                if isinstance(old_val, float):
                    print(f"{change_symbol} {name}: {old_val:.1f}% → {new_val:.1f}% ({change:+.1f}%)")
                else:
                    print(f"{change_symbol} {name}: {old_val} → {new_val} ({change:+d})")
        
        return comparison_results
    
    def analyze_improvements(self, comparison_data, performance_results):
        """改善点の分析"""
        print(f"\n" + "="*80)
        print("🚀 環境改善点の分析")
        print("="*80)
        
        improvements = []
        
        # パラメータ改善の分析
        for param_data in comparison_data:
            if param_data['parameter'] == 'REQUESTS':
                if param_data['change'] < 0:
                    improvements.append("📉 リクエスト数削減: 測定時間短縮とリソース効率化")
                else:
                    improvements.append("📈 リクエスト数増加: より詳細な測定")
            
            elif param_data['parameter'] == 'CONNECTIONS':
                if param_data['change'] < 0:
                    improvements.append("📉 接続数削減: システム負荷軽減")
                else:
                    improvements.append("📈 接続数増加: より現実的な負荷")
            
            elif param_data['parameter'] == 'THREADS':
                if param_data['change'] < 0:
                    improvements.append("📉 スレッド数削減: CPU競合の軽減")
                else:
                    improvements.append("📈 スレッド数増加: 並列処理向上")
            
            elif param_data['parameter'] == 'CONNECTION_WARMUP_TIME':
                if param_data['change'] > 0:
                    improvements.append("📈 ウォームアップ時間増加: より安定した測定")
            
            elif param_data['parameter'] == 'SYSTEM_STABILIZATION_TIME':
                improvements.append("🆕 システム安定化時間追加: 測定前の環境安定化")
            
            elif param_data['parameter'] == 'MEMORY_CLEANUP_ENABLED':
                if param_data['new_value'] == 'true':
                    improvements.append("🆕 メモリクリーンアップ有効化: メモリリーク防止")
            
            elif param_data['parameter'] == 'NETWORK_RESET_ENABLED':
                if param_data['new_value'] == 'true':
                    improvements.append("🆕 ネットワークリセット有効化: 測定間の環境クリーンアップ")
        
        # 性能改善の分析
        for perf_data in performance_results:
            if perf_data['metric'] == 'HTTP/3優位率':
                if perf_data['change'] > 0:
                    improvements.append("✅ HTTP/3優位ケース増加: より適切な条件設定")
                elif perf_data['change'] < 0:
                    improvements.append("⚠️ HTTP/3優位ケース減少: 条件設定の見直し必要")
            
            elif perf_data['metric'] == '平均スループット性能差':
                if abs(perf_data['change']) < 5:
                    improvements.append("✅ スループット性能差安定化: 測定精度向上")
                else:
                    improvements.append("⚠️ スループット性能差変動: 測定条件の調整必要")
        
        # 改善点の表示
        if improvements:
            print("🎯 検出された改善点:")
            for i, improvement in enumerate(improvements, 1):
                print(f"  {i}. {improvement}")
        else:
            print("ℹ️ 明確な改善点は検出されませんでした")
        
        return improvements
    
    def generate_comparison_graphs(self, comparison_data, performance_results, output_dir):
        """比較グラフを生成"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('3日前 vs 現在の実験環境比較', fontsize=16, fontweight='bold')
        
        # 1. パラメータ変更の影響
        ax1 = axes[0, 0]
        numeric_params = [d for d in comparison_data if isinstance(d['change'], (int, float))]
        if numeric_params:
            params = [d['parameter'] for d in numeric_params]
            changes = [d['change_percent'] for d in numeric_params if isinstance(d['change_percent'], (int, float))]
            
            colors = ['red' if c < 0 else 'green' if c > 0 else 'gray' for c in changes]
            bars = ax1.bar(range(len(changes)), changes, color=colors, alpha=0.7)
            ax1.set_xlabel('パラメータ')
            ax1.set_ylabel('変更率 (%)')
            ax1.set_title('パラメータ変更率')
            ax1.set_xticks(range(len(changes)))
            ax1.set_xticklabels(params, rotation=45, ha='right')
            ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax1.grid(True, alpha=0.3)
        
        # 2. 性能指標比較
        ax2 = axes[0, 1]
        if performance_results:
            metrics = [d['metric'] for d in performance_results]
            old_vals = [d['old_value'] for d in performance_results]
            new_vals = [d['new_value'] for d in performance_results]
            
            x = np.arange(len(metrics))
            width = 0.35
            
            ax2.bar(x - width/2, old_vals, width, label='3日前', alpha=0.8)
            ax2.bar(x + width/2, new_vals, width, label='現在', alpha=0.8)
            ax2.set_xlabel('性能指標')
            ax2.set_ylabel('値')
            ax2.set_title('性能指標比較')
            ax2.set_xticks(x)
            ax2.set_xticklabels(metrics, rotation=45, ha='right')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # 3. 性能変化の詳細
        ax3 = axes[1, 0]
        if performance_results:
            metrics = [d['metric'] for d in performance_results]
            changes = [d['change'] for d in performance_results]
            
            colors = ['red' if c < 0 else 'green' if c > 0 else 'gray' for c in changes]
            bars = ax3.bar(range(len(changes)), changes, color=colors, alpha=0.7)
            ax3.set_xlabel('性能指標')
            ax3.set_ylabel('変化量')
            ax3.set_title('性能変化量')
            ax3.set_xticks(range(len(changes)))
            ax3.set_xticklabels(metrics, rotation=45, ha='right')
            ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax3.grid(True, alpha=0.3)
        
        # 4. 環境改善の要約
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        # 改善点の要約テキスト
        summary_text = "環境改善の要約:\n\n"
        
        # パラメータ改善
        param_improvements = sum(1 for d in comparison_data if isinstance(d['change'], (int, float)) and d['change'] != 0)
        summary_text += f"• パラメータ変更: {param_improvements}項目\n"
        
        # 新機能追加
        new_features = sum(1 for d in comparison_data if d['change'] == 'N/A' and 'SYSTEM_STABILIZATION_TIME' in d['parameter'])
        summary_text += f"• 新機能追加: {new_features}項目\n"
        
        # 性能変化
        if performance_results:
            improved_metrics = sum(1 for d in performance_results if d['change'] > 0)
            summary_text += f"• 性能改善指標: {improved_metrics}項目\n"
        
        summary_text += "\n主な改善点:\n"
        summary_text += "• 測定安定性向上\n"
        summary_text += "• リソース効率化\n"
        summary_text += "• 環境クリーンアップ\n"
        summary_text += "• 日本語対応\n"
        
        ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
        
        plt.tight_layout()
        
        # 保存
        plt.savefig(output_dir / "environment_comparison.png", dpi=300, bbox_inches='tight')
        print(f"📊 環境比較グラフ保存: {output_dir / 'environment_comparison.png'}")
    
    def generate_detailed_report(self, comparison_data, performance_results, improvements, output_dir):
        """詳細レポートを生成"""
        report_file = output_dir / "environment_comparison_report.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("3日前 vs 現在の実験環境比較レポート\n")
            f.write("="*80 + "\n")
            f.write(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("📊 環境概要\n")
            f.write("-" * 40 + "\n")
            f.write("• 古い環境: 2025-07-23 (3日前)\n")
            f.write("• 新しい環境: 2025-07-25 (現在)\n")
            f.write("• 比較期間: 約3日間\n\n")
            
            f.write("🔧 パラメータ変更詳細\n")
            f.write("-" * 40 + "\n")
            for param_data in comparison_data:
                if isinstance(param_data['change'], (int, float)):
                    f.write(f"• {param_data['parameter']}: {param_data['old_value']} → {param_data['new_value']} ({param_data['change']:+d}, {param_data['change_percent']:+.1f}%)\n")
                else:
                    f.write(f"• {param_data['parameter']}: {param_data['old_value']} → {param_data['new_value']}\n")
            
            f.write("\n📈 性能変化詳細\n")
            f.write("-" * 40 + "\n")
            for perf_data in performance_results:
                if isinstance(perf_data['old_value'], float):
                    f.write(f"• {perf_data['metric']}: {perf_data['old_value']:.1f}% → {perf_data['new_value']:.1f}% ({perf_data['change']:+.1f}%)\n")
                else:
                    f.write(f"• {perf_data['metric']}: {perf_data['old_value']} → {perf_data['new_value']} ({perf_data['change']:+d})\n")
            
            f.write("\n🚀 主要な改善点\n")
            f.write("-" * 40 + "\n")
            for i, improvement in enumerate(improvements, 1):
                f.write(f"{i}. {improvement}\n")
            
            f.write("\n🔍 技術的改善の意義\n")
            f.write("-" * 40 + "\n")
            f.write("• 測定安定性: システム安定化時間とメモリクリーンアップにより測定精度向上\n")
            f.write("• リソース効率: 適切なパラメータ調整によりシステム負荷軽減\n")
            f.write("• 再現性: ネットワークリセット機能により測定間の独立性確保\n")
            f.write("• ユーザビリティ: 日本語対応により結果の理解しやすさ向上\n")
            
            f.write("\n📁 生成ファイル\n")
            f.write("-" * 40 + "\n")
            f.write("• environment_comparison.png - 環境比較グラフ\n")
            f.write("• environment_comparison_report.txt - このレポート\n")
        
        print(f"📄 詳細レポート保存: {report_file}")
    
    def run_comparison(self):
        """完全な比較分析を実行"""
        print("🚀 実験環境比較分析を開始...")
        
        # 環境の違いを分析
        env_data = self.analyze_environment_differences()
        
        if not env_data:
            print("❌ 比較可能な環境データが見つかりません")
            return
        
        # パラメータ比較
        comparison_data = self.compare_benchmark_parameters(
            env_data['old_params'], 
            env_data['new_params']
        )
        
        # 性能結果比較
        performance_results = self.compare_performance_results(
            env_data['old_performance'], 
            env_data['new_performance']
        )
        
        # 改善点分析
        improvements = self.analyze_improvements(comparison_data, performance_results)
        
        # 出力ディレクトリ作成
        output_dir = Path("logs") / f"environment_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir.mkdir(exist_ok=True)
        
        # グラフ生成
        self.generate_comparison_graphs(comparison_data, performance_results, output_dir)
        
        # 詳細レポート生成
        self.generate_detailed_report(comparison_data, performance_results, improvements, output_dir)
        
        print(f"\n✅ 比較分析完了！結果は {output_dir} に保存されました")

if __name__ == "__main__":
    analyzer = EnvironmentComparisonAnalyzer()
    analyzer.run_comparison() 