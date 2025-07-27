#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
監視データ分析スクリプト
ベンチマーク実行中のシステムリソースとネットワーク監視データを分析
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

class MonitoringDataAnalyzer:
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.monitoring_data = {}
        self.analysis_results = {}
        
    def load_monitoring_data(self):
        """監視データを読み込み"""
        print("🔍 監視データを読み込み中...")
        
        # システム監視データ
        system_monitor_files = list(self.log_dir.glob("system_monitor_*.csv"))
        if system_monitor_files:
            system_file = system_monitor_files[0]
            try:
                self.monitoring_data['system'] = pd.read_csv(system_file)
                print(f"✅ システム監視データ読み込み: {len(self.monitoring_data['system'])} 行")
            except Exception as e:
                print(f"❌ システム監視データ読み込みエラー: {e}")
        
        # ネットワーク監視データ
        network_stats_file = self.log_dir / "network_stats.csv"
        if network_stats_file.exists():
            try:
                self.monitoring_data['network'] = pd.read_csv(network_stats_file)
                print(f"✅ ネットワーク監視データ読み込み: {len(self.monitoring_data['network'])} 行")
            except Exception as e:
                print(f"❌ ネットワーク監視データ読み込みエラー: {e}")
        
        # JSON監視データ
        json_monitor_files = list(self.log_dir.glob("system_monitor_*.json"))
        if json_monitor_files:
            json_file = json_monitor_files[0]
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    self.monitoring_data['json'] = json.load(f)
                print(f"✅ JSON監視データ読み込み: {len(self.monitoring_data['json'])} データポイント")
            except Exception as e:
                print(f"❌ JSON監視データ読み込みエラー: {e}")
        
        print(f"✅ 監視データ読み込み完了")
        
    def analyze_system_resources(self):
        """システムリソースの分析"""
        print("\n💻 システムリソース分析を開始...")
        
        if 'system' not in self.monitoring_data:
            print("❌ システム監視データがありません")
            return
        
        df = self.monitoring_data['system']
        
        # 基本統計
        system_stats = {
            'cpu_usage': {
                'mean': df['cpu_usage'].mean(),
                'std': df['cpu_usage'].std(),
                'max': df['cpu_usage'].max(),
                'min': df['cpu_usage'].min(),
                'cv': df['cpu_usage'].std() / df['cpu_usage'].mean() if df['cpu_usage'].mean() > 0 else 0
            },
            'memory_usage': {
                'mean': df['memory_usage'].mean(),
                'std': df['memory_usage'].std(),
                'max': df['memory_usage'].max(),
                'min': df['memory_usage'].min(),
                'cv': df['memory_usage'].std() / df['memory_usage'].mean() if df['memory_usage'].mean() > 0 else 0
            },
            'docker_containers': {
                'mean': df['docker_containers'].mean(),
                'std': df['docker_containers'].std(),
                'max': df['docker_containers'].max(),
                'min': df['docker_containers'].min(),
                'cv': df['docker_containers'].std() / df['docker_containers'].mean() if df['docker_containers'].mean() > 0 else 0
            }
        }
        
        # 異常検出
        anomalies = {
            'high_cpu': len(df[df['cpu_usage'] > 80]),
            'high_memory': len(df[df['memory_usage'] > 90]),
            'container_changes': df['docker_containers'].diff().abs().sum()
        }
        
        self.analysis_results['system'] = {
            'stats': system_stats,
            'anomalies': anomalies,
            'data': df
        }
        
        print("✅ システムリソース分析完了")
        
    def analyze_network_performance(self):
        """ネットワーク性能の分析"""
        print("\n📡 ネットワーク性能分析を開始...")
        
        if 'network' not in self.monitoring_data:
            print("❌ ネットワーク監視データがありません")
            return
        
        df = self.monitoring_data['network']
        
        # インターフェース別の統計
        interface_stats = {}
        for interface in df['interface'].unique():
            interface_data = df[df['interface'] == interface]
            interface_stats[interface] = {
                'rx_bytes_total': interface_data['rx_bytes'].sum(),
                'tx_bytes_total': interface_data['tx_bytes'].sum(),
                'rx_packets_total': interface_data['rx_packets'].sum(),
                'tx_packets_total': interface_data['tx_packets'].sum(),
                'avg_rx_rate': interface_data['rx_bytes'].mean(),
                'avg_tx_rate': interface_data['tx_bytes'].mean()
            }
        
        # ネットワーク変動性
        network_variability = {
            'rx_bytes_cv': df['rx_bytes'].std() / df['rx_bytes'].mean() if df['rx_bytes'].mean() > 0 else 0,
            'tx_bytes_cv': df['tx_bytes'].std() / df['tx_bytes'].mean() if df['tx_bytes'].mean() > 0 else 0,
            'rx_packets_cv': df['rx_packets'].std() / df['rx_packets'].mean() if df['rx_packets'].mean() > 0 else 0,
            'tx_packets_cv': df['tx_packets'].std() / df['tx_packets'].mean() if df['tx_packets'].mean() > 0 else 0
        }
        
        self.analysis_results['network'] = {
            'interface_stats': interface_stats,
            'variability': network_variability,
            'data': df
        }
        
        print("✅ ネットワーク性能分析完了")
        
    def analyze_correlation_with_performance(self):
        """性能との相関分析"""
        print("\n📊 性能との相関分析を開始...")
        
        # ベンチマーク結果ファイルを検索
        csv_files = list(self.log_dir.glob("*.csv"))
        benchmark_data = None
        
        for csv_file in csv_files:
            if 'h2_' in csv_file.name or 'h3_' in csv_file.name:
                try:
                    df = pd.read_csv(csv_file, header=None, sep='\t')
                    df.columns = ['timestamp', 'status_code', 'response_time']
                    df['protocol'] = 'HTTP/2' if 'h2_' in csv_file.name else 'HTTP/3'
                    df['response_time_ms'] = df['response_time'] / 1000
                    
                    if benchmark_data is None:
                        benchmark_data = df
                    else:
                        benchmark_data = pd.concat([benchmark_data, df])
                except Exception as e:
                    print(f"⚠️ ベンチマークデータ読み込みエラー ({csv_file.name}): {e}")
        
        if benchmark_data is not None and 'system' in self.analysis_results:
            # システムリソースとベンチマーク性能の相関
            system_data = self.analysis_results['system']['data']
            
            # 時間ベースでの相関分析（簡易版）
            correlation_analysis = {
                'cpu_vs_response_time': np.corrcoef(system_data['cpu_usage'], 
                                                   benchmark_data['response_time_ms'].iloc[:len(system_data)])[0,1] if len(system_data) > 0 else 0,
                'memory_vs_response_time': np.corrcoef(system_data['memory_usage'], 
                                                      benchmark_data['response_time_ms'].iloc[:len(system_data)])[0,1] if len(system_data) > 0 else 0
            }
            
            self.analysis_results['correlation'] = correlation_analysis
            print("✅ 性能との相関分析完了")
        else:
            print("⚠️ ベンチマークデータまたはシステムデータが不足しています")
        
    def generate_monitoring_report(self):
        """監視データ分析レポートを生成"""
        print("\n📄 監視データ分析レポートを生成中...")
        
        # レポート内容
        report_content = []
        report_content.append("=" * 80)
        report_content.append("監視データ分析レポート")
        report_content.append("=" * 80)
        report_content.append(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_content.append(f"分析対象ディレクトリ: {self.log_dir}")
        report_content.append("")
        
        # システムリソース分析結果
        if 'system' in self.analysis_results:
            report_content.append("💻 システムリソース分析結果")
            report_content.append("-" * 40)
            
            system_stats = self.analysis_results['system']['stats']
            anomalies = self.analysis_results['system']['anomalies']
            
            # CPU使用率
            cpu_stats = system_stats['cpu_usage']
            report_content.append("📊 CPU使用率:")
            report_content.append(f"  - 平均: {cpu_stats['mean']:.2f}%")
            report_content.append(f"  - 標準偏差: {cpu_stats['std']:.2f}%")
            report_content.append(f"  - 変動係数: {cpu_stats['cv']:.3f}")
            report_content.append(f"  - 範囲: {cpu_stats['min']:.2f}% 〜 {cpu_stats['max']:.2f}%")
            report_content.append("")
            
            # メモリ使用率
            memory_stats = system_stats['memory_usage']
            report_content.append("💾 メモリ使用率:")
            report_content.append(f"  - 平均: {memory_stats['mean']:.2f}%")
            report_content.append(f"  - 標準偏差: {memory_stats['std']:.2f}%")
            report_content.append(f"  - 変動係数: {memory_stats['cv']:.3f}")
            report_content.append(f"  - 範囲: {memory_stats['min']:.2f}% 〜 {memory_stats['max']:.2f}%")
            report_content.append("")
            
            # Dockerコンテナ数
            container_stats = system_stats['docker_containers']
            report_content.append("🐳 Dockerコンテナ数:")
            report_content.append(f"  - 平均: {container_stats['mean']:.1f}")
            report_content.append(f"  - 標準偏差: {container_stats['std']:.2f}")
            report_content.append(f"  - 変動係数: {container_stats['cv']:.3f}")
            report_content.append(f"  - 範囲: {container_stats['min']:.0f} 〜 {container_stats['max']:.0f}")
            report_content.append("")
            
            # 異常検出
            report_content.append("⚠️ 異常検出:")
            report_content.append(f"  - CPU使用率80%超過: {anomalies['high_cpu']}回")
            report_content.append(f"  - メモリ使用率90%超過: {anomalies['high_memory']}回")
            report_content.append(f"  - コンテナ数変更: {anomalies['container_changes']:.0f}回")
            report_content.append("")
        
        # ネットワーク性能分析結果
        if 'network' in self.analysis_results:
            report_content.append("📡 ネットワーク性能分析結果")
            report_content.append("-" * 40)
            
            network_variability = self.analysis_results['network']['variability']
            report_content.append("📊 ネットワーク変動性:")
            report_content.append(f"  - 受信バイト変動係数: {network_variability['rx_bytes_cv']:.3f}")
            report_content.append(f"  - 送信バイト変動係数: {network_variability['tx_bytes_cv']:.3f}")
            report_content.append(f"  - 受信パケット変動係数: {network_variability['rx_packets_cv']:.3f}")
            report_content.append(f"  - 送信パケット変動係数: {network_variability['tx_packets_cv']:.3f}")
            report_content.append("")
        
        # 相関分析結果
        if 'correlation' in self.analysis_results:
            report_content.append("📈 性能との相関分析結果")
            report_content.append("-" * 40)
            
            correlation = self.analysis_results['correlation']
            report_content.append(f"• CPU使用率 vs レスポンス時間: {correlation['cpu_vs_response_time']:.3f}")
            report_content.append(f"• メモリ使用率 vs レスポンス時間: {correlation['memory_vs_response_time']:.3f}")
            report_content.append("")
        
        # 総合評価
        report_content.append("🎯 総合評価")
        report_content.append("-" * 40)
        
        # システム安定性評価
        system_stability = "良好"
        if 'system' in self.analysis_results:
            cpu_cv = self.analysis_results['system']['stats']['cpu_usage']['cv']
            memory_cv = self.analysis_results['system']['stats']['memory_usage']['cv']
            
            if cpu_cv > 0.5 or memory_cv > 0.5:
                system_stability = "不安定"
            elif cpu_cv > 0.3 or memory_cv > 0.3:
                system_stability = "中程度"
        
        report_content.append(f"• システム安定性: {system_stability}")
        
        # ネットワーク安定性評価
        network_stability = "良好"
        if 'network' in self.analysis_results:
            network_cv = self.analysis_results['network']['variability']['rx_bytes_cv']
            if network_cv > 1.0:
                network_stability = "不安定"
            elif network_cv > 0.5:
                network_stability = "中程度"
        
        report_content.append(f"• ネットワーク安定性: {network_stability}")
        
        # 推奨事項
        report_content.append("")
        report_content.append("💡 推奨事項")
        report_content.append("-" * 40)
        
        recommendations = []
        
        if 'system' in self.analysis_results:
            anomalies = self.analysis_results['system']['anomalies']
            if anomalies['high_cpu'] > 0:
                recommendations.append("• CPU使用率の監視と制御を強化")
            if anomalies['high_memory'] > 0:
                recommendations.append("• メモリ使用率の監視と制御を強化")
            if anomalies['container_changes'] > 0:
                recommendations.append("• Dockerコンテナの安定性を確保")
        
        if 'network' in self.analysis_results:
            network_cv = self.analysis_results['network']['variability']['rx_bytes_cv']
            if network_cv > 0.5:
                recommendations.append("• ネットワーク条件の一貫性を確保")
        
        if recommendations:
            for rec in recommendations:
                report_content.append(rec)
        else:
            report_content.append("• 現在の設定で十分な安定性が確保されています")
        
        report_content.append("")
        report_content.append("=" * 80)
        
        # レポート保存
        report_path = self.log_dir / "monitoring_analysis_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_content))
        
        print(f"✅ レポート保存完了: {report_path}")
        
        # 監視データ可視化グラフを生成
        self.generate_monitoring_plots()
        
    def generate_monitoring_plots(self):
        """監視データの可視化グラフを生成"""
        print("📊 監視データ可視化グラフを生成中...")
        
        # システムリソース監視グラフ
        if 'system' in self.analysis_results:
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('システムリソース監視結果', fontsize=16, fontweight='bold')
            
            df = self.analysis_results['system']['data']
            
            # CPU使用率の推移
            ax1 = axes[0, 0]
            ax1.plot(df.index, df['cpu_usage'], 'b-', alpha=0.7)
            ax1.set_title('CPU使用率の推移')
            ax1.set_ylabel('CPU使用率 (%)')
            ax1.grid(True, alpha=0.3)
            
            # メモリ使用率の推移
            ax2 = axes[0, 1]
            ax2.plot(df.index, df['memory_usage'], 'r-', alpha=0.7)
            ax2.set_title('メモリ使用率の推移')
            ax2.set_ylabel('メモリ使用率 (%)')
            ax2.grid(True, alpha=0.3)
            
            # Dockerコンテナ数の推移
            ax3 = axes[1, 0]
            ax3.plot(df.index, df['docker_containers'], 'g-', alpha=0.7)
            ax3.set_title('Dockerコンテナ数の推移')
            ax3.set_ylabel('コンテナ数')
            ax3.grid(True, alpha=0.3)
            
            # リソース使用率の分布
            ax4 = axes[1, 1]
            ax4.hist(df['cpu_usage'], bins=20, alpha=0.7, label='CPU', color='blue')
            ax4.hist(df['memory_usage'], bins=20, alpha=0.7, label='Memory', color='red')
            ax4.set_title('リソース使用率の分布')
            ax4.set_xlabel('使用率 (%)')
            ax4.set_ylabel('頻度')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plot_path = self.log_dir / "system_monitoring_analysis.png"
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ システム監視グラフ保存: {plot_path}")
        
        # ネットワーク監視グラフ
        if 'network' in self.analysis_results:
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('ネットワーク監視結果', fontsize=16, fontweight='bold')
            
            df = self.analysis_results['network']['data']
            
            # 受信バイト数の推移
            ax1 = axes[0, 0]
            for interface in df['interface'].unique()[:3]:  # 上位3つのインターフェース
                interface_data = df[df['interface'] == interface]
                ax1.plot(interface_data.index, interface_data['rx_bytes'], label=interface, alpha=0.7)
            ax1.set_title('受信バイト数の推移')
            ax1.set_ylabel('受信バイト数')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 送信バイト数の推移
            ax2 = axes[0, 1]
            for interface in df['interface'].unique()[:3]:
                interface_data = df[df['interface'] == interface]
                ax2.plot(interface_data.index, interface_data['tx_bytes'], label=interface, alpha=0.7)
            ax2.set_title('送信バイト数の推移')
            ax2.set_ylabel('送信バイト数')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # パケット数の推移
            ax3 = axes[1, 0]
            for interface in df['interface'].unique()[:3]:
                interface_data = df[df['interface'] == interface]
                ax3.plot(interface_data.index, interface_data['rx_packets'], label=f"{interface}_rx", alpha=0.7)
                ax3.plot(interface_data.index, interface_data['tx_packets'], label=f"{interface}_tx", alpha=0.7, linestyle='--')
            ax3.set_title('パケット数の推移')
            ax3.set_ylabel('パケット数')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # ネットワーク使用量の分布
            ax4 = axes[1, 1]
            ax4.hist(df['rx_bytes'], bins=20, alpha=0.7, label='受信', color='blue')
            ax4.hist(df['tx_bytes'], bins=20, alpha=0.7, label='送信', color='red')
            ax4.set_title('ネットワーク使用量の分布')
            ax4.set_xlabel('バイト数')
            ax4.set_ylabel('頻度')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plot_path = self.log_dir / "network_monitoring_analysis.png"
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ ネットワーク監視グラフ保存: {plot_path}")
        
    def run_analysis(self):
        """完全な監視データ分析を実行"""
        print("🚀 監視データ分析を開始...")
        
        self.load_monitoring_data()
        self.analyze_system_resources()
        self.analyze_network_performance()
        self.analyze_correlation_with_performance()
        self.generate_monitoring_report()
        
        print(f"\n✅ 監視データ分析完了！")
        print(f"📁 結果保存先: {self.log_dir}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("使用方法: python3 scripts/analyze_monitoring_data.py <log_directory>")
        sys.exit(1)
    
    log_dir = sys.argv[1]
    analyzer = MonitoringDataAnalyzer(log_dir)
    analyzer.run_analysis() 