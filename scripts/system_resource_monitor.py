#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
システムリソース詳細監視スクリプト
ベンチマーク実行中のシステムリソース使用状況を詳細に監視
"""

import os
import time
import psutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import json

class SystemResourceMonitor:
    def __init__(self, output_dir="logs/system_monitor"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.monitoring = False
        self.monitor_thread = None
        self.monitor_data = []
        
    def get_system_info(self):
        """システム基本情報を取得"""
        info = {
            'timestamp': datetime.now().isoformat(),
            'cpu': {
                'count': psutil.cpu_count(),
                'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                'usage_percent': psutil.cpu_percent(interval=1),
                'load_avg': psutil.getloadavg()
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'used': psutil.virtual_memory().used,
                'percent': psutil.virtual_memory().percent,
                'swap_total': psutil.swap_memory().total,
                'swap_used': psutil.swap_memory().used,
                'swap_percent': psutil.swap_memory().percent
            },
            'disk': {
                'partitions': [],
                'io_counters': psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else None
            },
            'network': {
                'connections': len(psutil.net_connections()),
                'io_counters': psutil.net_io_counters()._asdict() if psutil.net_io_counters() else None
            },
            'processes': {
                'total': len(psutil.pids()),
                'docker_processes': 0
            }
        }
        
        # ディスクパーティション情報
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                info['disk']['partitions'].append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except:
                pass
        
        # Dockerプロセス数
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['name'] and 'docker' in proc.info['name'].lower():
                    info['processes']['docker_processes'] += 1
        except:
            pass
        
        return info
    
    def get_docker_info(self):
        """Docker情報を取得"""
        docker_info = {
            'timestamp': datetime.now().isoformat(),
            'containers': [],
            'images': [],
            'system': {}
        }
        
        try:
            # 実行中のコンテナ
            result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            container = json.loads(line)
                            docker_info['containers'].append({
                                'id': container.get('ID', ''),
                                'name': container.get('Names', ''),
                                'image': container.get('Image', ''),
                                'status': container.get('Status', ''),
                                'ports': container.get('Ports', '')
                            })
                        except:
                            pass
            
            # システム情報
            result = subprocess.run(['docker', 'system', 'df', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                try:
                    docker_info['system'] = json.loads(result.stdout.strip())
                except:
                    pass
                    
        except Exception as e:
            docker_info['error'] = str(e)
        
        return docker_info
    
    def monitor_resources(self, interval=5):
        """リソース監視を開始"""
        self.monitoring = True
        self.monitor_data = []
        
        print(f"🔍 システムリソース監視開始 (間隔: {interval}秒)")
        print(f"📁 出力先: {self.output_dir}")
        
        while self.monitoring:
            try:
                # システム情報取得
                system_info = self.get_system_info()
                docker_info = self.get_docker_info()
                
                # データ統合
                monitor_data = {
                    'system': system_info,
                    'docker': docker_info
                }
                
                self.monitor_data.append(monitor_data)
                
                # リアルタイム表示
                cpu_usage = system_info['cpu']['usage_percent']
                memory_usage = system_info['memory']['percent']
                docker_containers = len(docker_info['containers'])
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"CPU: {cpu_usage:.1f}% | "
                      f"Memory: {memory_usage:.1f}% | "
                      f"Docker: {docker_containers} containers")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n⏹️ 監視を停止します...")
                break
            except Exception as e:
                print(f"⚠️ 監視エラー: {e}")
                time.sleep(interval)
        
        self.save_monitor_data()
    
    def save_monitor_data(self):
        """監視データを保存"""
        if not self.monitor_data:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSONファイルとして保存
        json_file = self.output_dir / f"system_monitor_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.monitor_data, f, indent=2, ensure_ascii=False)
        
        # CSVファイルとして保存（統計情報）
        csv_file = self.output_dir / f"system_monitor_{timestamp}.csv"
        csv_data = []
        
        for data in self.monitor_data:
            system = data['system']
            csv_data.append({
                'timestamp': system['timestamp'],
                'cpu_usage': system['cpu']['usage_percent'],
                'memory_usage': system['memory']['percent'],
                'memory_available_gb': system['memory']['available'] / (1024**3),
                'swap_usage': system['memory']['swap_percent'],
                'processes_total': system['processes']['total'],
                'docker_processes': system['processes']['docker_processes'],
                'network_connections': system['network']['connections'],
                'docker_containers': len(data['docker']['containers'])
            })
        
        import pandas as pd
        df = pd.DataFrame(csv_data)
        df.to_csv(csv_file, index=False)
        
        print(f"✅ 監視データ保存完了:")
        print(f"  📄 JSON: {json_file}")
        print(f"  📊 CSV: {csv_file}")
        
        # 統計サマリーを生成
        self.generate_statistics_summary()
    
    def generate_statistics_summary(self):
        """統計サマリーを生成"""
        if not self.monitor_data:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.output_dir / f"system_monitor_summary_{timestamp}.txt"
        
        # 統計計算
        cpu_usage = [d['system']['cpu']['usage_percent'] for d in self.monitor_data]
        memory_usage = [d['system']['memory']['percent'] for d in self.monitor_data]
        docker_containers = [len(d['docker']['containers']) for d in self.monitor_data]
        
        summary_content = []
        summary_content.append("=" * 60)
        summary_content.append("システムリソース監視サマリー")
        summary_content.append("=" * 60)
        summary_content.append(f"監視期間: {self.monitor_data[0]['system']['timestamp']} 〜 {self.monitor_data[-1]['system']['timestamp']}")
        summary_content.append(f"データポイント数: {len(self.monitor_data)}")
        summary_content.append("")
        
        # CPU使用率統計
        summary_content.append("📊 CPU使用率統計")
        summary_content.append("-" * 30)
        summary_content.append(f"平均: {np.mean(cpu_usage):.2f}%")
        summary_content.append(f"最大: {np.max(cpu_usage):.2f}%")
        summary_content.append(f"最小: {np.min(cpu_usage):.2f}%")
        summary_content.append(f"標準偏差: {np.std(cpu_usage):.2f}%")
        summary_content.append("")
        
        # メモリ使用率統計
        summary_content.append("💾 メモリ使用率統計")
        summary_content.append("-" * 30)
        summary_content.append(f"平均: {np.mean(memory_usage):.2f}%")
        summary_content.append(f"最大: {np.max(memory_usage):.2f}%")
        summary_content.append(f"最小: {np.min(memory_usage):.2f}%")
        summary_content.append(f"標準偏差: {np.std(memory_usage):.2f}%")
        summary_content.append("")
        
        # Docker統計
        summary_content.append("🐳 Docker統計")
        summary_content.append("-" * 30)
        summary_content.append(f"平均コンテナ数: {np.mean(docker_containers):.1f}")
        summary_content.append(f"最大コンテナ数: {np.max(docker_containers)}")
        summary_content.append(f"最小コンテナ数: {np.min(docker_containers)}")
        summary_content.append("")
        
        # 異常検出
        summary_content.append("⚠️ 異常検出")
        summary_content.append("-" * 30)
        
        # CPU使用率が80%を超えた回数
        high_cpu_count = sum(1 for cpu in cpu_usage if cpu > 80)
        if high_cpu_count > 0:
            summary_content.append(f"• CPU使用率80%超過: {high_cpu_count}回")
        
        # メモリ使用率が90%を超えた回数
        high_memory_count = sum(1 for mem in memory_usage if mem > 90)
        if high_memory_count > 0:
            summary_content.append(f"• メモリ使用率90%超過: {high_memory_count}回")
        
        # コンテナ数の変動
        container_variance = np.var(docker_containers)
        if container_variance > 1:
            summary_content.append(f"• Dockerコンテナ数変動: 分散 {container_variance:.2f}")
        
        if high_cpu_count == 0 and high_memory_count == 0 and container_variance <= 1:
            summary_content.append("• 異常は検出されませんでした")
        
        summary_content.append("")
        summary_content.append("=" * 60)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(summary_content))
        
        print(f"📋 統計サマリー保存: {summary_file}")
    
    def start_monitoring(self, duration=None, interval=5):
        """監視を開始"""
        if self.monitoring:
            print("⚠️ 既に監視中です")
            return
        
        # 監視スレッドを開始
        self.monitor_thread = threading.Thread(
            target=self.monitor_resources, 
            args=(interval,)
        )
        self.monitor_thread.start()
        
        # 指定された時間だけ監視
        if duration:
            time.sleep(duration)
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """監視を停止"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        
        print("✅ システムリソース監視停止")

if __name__ == "__main__":
    import numpy as np
    
    # 監視インスタンス作成
    monitor = SystemResourceMonitor()
    
    try:
        # 30分間監視（5秒間隔）
        print("🚀 システムリソース監視を開始します...")
        print("⏱️ 監視時間: 30分")
        print("📊 監視間隔: 5秒")
        print("🛑 停止するには Ctrl+C を押してください")
        
        monitor.start_monitoring(duration=1800, interval=5)
        
    except KeyboardInterrupt:
        print("\n⏹️ ユーザーによる停止")
        monitor.stop_monitoring()
    
    print("✅ 監視完了") 