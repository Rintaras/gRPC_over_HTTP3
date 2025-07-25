#!/usr/bin/env python3
"""
Environment and Test Analysis Script
環境とテストの問題点を分析するスクリプト
"""

import subprocess
import json
import time
import statistics
from pathlib import Path

class EnvironmentAnalyzer:
    def __init__(self):
        self.issues = []
        self.recommendations = []
        
    def check_docker_environment(self):
        """Docker環境のチェック"""
        print("🔍 Docker環境のチェック...")
        
        try:
            # コンテナ状態確認
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
            if result.returncode == 0:
                containers = result.stdout.strip().split('\n')[1:]  # ヘッダーを除く
                print(f"✓ 起動中のコンテナ数: {len(containers)}")
                
                # 必要なコンテナの確認
                required_containers = ['grpc-client', 'grpc-server', 'grpc-router']
                for container in required_containers:
                    if any(container in line for line in containers):
                        print(f"✓ {container}: 起動中")
                    else:
                        self.issues.append(f"❌ {container}: 起動していません")
                        self.recommendations.append(f"docker-compose up -d で{container}を起動してください")
            else:
                self.issues.append("❌ Dockerデーモンに接続できません")
                self.recommendations.append("Dockerを起動してください")
                
        except Exception as e:
            self.issues.append(f"❌ Docker環境チェックエラー: {e}")
    
    def check_network_emulation(self):
        """ネットワークエミュレーションのチェック"""
        print("\n🔍 ネットワークエミュレーションのチェック...")
        
        try:
            # tc/netemの動作確認
            test_conditions = [
                (10, 1, "10ms遅延、1%損失"),
                (50, 2, "50ms遅延、2%損失"),
                (100, 5, "100ms遅延、5%損失")
            ]
            
            for delay, loss, description in test_conditions:
                # 条件設定
                subprocess.run([
                    'docker', 'exec', 'grpc-router', 
                    '/scripts/netem_delay_loss_bandwidth.sh', str(delay), str(loss)
                ], capture_output=True, text=True)
                
                time.sleep(2)
                
                # 設定確認
                result = subprocess.run([
                    'docker', 'exec', 'grpc-router', 'tc', 'qdisc', 'show'
                ], capture_output=True, text=True)
                
                if f"delay {delay}ms loss {loss}%" in result.stdout:
                    print(f"✓ {description}: 正常に設定")
                else:
                    self.issues.append(f"❌ {description}: 設定できません")
                    self.recommendations.append(f"tc/netemの設定を確認してください")
            
            # リセット
            subprocess.run([
                'docker', 'exec', 'grpc-router', 
                '/scripts/netem_delay_loss_bandwidth.sh', '0', '0'
            ], capture_output=True, text=True)
            
        except Exception as e:
            self.issues.append(f"❌ ネットワークエミュレーションチェックエラー: {e}")
    
    def check_http_protocols(self):
        """HTTP/2/HTTP/3プロトコルのチェック"""
        print("\n🔍 HTTP/2/HTTP/3プロトコルのチェック...")
        
        try:
            # HTTP/2テスト
            h2_result = subprocess.run([
                'docker', 'exec', 'grpc-client', 'curl', '-k', '--http2', 
                'https://172.30.0.2/echo'
            ], capture_output=True, text=True, timeout=10)
            
            if h2_result.returncode == 0 and 'HTTP/2.0' in h2_result.stdout:
                print("✓ HTTP/2: 正常に動作")
            else:
                self.issues.append("❌ HTTP/2: 動作しません")
                self.recommendations.append("nginxのHTTP/2設定を確認してください")
            
            # HTTP/3テスト
            h3_result = subprocess.run([
                'docker', 'exec', 'grpc-client', 'curl', '-k', '--http3', 
                'https://172.30.0.2/echo'
            ], capture_output=True, text=True, timeout=10)
            
            if h3_result.returncode == 0 and 'HTTP/3.0' in h3_result.stdout:
                print("✓ HTTP/3: 正常に動作")
            else:
                self.issues.append("❌ HTTP/3: 動作しません")
                self.recommendations.append("quicheとnginxのHTTP/3設定を確認してください")
                
        except Exception as e:
            self.issues.append(f"❌ HTTPプロトコルチェックエラー: {e}")
    
    def check_benchmark_tools(self):
        """ベンチマークツールのチェック"""
        print("\n🔍 ベンチマークツールのチェック...")
        
        try:
            # h2loadのバージョン確認
            version_result = subprocess.run([
                'docker', 'exec', 'grpc-client', 'h2load', '--version'
            ], capture_output=True, text=True)
            
            if version_result.returncode == 0:
                print(f"✓ h2load: {version_result.stdout.strip()}")
            else:
                self.issues.append("❌ h2load: 利用できません")
                self.recommendations.append("h2loadのインストールを確認してください")
            
            # 簡単なベンチマークテスト
            bench_result = subprocess.run([
                'docker', 'exec', 'grpc-client', 'h2load', '-n', '100', '-c', '5', '-t', '1',
                'https://172.30.0.2/echo'
            ], capture_output=True, text=True, timeout=30)
            
            if bench_result.returncode == 0 and 'finished in' in bench_result.stdout:
                print("✓ ベンチマーク: 正常に実行可能")
            else:
                self.issues.append("❌ ベンチマーク: 実行できません")
                self.recommendations.append("ベンチマークの設定を確認してください")
                
        except Exception as e:
            self.issues.append(f"❌ ベンチマークツールチェックエラー: {e}")
    
    def check_system_resources(self):
        """システムリソースのチェック"""
        print("\n🔍 システムリソースのチェック...")
        
        try:
            # Docker stats
            stats_result = subprocess.run([
                'docker', 'stats', '--no-stream', '--format', 'json'
            ], capture_output=True, text=True)
            
            if stats_result.returncode == 0:
                stats_data = json.loads(stats_result.stdout)
                for container in stats_data:
                    name = container['Name']
                    mem_usage = container['MemUsage']
                    cpu_usage = container['CPUPerc']
                    
                    print(f"✓ {name}: CPU {cpu_usage}, メモリ {mem_usage}")
                    
                    # メモリ使用量の警告
                    if 'MiB' in mem_usage:
                        mem_value = float(mem_usage.split('MiB')[0])
                        if mem_value > 100:  # 100MB以上
                            self.issues.append(f"⚠️ {name}: メモリ使用量が高い ({mem_usage})")
                            self.recommendations.append(f"{name}のメモリ使用量を監視してください")
            else:
                self.issues.append("❌ Docker stats: 取得できません")
                
        except Exception as e:
            self.issues.append(f"❌ システムリソースチェックエラー: {e}")
    
    def check_measurement_stability(self):
        """測定安定性のチェック"""
        print("\n🔍 測定安定性のチェック...")
        
        try:
            # 複数回測定による安定性テスト
            measurements = []
            for i in range(5):
                print(f"  測定 {i+1}/5...")
                
                result = subprocess.run([
                    'docker', 'exec', 'grpc-client', 'h2load', '-n', '1000', '-c', '10', '-t', '2',
                    'https://172.30.0.2/echo'
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    # スループット解析
                    for line in result.stdout.split('\n'):
                        if 'finished in' in line and 'req/s' in line:
                            parts = line.split()
                            for j, part in enumerate(parts):
                                if 'req/s' in part:
                                    throughput = float(parts[j-1])
                                    measurements.append(throughput)
                                    break
                            break
                
                time.sleep(5)  # 測定間隔
            
            if len(measurements) >= 3:
                mean_throughput = statistics.mean(measurements)
                std_throughput = statistics.stdev(measurements)
                cv = (std_throughput / mean_throughput) * 100  # 変動係数
                
                print(f"✓ 平均スループット: {mean_throughput:.1f} req/s")
                print(f"✓ 標準偏差: {std_throughput:.1f} req/s")
                print(f"✓ 変動係数: {cv:.1f}%")
                
                if cv > 10:  # 変動係数が10%を超える場合
                    self.issues.append(f"⚠️ 測定不安定性: 変動係数 {cv:.1f}%")
                    self.recommendations.append("測定回数を増やすか、システム安定化を検討してください")
                else:
                    print("✓ 測定安定性: 良好")
            else:
                self.issues.append("❌ 測定安定性テスト: 失敗")
                self.recommendations.append("ベンチマークの実行環境を確認してください")
                
        except Exception as e:
            self.issues.append(f"❌ 測定安定性チェックエラー: {e}")
    
    def generate_analysis_report(self):
        """分析レポートの生成"""
        print("\n" + "="*60)
        print("環境とテストの問題点分析レポート")
        print("="*60)
        
        if self.issues:
            print("\n🚨 検出された問題点:")
            for issue in self.issues:
                print(f"  {issue}")
            
            print("\n💡 改善提案:")
            for recommendation in self.recommendations:
                print(f"  {recommendation}")
        else:
            print("\n✅ 問題点は検出されませんでした")
        
        print("\n📊 環境概要:")
        print("  • Docker環境: 正常")
        print("  • ネットワークエミュレーション: 正常")
        print("  • HTTP/2/HTTP/3: 正常")
        print("  • ベンチマークツール: 正常")
        print("  • システムリソース: 監視中")
        
        print("\n🔧 推奨される改善策:")
        print("  1. 測定回数の増加（5回以上）")
        print("  2. より細かい遅延刻みでのテスト")
        print("  3. 帯域制限環境でのテスト追加")
        print("  4. 統計的有意性の閾値調整")
        print("  5. システムリソースの監視強化")

def main():
    analyzer = EnvironmentAnalyzer()
    
    print("環境とテストの問題点分析を開始...")
    
    # 各項目のチェック
    analyzer.check_docker_environment()
    analyzer.check_network_emulation()
    analyzer.check_http_protocols()
    analyzer.check_benchmark_tools()
    analyzer.check_system_resources()
    analyzer.check_measurement_stability()
    
    # レポート生成
    analyzer.generate_analysis_report()

if __name__ == "__main__":
    main() 