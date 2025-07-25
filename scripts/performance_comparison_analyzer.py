#!/usr/bin/env python3
"""
Performance Comparison Analyzer
performance_comparison_overview.pngのような詳細な性能比較グラフを生成
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import json
from pathlib import Path
import argparse
import subprocess
import time

# 日本語フォント設定（文字化け対策完全強化）
import matplotlib.font_manager as fm
import matplotlib as mpl
import warnings

# 警告を無視
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

# 日本語フォントの優先順位リスト（拡張版）
japanese_fonts = [
    'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', 'Meiryo', 
    'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP', 
    'Source Han Sans JP', 'Noto Sans JP', 'M PLUS 1p', 'Kosugi Maru',
    'Hiragino Maru Gothic ProN', 'Yu Gothic UI', 'MS Gothic', 'MS Mincho'
]

# 利用可能なフォントを確認
available_fonts = [f.name for f in fm.fontManager.ttflist]

# 日本語フォントを優先的に設定
font_found = False
selected_font = None

for font in japanese_fonts:
    if font in available_fonts:
        selected_font = font
        font_found = True
        break

if font_found:
    # 完全なフォント設定
    font_family = [selected_font, 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
    
    # 全てのmatplotlib設定を更新
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
    
    # matplotlib全体の設定も更新
    mpl.rcParams.update({
        'font.family': font_family,
        'font.sans-serif': font_family,
        'axes.unicode_minus': False
    })
    
    print(f"✅ 日本語フォント設定成功: {selected_font}")
else:
    # フォールバック設定
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

print(f"📝 利用可能な日本語フォント: {[f for f in japanese_fonts if f in available_fonts]}")
print(f"🔧 現在のフォント設定: {plt.rcParams['font.family']}")

class PerformanceComparisonAnalyzer:
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.results = []
        
    def run_comprehensive_benchmark(self, delay, loss, bandwidth=0, protocol='http2'):
        """包括的なベンチマーク実行"""
        print(f"実行中: {protocol} - 遅延:{delay}ms, 損失:{loss}%, 帯域:{bandwidth}Mbps")
        
        # 3回測定で平均化
        measurements = []
        for i in range(3):
            print(f"  測定 {i+1}/3...")
            
            # ネットワーク条件設定
            self.set_network_conditions(delay, loss, bandwidth)
            
            # システム安定化
            time.sleep(10)
            
            # ベンチマーク実行
            result = self.execute_benchmark(protocol)
            if result:
                measurements.append(result)
                print(f"    結果: {result['throughput']:.1f} req/s, {result['latency']:.1f}ms, {result['connect_time']:.1f}ms")
            else:
                print(f"    測定失敗")
            
            # 測定間隔
            time.sleep(5)
        
        if not measurements:
            print(f"  警告: 全ての測定が失敗しました")
            return None
        
        # 異常値除去と平均化
        throughputs = [m['throughput'] for m in measurements]
        latencies = [m['latency'] for m in measurements]
        connect_times = [m['connect_time'] for m in measurements]
        
        print(f"  生データ: {throughputs}")
        
        # 外れ値除去（3σルール）
        throughput_mean = np.mean(throughputs)
        throughput_std = np.std(throughputs)
        valid_measurements = []
        
        for i, t in enumerate(throughputs):
            if abs(t - throughput_mean) <= 3 * throughput_std:
                valid_measurements.append(measurements[i])
            else:
                print(f"    外れ値除去: {t:.1f} req/s (平均: {throughput_mean:.1f} ± {3*throughput_std:.1f})")
        
        if len(valid_measurements) < 2:
            print(f"  警告: 有効な測定値が不足 ({len(valid_measurements)}/3)")
            valid_measurements = measurements
        
        # 平均値計算
        avg_throughput = np.mean([m['throughput'] for m in valid_measurements])
        avg_latency = np.mean([m['latency'] for m in valid_measurements])
        avg_connect_time = np.mean([m['connect_time'] for m in valid_measurements])
        
        print(f"  最終結果: {avg_throughput:.1f} req/s, {avg_latency:.1f}ms, {avg_connect_time:.1f}ms")
        
        return {
            'protocol': protocol,
            'delay': delay,
            'loss': loss,
            'bandwidth': bandwidth,
            'throughput': avg_throughput,
            'latency': avg_latency,
            'connect_time': avg_connect_time
        }
    
    def set_network_conditions(self, delay, loss, bandwidth):
        """ネットワーク条件設定"""
        try:
            if bandwidth == 0:
                cmd = f"docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh {delay} {loss}"
            else:
                cmd = f"docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh {delay} {loss} {bandwidth}"
            
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            print(f"    ネットワーク条件設定: {delay}ms, {loss}%, {bandwidth}Mbps")
        except subprocess.CalledProcessError as e:
            print(f"    ネットワーク条件設定エラー: {e}")
    
    def execute_benchmark(self, protocol):
        """ベンチマーク実行"""
        try:
            if protocol == 'http2':
                cmd = [
                    'docker', 'exec', 'grpc-client', 'h2load',
                    '--alpn-list=h2,http/1.1',
                    '-n', '1000',
                    '-c', '10',
                    '-t', '2',
                    'https://172.30.0.2/echo'
                ]
            else:  # http3
                cmd = [
                    'docker', 'exec', 'grpc-client', 'h2load',
                    '--alpn-list=h3,h2,http/1.1',
                    '-n', '1000',
                    '-c', '10',
                    '-t', '2',
                    'https://172.30.0.2/echo'
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # 結果解析
                output = result.stdout
                throughput = self.parse_throughput(output)
                latency = self.parse_latency(output)
                connect_time = self.parse_connect_time(output)
                
                if throughput and latency and connect_time:
                    return {
                        'throughput': throughput,
                        'latency': latency,
                        'connect_time': connect_time
                    }
                else:
                    print(f"      解析失敗: throughput={throughput}, latency={latency}, connect_time={connect_time}")
            else:
                print(f"      ベンチマーク失敗: returncode={result.returncode}")
                print(f"      エラー: {result.stderr}")
            
            return None
            
        except subprocess.TimeoutExpired:
            print("      タイムアウト: ベンチマークが300秒を超過")
            return None
        except Exception as e:
            print(f"      ベンチマーク実行エラー: {e}")
            return None
    
    def parse_throughput(self, output):
        """スループット解析"""
        try:
            for line in output.split('\n'):
                if 'finished in' in line and 'req/s' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'req/s' in part:
                            return float(parts[i-1])
            return None
        except:
            return None
    
    def parse_latency(self, output):
        """レイテンシ解析"""
        try:
            for line in output.split('\n'):
                if 'time for request:' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'ms' in part and part.replace('.', '').replace('ms', '').isdigit():
                            return float(part.replace('ms', ''))
            return None
        except:
            return None
    
    def parse_connect_time(self, output):
        """接続時間解析"""
        try:
            for line in output.split('\n'):
                if 'time for connect:' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'ms' in part and part.replace('.', '').replace('ms', '').isdigit():
                            return float(part.replace('ms', ''))
            return None
        except:
            return None
    
    def generate_performance_comparison_graphs(self):
        """performance_comparison_overview.pngのようなグラフ生成"""
        if not self.results:
            print("データが不足しています")
            return
        
        df = pd.DataFrame(self.results)
        
        # グラフ設定
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        # 遅延条件の取得
        delays = sorted(df['delay'].unique())
        
        # 上段: 絶対値比較
        # 1. スループット比較
        ax1 = axes[0, 0]
        h2_throughput = []
        h3_throughput = []
        
        for delay in delays:
            h2_data = df[(df['protocol'] == 'http2') & (df['delay'] == delay)]
            h3_data = df[(df['protocol'] == 'http3') & (df['delay'] == delay)]
            
            if len(h2_data) > 0:
                h2_throughput.append(h2_data['throughput'].iloc[0])
            else:
                h2_throughput.append(0)
                
            if len(h3_data) > 0:
                h3_throughput.append(h3_data['throughput'].iloc[0])
            else:
                h3_throughput.append(0)
        
        x = np.arange(len(delays))
        width = 0.35
        
        ax1.bar(x - width/2, h2_throughput, width, label='HTTP/2', color='blue', alpha=0.7)
        ax1.bar(x + width/2, h3_throughput, width, label='HTTP/3', color='orange', alpha=0.7)
        
        ax1.set_xlabel('遅延 (ms)')
        ax1.set_ylabel('スループット (req/s)')
        ax1.set_title('スループット比較')
        ax1.set_xticks(x)
        ax1.set_xticklabels(delays)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. レイテンシ比較
        ax2 = axes[0, 1]
        h2_latency = []
        h3_latency = []
        
        for delay in delays:
            h2_data = df[(df['protocol'] == 'http2') & (df['delay'] == delay)]
            h3_data = df[(df['protocol'] == 'http3') & (df['delay'] == delay)]
            
            if len(h2_data) > 0:
                h2_latency.append(h2_data['latency'].iloc[0])
            else:
                h2_latency.append(0)
                
            if len(h3_data) > 0:
                h3_latency.append(h3_data['latency'].iloc[0])
            else:
                h3_latency.append(0)
        
        ax2.bar(x - width/2, h2_latency, width, label='HTTP/2', color='blue', alpha=0.7)
        ax2.bar(x + width/2, h3_latency, width, label='HTTP/3', color='orange', alpha=0.7)
        
        ax2.set_xlabel('遅延 (ms)')
        ax2.set_ylabel('レイテンシ (ms)')
        ax2.set_title('レイテンシ比較')
        ax2.set_xticks(x)
        ax2.set_xticklabels(delays)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 接続時間比較
        ax3 = axes[0, 2]
        h2_connect = []
        h3_connect = []
        
        for delay in delays:
            h2_data = df[(df['protocol'] == 'http2') & (df['delay'] == delay)]
            h3_data = df[(df['protocol'] == 'http3') & (df['delay'] == delay)]
            
            if len(h2_data) > 0:
                h2_connect.append(h2_data['connect_time'].iloc[0])
            else:
                h2_connect.append(0)
                
            if len(h3_data) > 0:
                h3_connect.append(h3_data['connect_time'].iloc[0])
            else:
                h3_connect.append(0)
        
        ax3.bar(x - width/2, h2_connect, width, label='HTTP/2', color='blue', alpha=0.7)
        ax3.bar(x + width/2, h3_connect, width, label='HTTP/3', color='orange', alpha=0.7)
        
        ax3.set_xlabel('遅延 (ms)')
        ax3.set_ylabel('接続時間 (ms)')
        ax3.set_title('接続時間比較')
        ax3.set_xticks(x)
        ax3.set_xticklabels(delays)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 下段: HTTP/3優位性（パーセンテージ）
        # 4. スループット優位性
        ax4 = axes[1, 0]
        throughput_advantage = []
        
        for i, delay in enumerate(delays):
            if h3_throughput[i] > 0 and h2_throughput[i] > 0:
                advantage = ((h3_throughput[i] - h2_throughput[i]) / h2_throughput[i]) * 100
                throughput_advantage.append(advantage)
            else:
                throughput_advantage.append(0)
        
        colors = ['green' if x > 0 else 'red' for x in throughput_advantage]
        ax4.bar(x, throughput_advantage, color=colors, alpha=0.7)
        ax4.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        
        ax4.set_xlabel('遅延 (ms)')
        ax4.set_ylabel('HTTP/3 優位性 (%)')
        ax4.set_title('スループット優位性\n(緑=HTTP/3優位)')
        ax4.set_xticks(x)
        ax4.set_xticklabels(delays)
        ax4.grid(True, alpha=0.3)
        
        # 5. レイテンシ優位性
        ax5 = axes[1, 1]
        latency_advantage = []
        
        for i, delay in enumerate(delays):
            if h3_latency[i] > 0 and h2_latency[i] > 0:
                advantage = ((h2_latency[i] - h3_latency[i]) / h2_latency[i]) * 100
                latency_advantage.append(advantage)
            else:
                latency_advantage.append(0)
        
        colors = ['green' if x > 0 else 'red' for x in latency_advantage]
        ax5.bar(x, latency_advantage, color=colors, alpha=0.7)
        ax5.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        
        ax5.set_xlabel('遅延 (ms)')
        ax5.set_ylabel('HTTP/3 優位性 (%)')
        ax5.set_title('レイテンシ優位性\n(緑=HTTP/3優位)')
        ax5.set_xticks(x)
        ax5.set_xticklabels(delays)
        ax5.grid(True, alpha=0.3)
        
        # 6. 接続時間優位性
        ax6 = axes[1, 2]
        connect_advantage = []
        
        for i, delay in enumerate(delays):
            if h3_connect[i] > 0 and h2_connect[i] > 0:
                advantage = ((h2_connect[i] - h3_connect[i]) / h2_connect[i]) * 100
                connect_advantage.append(advantage)
            else:
                connect_advantage.append(0)
        
        colors = ['green' if x > 0 else 'red' for x in connect_advantage]
        ax6.bar(x, connect_advantage, color=colors, alpha=0.7)
        ax6.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        
        ax6.set_xlabel('遅延 (ms)')
        ax6.set_ylabel('HTTP/3 優位性 (%)')
        ax6.set_title('接続時間優位性\n(緑=HTTP/3優位)')
        ax6.set_xticks(x)
        ax6.set_xticklabels(delays)
        ax6.grid(True, alpha=0.3)
        
        # 文字化け対策: シンプルなフォント再設定
        font_family = ['Hiragino Sans', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
        
        # 設定を再更新
        plt.rcParams['font.family'] = font_family
        plt.rcParams['font.sans-serif'] = font_family
        plt.rcParams['axes.unicode_minus'] = False
        
        mpl.rcParams['font.family'] = font_family
        mpl.rcParams['font.sans-serif'] = font_family
        mpl.rcParams['axes.unicode_minus'] = False
        
        plt.tight_layout()
        plt.savefig(self.log_dir / 'performance_comparison_overview.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"性能比較グラフを保存: {self.log_dir / 'performance_comparison_overview.png'}")
    
    def generate_comparison_report(self):
        """性能比較レポート生成"""
        report_file = self.log_dir / "performance_comparison_report.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("HTTP/2 vs HTTP/3 性能比較レポート\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("📊 測定統計\n")
            f.write("-" * 30 + "\n")
            f.write(f"総測定数: {len(self.results)}\n")
            f.write(f"テスト条件数: {len(set([(r['delay'], r['loss'], r['bandwidth']) for r in self.results]))}\n\n")
            
            f.write("📈 詳細結果\n")
            f.write("-" * 30 + "\n")
            
            delays = sorted(set([r['delay'] for r in self.results]))
            for delay in delays:
                f.write(f"\n遅延: {delay}ms\n")
                f.write("-" * 20 + "\n")
                
                h2_data = [r for r in self.results if r['protocol'] == 'http2' and r['delay'] == delay]
                h3_data = [r for r in self.results if r['protocol'] == 'http3' and r['delay'] == delay]
                
                if h2_data and h3_data:
                    h2 = h2_data[0]
                    h3 = h3_data[0]
                    
                    f.write(f"HTTP/2: スループット {h2['throughput']:.1f} req/s, レイテンシ {h2['latency']:.1f}ms, 接続時間 {h2['connect_time']:.1f}ms\n")
                    f.write(f"HTTP/3: スループット {h3['throughput']:.1f} req/s, レイテンシ {h3['latency']:.1f}ms, 接続時間 {h3['connect_time']:.1f}ms\n")
                    
                    # 優位性計算
                    throughput_adv = ((h3['throughput'] - h2['throughput']) / h2['throughput']) * 100
                    latency_adv = ((h2['latency'] - h3['latency']) / h2['latency']) * 100
                    connect_adv = ((h2['connect_time'] - h3['connect_time']) / h2['connect_time']) * 100
                    
                    f.write(f"優位性: スループット {throughput_adv:+.1f}%, レイテンシ {latency_adv:+.1f}%, 接続時間 {connect_adv:+.1f}%\n")
        
        print(f"性能比較レポートを保存: {report_file}")

def main():
    parser = argparse.ArgumentParser(description='性能比較分析')
    parser.add_argument('--log_dir', required=True, help='ログディレクトリ')
    parser.add_argument('--test_conditions', nargs='+', 
                       default=['0:0:0', '50:0:0', '100:0:0', '150:0:0'],
                       help='テスト条件 (delay:loss:bandwidth)')
    
    args = parser.parse_args()
    
    analyzer = PerformanceComparisonAnalyzer(args.log_dir)
    
    print("性能比較分析を開始...")
    
    # テスト条件の解析と実行
    for condition in args.test_conditions:
        delay, loss, bandwidth = map(float, condition.split(':'))
        
        # HTTP/2テスト
        h2_result = analyzer.run_comprehensive_benchmark(delay, loss, bandwidth, 'http2')
        if h2_result:
            analyzer.results.append(h2_result)
        
        # HTTP/3テスト
        h3_result = analyzer.run_comprehensive_benchmark(delay, loss, bandwidth, 'http3')
        if h3_result:
            analyzer.results.append(h3_result)
    
    # グラフ生成
    analyzer.generate_performance_comparison_graphs()
    
    # レポート生成
    analyzer.generate_comparison_report()
    
    print("性能比較分析完了！")

if __name__ == "__main__":
    main() 