#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
システム最適化ツール
ベンチマーク実行前のシステムリソースクリーンアップと最適化を行う
"""

import os
import subprocess
import psutil
import time
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class SystemOptimizationTools:
    def __init__(self):
        self.optimization_results = {}
        
    def cleanup_docker_resources(self):
        """Dockerリソースのクリーンアップ"""
        print("🐳 Dockerリソースをクリーンアップ中...")
        
        results = {}
        
        try:
            # 未使用のコンテナを削除
            result = subprocess.run(['docker', 'container', 'prune', '-f'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                results['containers_cleaned'] = True
                print("✅ 未使用コンテナを削除しました")
            
            # 未使用のイメージを削除
            result = subprocess.run(['docker', 'image', 'prune', '-f'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                results['images_cleaned'] = True
                print("✅ 未使用イメージを削除しました")
            
            # 未使用のボリュームを削除
            result = subprocess.run(['docker', 'volume', 'prune', '-f'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                results['volumes_cleaned'] = True
                print("✅ 未使用ボリュームを削除しました")
            
            # ビルドキャッシュをクリア
            result = subprocess.run(['docker', 'builder', 'prune', '-f'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                results['build_cache_cleaned'] = True
                print("✅ ビルドキャッシュをクリアしました")
            
            # システム全体のクリーンアップ
            result = subprocess.run(['docker', 'system', 'prune', '-f'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                results['system_cleaned'] = True
                print("✅ Dockerシステム全体をクリーンアップしました")
                
        except Exception as e:
            print(f"⚠️ Dockerクリーンアップエラー: {e}")
            results['error'] = str(e)
        
        return results
    
    def cleanup_memory(self):
        """メモリのクリーンアップ"""
        print("🧠 メモリをクリーンアップ中...")
        
        results = {}
        
        try:
            # メモリ使用状況を記録
            memory_before = psutil.virtual_memory()
            results['memory_before'] = {
                'used': memory_before.used,
                'available': memory_before.available,
                'percent': memory_before.percent
            }
            
            # macOSの場合のメモリクリーンアップ
            if os.name == 'posix' and os.uname().sysname == 'Darwin':
                # purgeコマンドでメモリをクリア
                result = subprocess.run(['sudo', 'purge'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    results['memory_purged'] = True
                    print("✅ メモリをクリアしました")
                else:
                    print("⚠️ メモリクリアに失敗しました（sudo権限が必要）")
            
            # 少し待機してメモリ状況を確認
            time.sleep(2)
            
            memory_after = psutil.virtual_memory()
            results['memory_after'] = {
                'used': memory_after.used,
                'available': memory_after.available,
                'percent': memory_after.percent
            }
            
            # 改善量を計算
            improvement = memory_before.available - memory_after.available
            results['memory_improvement'] = improvement
            
            if improvement > 0:
                print(f"✅ メモリ改善: {improvement / (1024**3):.2f}GB 解放")
            else:
                print("ℹ️ メモリ状況に変化なし")
                
        except Exception as e:
            print(f"⚠️ メモリクリーンアップエラー: {e}")
            results['error'] = str(e)
        
        return results
    
    def optimize_network(self):
        """ネットワーク最適化"""
        print("🌐 ネットワークを最適化中...")
        
        results = {}
        
        try:
            # ネットワーク接続数を確認
            connections = psutil.net_connections()
            results['connections_before'] = len(connections)
            
            # 不要な接続を特定（ESTABLISHED以外の状態）
            unnecessary_connections = [conn for conn in connections 
                                    if conn.status not in ['ESTABLISHED', 'LISTEN']]
            results['unnecessary_connections'] = len(unnecessary_connections)
            
            # ネットワーク統計を記録
            net_io = psutil.net_io_counters()
            results['network_stats'] = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
            
            print(f"✅ ネットワーク状況を記録しました（接続数: {len(connections)}）")
            
        except Exception as e:
            print(f"⚠️ ネットワーク最適化エラー: {e}")
            results['error'] = str(e)
        
        return results
    
    def optimize_system_settings(self):
        """システム設定の最適化"""
        print("⚙️ システム設定を最適化中...")
        
        results = {}
        
        try:
            # CPU使用率を確認
            cpu_percent = psutil.cpu_percent(interval=1)
            results['cpu_percent'] = cpu_percent
            
            # プロセス数を確認
            process_count = len(psutil.pids())
            results['process_count'] = process_count
            
            # ディスク使用率を確認
            disk = psutil.disk_usage('/')
            results['disk_usage'] = {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent
            }
            
            # システム負荷を確認（Linuxの場合）
            if os.name == 'posix' and os.uname().sysname == 'Linux':
                load_avg = os.getloadavg()
                results['load_average'] = load_avg
                print(f"✅ システム負荷: {load_avg}")
            
            print(f"✅ システム状況を記録しました（CPU: {cpu_percent}%, プロセス: {process_count}）")
            
        except Exception as e:
            print(f"⚠️ システム設定最適化エラー: {e}")
            results['error'] = str(e)
        
        return results
    
    def create_optimization_script(self):
        """最適化スクリプトを作成"""
        script_content = '''#!/bin/bash
# ベンチマーク実行前のシステム最適化スクリプト

echo "🚀 システム最適化を開始..."

# Dockerリソースのクリーンアップ
echo "🐳 Dockerリソースをクリーンアップ中..."
docker container prune -f
docker image prune -f
docker volume prune -f
docker builder prune -f
docker system prune -f

# メモリクリーンアップ（macOS）
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🧠 メモリをクリーンアップ中..."
    sudo purge
fi

# システム情報の表示
echo "📊 システム情報:"
echo "CPU使用率: $(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')"
echo "メモリ使用率: $(top -l 1 | grep "PhysMem" | awk '{print $2}' | sed 's/G//')"
echo "ディスク使用率: $(df -h / | tail -1 | awk '{print $5}')"

echo "✅ システム最適化完了！"
'''
        
        script_path = Path("scripts") / "optimize_system.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # 実行権限を付与
        os.chmod(script_path, 0o755)
        
        print(f"✅ 最適化スクリプトを作成しました: {script_path}")
        return script_path
    
    def create_monitoring_script(self):
        """モニタリングスクリプトを作成"""
        script_content = '''#!/bin/bash
# システムリソース監視スクリプト

echo "📊 システムリソース監視を開始..."

while true; do
    echo "=== $(date) ==="
    
    # CPU使用率
    cpu_usage=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
    echo "CPU使用率: ${cpu_usage}%"
    
    # メモリ使用率
    memory_usage=$(top -l 1 | grep "PhysMem" | awk '{print $2}' | sed 's/G//')
    echo "メモリ使用率: ${memory_usage}%"
    
    # ディスク使用率
    disk_usage=$(df -h / | tail -1 | awk '{print $5}')
    echo "ディスク使用率: ${disk_usage}"
    
    # Dockerコンテナ状況
    echo "Dockerコンテナ:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo "---"
    sleep 5
done
'''
        
        script_path = Path("scripts") / "monitor_system.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # 実行権限を付与
        os.chmod(script_path, 0o755)
        
        print(f"✅ モニタリングスクリプトを作成しました: {script_path}")
        return script_path
    
    def generate_optimization_report(self, results):
        """最適化レポートを生成"""
        output_dir = Path("logs") / f"system_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir.mkdir(exist_ok=True)
        
        report_file = output_dir / "optimization_report.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("システム最適化レポート\n")
            f.write("="*80 + "\n")
            f.write(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("🐳 Docker最適化結果\n")
            f.write("-" * 40 + "\n")
            docker_results = results.get('docker', {})
            for key, value in docker_results.items():
                if key != 'error':
                    f.write(f"• {key}: {'成功' if value else '失敗'}\n")
            if 'error' in docker_results:
                f.write(f"• エラー: {docker_results['error']}\n")
            
            f.write("\n🧠 メモリ最適化結果\n")
            f.write("-" * 40 + "\n")
            memory_results = results.get('memory', {})
            if 'memory_before' in memory_results:
                before = memory_results['memory_before']
                f.write(f"• 最適化前: {before['used'] / (1024**3):.2f}GB使用, {before['available'] / (1024**3):.2f}GB利用可能\n")
            if 'memory_after' in memory_results:
                after = memory_results['memory_after']
                f.write(f"• 最適化後: {after['used'] / (1024**3):.2f}GB使用, {after['available'] / (1024**3):.2f}GB利用可能\n")
            if 'memory_improvement' in memory_results:
                improvement = memory_results['memory_improvement']
                f.write(f"• 改善量: {improvement / (1024**3):.2f}GB\n")
            
            f.write("\n🌐 ネットワーク最適化結果\n")
            f.write("-" * 40 + "\n")
            network_results = results.get('network', {})
            if 'connections_before' in network_results:
                f.write(f"• ネットワーク接続数: {network_results['connections_before']}\n")
            if 'unnecessary_connections' in network_results:
                f.write(f"• 不要な接続数: {network_results['unnecessary_connections']}\n")
            
            f.write("\n⚙️ システム設定最適化結果\n")
            f.write("-" * 40 + "\n")
            system_results = results.get('system', {})
            if 'cpu_percent' in system_results:
                f.write(f"• CPU使用率: {system_results['cpu_percent']:.1f}%\n")
            if 'process_count' in system_results:
                f.write(f"• プロセス数: {system_results['process_count']}\n")
            if 'disk_usage' in system_results:
                disk = system_results['disk_usage']
                f.write(f"• ディスク使用率: {disk['percent']:.1f}%\n")
            
            f.write("\n📁 生成されたスクリプト\n")
            f.write("-" * 40 + "\n")
            f.write("• scripts/optimize_system.sh - システム最適化スクリプト\n")
            f.write("• scripts/monitor_system.sh - システム監視スクリプト\n")
            
            f.write("\n🔧 使用方法\n")
            f.write("-" * 40 + "\n")
            f.write("1. ベンチマーク実行前: ./scripts/optimize_system.sh\n")
            f.write("2. システム監視: ./scripts/monitor_system.sh\n")
            f.write("3. 定期的なクリーンアップ: 週1回程度の実行を推奨\n")
        
        print(f"📄 最適化レポート保存: {report_file}")
        return output_dir
    
    def run_full_optimization(self):
        """完全な最適化を実行"""
        print("🚀 システム最適化を開始...")
        
        results = {}
        
        # 各最適化を実行
        print("\n" + "="*60)
        results['docker'] = self.cleanup_docker_resources()
        
        print("\n" + "="*60)
        results['memory'] = self.cleanup_memory()
        
        print("\n" + "="*60)
        results['network'] = self.optimize_network()
        
        print("\n" + "="*60)
        results['system'] = self.optimize_system_settings()
        
        # スクリプトを作成
        print("\n" + "="*60)
        self.create_optimization_script()
        self.create_monitoring_script()
        
        # レポートを生成
        print("\n" + "="*60)
        output_dir = self.generate_optimization_report(results)
        
        # 結果サマリー
        print(f"\n📊 最適化結果サマリー:")
        
        # Docker最適化結果
        docker_success = sum(1 for v in results['docker'].values() if isinstance(v, bool) and v)
        print(f"• Docker最適化: {docker_success}項目成功")
        
        # メモリ最適化結果
        if 'memory_improvement' in results['memory']:
            improvement = results['memory']['memory_improvement']
            if improvement > 0:
                print(f"• メモリ改善: {improvement / (1024**3):.2f}GB 解放")
            else:
                print("• メモリ改善: 変化なし")
        
        # システム状況
        if 'cpu_percent' in results['system']:
            print(f"• CPU使用率: {results['system']['cpu_percent']:.1f}%")
        
        print(f"\n✅ 最適化完了！結果は {output_dir} に保存されました")
        
        return results

if __name__ == "__main__":
    optimizer = SystemOptimizationTools()
    optimizer.run_full_optimization() 