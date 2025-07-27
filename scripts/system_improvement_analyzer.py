#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
システム関係の改善点を分析するスクリプト
現在のシステム状況を調査し、ベンチマーク性能向上のための改善提案を行う
"""

import os
import re
import subprocess
import psutil
import platform
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class SystemImprovementAnalyzer:
    def __init__(self):
        self.system_info = {}
        self.docker_info = {}
        self.network_info = {}
        self.resource_usage = {}
        self.improvement_suggestions = []
        
    def get_system_info(self):
        """システム基本情報を取得"""
        print("🔍 システム基本情報を調査中...")
        
        self.system_info = {
            'os': platform.system(),
            'os_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'hostname': platform.node()
        }
        
        # CPU情報
        try:
            self.system_info['cpu_count'] = psutil.cpu_count()
            self.system_info['cpu_count_logical'] = psutil.cpu_count(logical=True)
            self.system_info['cpu_freq'] = psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
        except Exception as e:
            print(f"⚠️ CPU情報取得エラー: {e}")
        
        # メモリ情報
        try:
            memory = psutil.virtual_memory()
            self.system_info['memory_total'] = memory.total
            self.system_info['memory_available'] = memory.available
            self.system_info['memory_percent'] = memory.percent
        except Exception as e:
            print(f"⚠️ メモリ情報取得エラー: {e}")
        
        # ディスク情報
        try:
            disk = psutil.disk_usage('/')
            self.system_info['disk_total'] = disk.total
            self.system_info['disk_free'] = disk.free
            self.system_info['disk_percent'] = disk.percent
        except Exception as e:
            print(f"⚠️ ディスク情報取得エラー: {e}")
        
        print("✅ システム基本情報取得完了")
    
    def get_docker_info(self):
        """Docker環境情報を取得"""
        print("🐳 Docker環境情報を調査中...")
        
        try:
            # Dockerバージョン
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.docker_info['version'] = result.stdout.strip()
            
            # Docker Composeバージョン
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.docker_info['compose_version'] = result.stdout.strip()
            
            # 実行中のコンテナ
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
            if result.returncode == 0:
                self.docker_info['running_containers'] = result.stdout.strip()
            
            # Dockerシステム情報
            result = subprocess.run(['docker', 'system', 'df'], capture_output=True, text=True)
            if result.returncode == 0:
                self.docker_info['system_df'] = result.stdout.strip()
            
            # Dockerデーモン情報
            result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
            if result.returncode == 0:
                self.docker_info['info'] = result.stdout.strip()
                
        except Exception as e:
            print(f"⚠️ Docker情報取得エラー: {e}")
        
        print("✅ Docker環境情報取得完了")
    
    def get_network_info(self):
        """ネットワーク情報を取得"""
        print("🌐 ネットワーク情報を調査中...")
        
        try:
            # ネットワークインターフェース
            net_if_addrs = psutil.net_if_addrs()
            self.network_info['interfaces'] = {}
            
            for interface, addrs in net_if_addrs.items():
                self.network_info['interfaces'][interface] = []
                for addr in addrs:
                    self.network_info['interfaces'][interface].append({
                        'family': str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask
                    })
            
            # ネットワーク統計
            net_io = psutil.net_io_counters()
            self.network_info['io_stats'] = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
            
            # ネットワーク接続
            connections = psutil.net_connections()
            self.network_info['active_connections'] = len(connections)
            
        except Exception as e:
            print(f"⚠️ ネットワーク情報取得エラー: {e}")
        
        print("✅ ネットワーク情報取得完了")
    
    def get_resource_usage(self):
        """現在のリソース使用状況を取得"""
        print("📊 リソース使用状況を調査中...")
        
        try:
            # CPU使用率
            self.resource_usage['cpu_percent'] = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            self.resource_usage['memory_percent'] = memory.percent
            self.resource_usage['memory_used'] = memory.used
            self.resource_usage['memory_available'] = memory.available
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            self.resource_usage['disk_percent'] = disk.percent
            self.resource_usage['disk_free'] = disk.free
            
            # プロセス数
            self.resource_usage['process_count'] = len(psutil.pids())
            
            # 負荷平均（Linuxの場合）
            if platform.system() == 'Linux':
                load_avg = os.getloadavg()
                self.resource_usage['load_average'] = load_avg
            
        except Exception as e:
            print(f"⚠️ リソース使用状況取得エラー: {e}")
        
        print("✅ リソース使用状況取得完了")
    
    def analyze_system_bottlenecks(self):
        """システムボトルネックを分析"""
        print("\n🔍 システムボトルネック分析中...")
        
        bottlenecks = []
        
        # CPU使用率チェック
        if 'cpu_percent' in self.resource_usage:
            cpu_usage = self.resource_usage['cpu_percent']
            if cpu_usage > 80:
                bottlenecks.append(f"🚨 CPU使用率が高い: {cpu_usage:.1f}%")
            elif cpu_usage > 60:
                bottlenecks.append(f"⚠️ CPU使用率が中程度: {cpu_usage:.1f}%")
        
        # メモリ使用率チェック
        if 'memory_percent' in self.resource_usage:
            memory_usage = self.resource_usage['memory_percent']
            if memory_usage > 90:
                bottlenecks.append(f"🚨 メモリ使用率が非常に高い: {memory_usage:.1f}%")
            elif memory_usage > 80:
                bottlenecks.append(f"⚠️ メモリ使用率が高い: {memory_usage:.1f}%")
        
        # ディスク使用率チェック
        if 'disk_percent' in self.resource_usage:
            disk_usage = self.resource_usage['disk_percent']
            if disk_usage > 90:
                bottlenecks.append(f"🚨 ディスク使用率が非常に高い: {disk_usage:.1f}%")
            elif disk_usage > 80:
                bottlenecks.append(f"⚠️ ディスク使用率が高い: {disk_usage:.1f}%")
        
        # Dockerリソースチェック
        if 'system_df' in self.docker_info:
            df_output = self.docker_info['system_df']
            if 'Images' in df_output:
                # Dockerイメージの使用量をチェック
                lines = df_output.split('\n')
                for line in lines:
                    if 'Images' in line and 'GB' in line:
                        size_match = re.search(r'(\d+\.?\d*)\s*GB', line)
                        if size_match:
                            size_gb = float(size_match.group(1))
                            if size_gb > 10:
                                bottlenecks.append(f"⚠️ Dockerイメージサイズが大きい: {size_gb:.1f}GB")
        
        return bottlenecks
    
    def generate_improvement_suggestions(self):
        """改善提案を生成"""
        print("\n💡 改善提案を生成中...")
        
        suggestions = []
        
        # CPU最適化提案
        if 'cpu_count' in self.system_info:
            cpu_count = self.system_info['cpu_count']
            if cpu_count < 4:
                suggestions.append({
                    'category': 'CPU最適化',
                    'priority': '高',
                    'suggestion': f'CPUコア数が少ない({cpu_count}コア)。ベンチマークの並列度を調整してください。',
                    'action': 'THREADSパラメータをCPUコア数に合わせて調整'
                })
        
        # メモリ最適化提案
        if 'memory_total' in self.system_info:
            memory_gb = self.system_info['memory_total'] / (1024**3)
            if memory_gb < 8:
                suggestions.append({
                    'category': 'メモリ最適化',
                    'priority': '高',
                    'suggestion': f'メモリ容量が少ない({memory_gb:.1f}GB)。同時接続数を制限してください。',
                    'action': 'CONNECTIONSパラメータを削減'
                })
        
        # Docker最適化提案
        if 'info' in self.docker_info:
            info = self.docker_info['info']
            if 'CPUs' in info:
                cpu_match = re.search(r'CPUs:\s*(\d+)', info)
                if cpu_match:
                    docker_cpus = int(cpu_match.group(1))
                    if docker_cpus < 2:
                        suggestions.append({
                            'category': 'Docker最適化',
                            'priority': '中',
                            'suggestion': f'Dockerに割り当てられたCPUが少ない({docker_cpus}コア)。',
                            'action': 'Docker Desktopのリソース設定を調整'
                        })
        
        # ネットワーク最適化提案
        if 'active_connections' in self.network_info:
            connections = self.network_info['active_connections']
            if connections > 1000:
                suggestions.append({
                    'category': 'ネットワーク最適化',
                    'priority': '中',
                    'suggestion': f'アクティブなネットワーク接続が多い({connections}個)。',
                    'action': '不要な接続をクリーンアップ'
                })
        
        # システム安定性提案
        suggestions.append({
            'category': 'システム安定性',
            'priority': '高',
            'suggestion': 'ベンチマーク実行前にシステムリソースをクリーンアップしてください。',
            'action': 'メモリクリーンアップとプロセス整理を実行'
        })
        
        # 測定精度向上提案
        suggestions.append({
            'category': '測定精度',
            'priority': '中',
            'suggestion': '複数回の測定による統計的有意性の確保。',
            'action': '自動化スクリプトで複数回測定を実行'
        })
        
        # モニタリング提案
        suggestions.append({
            'category': 'モニタリング',
            'priority': '低',
            'suggestion': 'リアルタイムでのリソース監視を実装。',
            'action': 'システムメトリクス収集スクリプトの追加'
        })
        
        return suggestions
    
    def generate_system_report(self, bottlenecks, suggestions):
        """システムレポートを生成"""
        output_dir = Path("logs") / f"system_improvement_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir.mkdir(exist_ok=True)
        
        report_file = output_dir / "system_improvement_report.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("システム改善分析レポート\n")
            f.write("="*80 + "\n")
            f.write(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("📊 システム基本情報\n")
            f.write("-" * 40 + "\n")
            for key, value in self.system_info.items():
                if key in ['memory_total', 'memory_available', 'disk_total', 'disk_free']:
                    # バイト単位の値をGBに変換
                    gb_value = value / (1024**3)
                    f.write(f"• {key}: {gb_value:.2f} GB\n")
                else:
                    f.write(f"• {key}: {value}\n")
            
            f.write("\n🐳 Docker環境情報\n")
            f.write("-" * 40 + "\n")
            for key, value in self.docker_info.items():
                if key != 'info':  # infoは長すぎるので除外
                    f.write(f"• {key}: {value}\n")
            
            f.write("\n🌐 ネットワーク情報\n")
            f.write("-" * 40 + "\n")
            f.write(f"• アクティブ接続数: {self.network_info.get('active_connections', 'N/A')}\n")
            if 'io_stats' in self.network_info:
                io_stats = self.network_info['io_stats']
                f.write(f"• 送信バイト数: {io_stats['bytes_sent']:,}\n")
                f.write(f"• 受信バイト数: {io_stats['bytes_recv']:,}\n")
            
            f.write("\n📊 現在のリソース使用状況\n")
            f.write("-" * 40 + "\n")
            for key, value in self.resource_usage.items():
                if isinstance(value, float):
                    f.write(f"• {key}: {value:.1f}\n")
                else:
                    f.write(f"• {key}: {value}\n")
            
            f.write("\n🚨 検出されたボトルネック\n")
            f.write("-" * 40 + "\n")
            if bottlenecks:
                for i, bottleneck in enumerate(bottlenecks, 1):
                    f.write(f"{i}. {bottleneck}\n")
            else:
                f.write("• 重大なボトルネックは検出されませんでした\n")
            
            f.write("\n💡 改善提案\n")
            f.write("-" * 40 + "\n")
            for i, suggestion in enumerate(suggestions, 1):
                f.write(f"{i}. [{suggestion['priority']}] {suggestion['category']}\n")
                f.write(f"   提案: {suggestion['suggestion']}\n")
                f.write(f"   アクション: {suggestion['action']}\n\n")
            
            f.write("\n🔧 推奨されるシステム設定\n")
            f.write("-" * 40 + "\n")
            f.write("• Docker Desktop: CPU 4コア以上、メモリ 8GB以上\n")
            f.write("• ベンチマーク実行前: システムリソースのクリーンアップ\n")
            f.write("• 測定中: 他のアプリケーションの終了\n")
            f.write("• ネットワーク: 安定した接続環境の確保\n")
            f.write("• ディスク: 十分な空き容量の確保（10GB以上）\n")
        
        print(f"📄 システム改善レポート保存: {report_file}")
        return output_dir
    
    def run_analysis(self):
        """完全なシステム分析を実行"""
        print("🚀 システム改善分析を開始...")
        
        # 各種情報を取得
        self.get_system_info()
        self.get_docker_info()
        self.get_network_info()
        self.get_resource_usage()
        
        # ボトルネック分析
        bottlenecks = self.analyze_system_bottlenecks()
        
        # 改善提案生成
        suggestions = self.generate_improvement_suggestions()
        
        # レポート生成
        output_dir = self.generate_system_report(bottlenecks, suggestions)
        
        # 結果表示
        print(f"\n📊 システム分析結果:")
        print(f"• OS: {self.system_info.get('os', 'N/A')} {self.system_info.get('os_version', 'N/A')}")
        print(f"• CPU: {self.system_info.get('cpu_count', 'N/A')}コア")
        print(f"• メモリ: {self.system_info.get('memory_total', 0) / (1024**3):.1f}GB")
        print(f"• CPU使用率: {self.resource_usage.get('cpu_percent', 'N/A')}%")
        print(f"• メモリ使用率: {self.resource_usage.get('memory_percent', 'N/A')}%")
        
        print(f"\n🚨 検出されたボトルネック: {len(bottlenecks)}個")
        for bottleneck in bottlenecks:
            print(f"  • {bottleneck}")
        
        print(f"\n💡 改善提案: {len(suggestions)}個")
        for suggestion in suggestions:
            print(f"  • [{suggestion['priority']}] {suggestion['category']}: {suggestion['suggestion']}")
        
        print(f"\n✅ システム分析完了！結果は {output_dir} に保存されました")
        
        return {
            'system_info': self.system_info,
            'docker_info': self.docker_info,
            'network_info': self.network_info,
            'resource_usage': self.resource_usage,
            'bottlenecks': bottlenecks,
            'suggestions': suggestions,
            'output_dir': output_dir
        }

if __name__ == "__main__":
    analyzer = SystemImprovementAnalyzer()
    analyzer.run_analysis() 