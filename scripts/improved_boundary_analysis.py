#!/usr/bin/env python3
"""
Improved HTTP/2 vs HTTP/3 Performance Boundary Analysis
信頼性の高い境界値分析スクリプト
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

# 日本語フォント設定
plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Hiragino Sans']
plt.rcParams['axes.unicode_minus'] = False

class ImprovedBoundaryAnalyzer:
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.results = []
        self.boundaries = []
        
    def run_reliable_benchmark(self, delay, loss, bandwidth=0, protocol='http2'):
        """信頼性の高いベンチマーク実行"""
        print(f"実行中: {protocol} - 遅延:{delay}ms, 損失:{loss}%, 帯域:{bandwidth}Mbps")
        
        # 複数回測定で平均化
        measurements = []
        for i in range(3):  # 3回測定
            print(f"  測定 {i+1}/3...")
            
            # ネットワーク条件設定
            self.set_network_conditions(delay, loss, bandwidth)
            
            # システム安定化
            time.sleep(10)
            
            # ベンチマーク実行
            result = self.execute_benchmark(protocol)
            if result:
                measurements.append(result)
                print(f"    結果: {result['throughput']:.1f} req/s, {result['latency']:.1f}ms")
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
        std_throughput = np.std([m['throughput'] for m in valid_measurements])
        
        print(f"  最終結果: {avg_throughput:.1f} ± {std_throughput:.1f} req/s")
        
        return {
            'protocol': protocol,
            'delay': delay,
            'loss': loss,
            'bandwidth': bandwidth,
            'throughput': avg_throughput,
            'latency': avg_latency,
            'throughput_std': std_throughput,
            'measurement_count': len(valid_measurements)
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
                    '-n', '10000',
                    '-c', '50',
                    '-t', '10',
                    'https://172.30.0.2/echo'
                ]
            else:  # http3
                cmd = [
                    'docker', 'exec', 'grpc-client', 'h2load',
                    '--alpn-list=h3,h2,http/1.1',
                    '-n', '10000',
                    '-c', '50',
                    '-t', '10',
                    'https://172.30.0.2/echo'
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # 結果解析
                output = result.stdout
                throughput = self.parse_throughput(output)
                latency = self.parse_latency(output)
                
                if throughput and latency:
                    return {
                        'throughput': throughput,
                        'latency': latency
                    }
                else:
                    print(f"      解析失敗: throughput={throughput}, latency={latency}")
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
    
    def detect_reliable_boundaries(self, threshold=5.0, confidence_level=0.95):
        """信頼性の高い境界値検出"""
        boundaries = []
        
        print(f"\n境界値検出開始 (閾値: {threshold}%, 信頼度: {confidence_level*100:.0f}%)")
        
        # 同じ条件下でのHTTP/2とHTTP/3の比較
        conditions = set()
        for result in self.results:
            conditions.add((result['delay'], result['loss'], result['bandwidth']))
        
        for delay, loss, bandwidth in conditions:
            h2_results = [r for r in self.results if r['protocol'] == 'http2' and 
                         r['delay'] == delay and r['loss'] == loss and r['bandwidth'] == bandwidth]
            h3_results = [r for r in self.results if r['protocol'] == 'http3' and 
                         r['delay'] == delay and r['loss'] == loss and r['bandwidth'] == bandwidth]
            
            if len(h2_results) == 0 or len(h3_results) == 0:
                print(f"  条件 ({delay}ms, {loss}%, {bandwidth}Mbps): データ不足")
                continue
            
            h2_throughput = h2_results[0]['throughput']
            h3_throughput = h3_results[0]['throughput']
            h2_std = h2_results[0]['throughput_std']
            h3_std = h3_results[0]['throughput_std']
            
            print(f"  条件 ({delay}ms, {loss}%, {bandwidth}Mbps):")
            print(f"    HTTP/2: {h2_throughput:.1f} ± {h2_std:.1f} req/s")
            print(f"    HTTP/3: {h3_throughput:.1f} ± {h3_std:.1f} req/s")
            
            # 統計的有意性検定
            is_significant = self.is_statistically_significant(h2_throughput, h3_throughput, h2_std, h3_std, confidence_level)
            
            if is_significant:
                diff_pct = ((h2_throughput - h3_throughput) / h3_throughput) * 100
                print(f"    性能差: {diff_pct:.1f}% (統計的有意)")
                
                # 境界値判定
                if abs(diff_pct) <= threshold or diff_pct < 0:
                    boundaries.append({
                        'delay': delay,
                        'loss': loss,
                        'bandwidth': bandwidth,
                        'h2_throughput': h2_throughput,
                        'h3_throughput': h3_throughput,
                        'h2_std': h2_std,
                        'h3_std': h3_std,
                        'diff_pct': diff_pct,
                        'superior_protocol': 'HTTP/3' if diff_pct < 0 else 'HTTP/2',
                        'confidence_level': confidence_level
                    })
                    print(f"    → 境界値検出!")
                else:
                    print(f"    → 閾値超過 ({threshold}%)")
            else:
                print(f"    → 統計的に有意でない")
        
        return boundaries
    
    def is_statistically_significant(self, h2_mean, h3_mean, h2_std, h3_std, confidence_level):
        """統計的有意性検定"""
        try:
            # t検定による有意性判定
            # 簡易版: 信頼区間の重複チェック
            h2_ci = 1.96 * h2_std  # 95%信頼区間
            h3_ci = 1.96 * h3_std
            
            # 信頼区間が重複しない場合、統計的有意
            return abs(h2_mean - h3_mean) > (h2_ci + h3_ci)
        except:
            return True  # エラーの場合は有意とみなす
    
    def generate_improved_graphs(self):
        """改善されたグラフ生成"""
        if not self.results:
            print("データが不足しています")
            return
        
        df = pd.DataFrame(self.results)
        
        # グラフ設定
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 信頼性付きスループット比較
        ax1 = axes[0, 0]
        h2_data = df[df['protocol'] == 'http2']
        h3_data = df[df['protocol'] == 'http3']
        
        # エラーバー付きプロット
        ax1.errorbar(h2_data['delay'], h2_data['throughput'], 
                    yerr=h2_data['throughput_std'], fmt='o', 
                    label='HTTP/2', capsize=5, capthick=2)
        ax1.errorbar(h3_data['delay'], h3_data['throughput'], 
                    yerr=h3_data['throughput_std'], fmt='s', 
                    label='HTTP/3', capsize=5, capthick=2)
        
        # 境界値をマーク
        if self.boundaries:
            boundary_df = pd.DataFrame(self.boundaries)
            ax1.scatter(boundary_df['delay'], boundary_df['h3_throughput'], 
                       c='red', s=200, marker='*', edgecolors='black', 
                       linewidth=2, label='境界値', zorder=5)
        
        ax1.set_xlabel('遅延 (ms)')
        ax1.set_ylabel('スループット (req/s)')
        ax1.set_title('信頼性付き HTTP/2 vs HTTP/3 スループット比較')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 信頼区間付き性能差
        ax2 = axes[0, 1]
        performance_diff = []
        for delay in df['delay'].unique():
            delay_data = df[df['delay'] == delay]
            h2_avg = delay_data[delay_data['protocol'] == 'http2']['throughput'].mean()
            h3_avg = delay_data[delay_data['protocol'] == 'http3']['throughput'].mean()
            h2_std = delay_data[delay_data['protocol'] == 'http2']['throughput_std'].mean()
            h3_std = delay_data[delay_data['protocol'] == 'http3']['throughput_std'].mean()
            
            if h3_avg > 0:
                diff = ((h2_avg - h3_avg) / h3_avg) * 100
                # 信頼区間の計算
                diff_std = np.sqrt((h2_std/h2_avg)**2 + (h3_std/h3_avg)**2) * 100
                performance_diff.append({
                    'delay': delay, 
                    'diff': diff, 
                    'diff_std': diff_std
                })
        
        if performance_diff:
            diff_df = pd.DataFrame(performance_diff)
            ax2.errorbar(diff_df['delay'], diff_df['diff'], 
                        yerr=diff_df['diff_std'], fmt='o', capsize=5)
            ax2.axhline(y=0, color='red', linestyle='--', alpha=0.7)
            ax2.axhline(y=5, color='orange', linestyle=':', alpha=0.7)
            ax2.axhline(y=-5, color='orange', linestyle=':', alpha=0.7)
        
        ax2.set_xlabel('遅延 (ms)')
        ax2.set_ylabel('性能差 (%)')
        ax2.set_title('信頼区間付き性能差異')
        ax2.grid(True, alpha=0.3)
        
        # 3. 測定信頼性マップ
        ax3 = axes[1, 0]
        reliability = df.groupby(['delay', 'protocol'])['measurement_count'].mean().reset_index()
        reliability_pivot = reliability.pivot(index='delay', columns='protocol', values='measurement_count')
        reliability_pivot.plot(kind='bar', ax=ax3)
        ax3.set_xlabel('遅延 (ms)')
        ax3.set_ylabel('有効測定回数')
        ax3.set_title('測定信頼性')
        ax3.legend()
        
        # 4. 標準偏差の比較
        ax4 = axes[1, 1]
        std_comparison = df.groupby(['delay', 'protocol'])['throughput_std'].mean().reset_index()
        std_pivot = std_comparison.pivot(index='delay', columns='protocol', values='throughput_std')
        std_pivot.plot(kind='bar', ax=ax4)
        ax4.set_xlabel('遅延 (ms)')
        ax4.set_ylabel('スループット標準偏差')
        ax4.set_title('測定安定性比較')
        ax4.legend()
        
        plt.tight_layout()
        plt.savefig(self.log_dir / 'improved_boundary_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"改善されたグラフを保存: {self.log_dir / 'improved_boundary_analysis.png'}")
    
    def generate_reliability_report(self):
        """信頼性レポート生成"""
        report_file = self.log_dir / "reliability_report.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("信頼性向上された境界値分析レポート\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("🔧 改善点\n")
            f.write("-" * 30 + "\n")
            f.write("• 複数回測定による平均化\n")
            f.write("• 外れ値除去（3σルール）\n")
            f.write("• 統計的有意性検定\n")
            f.write("• 信頼区間の計算\n")
            f.write("• 測定安定性の評価\n\n")
            
            f.write("📊 測定統計\n")
            f.write("-" * 30 + "\n")
            f.write(f"総測定数: {len(self.results)}\n")
            f.write(f"境界値数: {len(self.boundaries)}\n")
            
            if self.results:
                f.write("\n📈 詳細測定結果\n")
                f.write("-" * 30 + "\n")
                for result in self.results:
                    f.write(f"{result['protocol'].upper()}: {result['delay']}ms, {result['loss']}%\n")
                    f.write(f"  スループット: {result['throughput']:.1f} ± {result['throughput_std']:.1f} req/s\n")
                    f.write(f"  レイテンシ: {result['latency']:.1f} ms\n")
                    f.write(f"  有効測定回数: {result['measurement_count']}/3\n\n")
            
            if self.boundaries:
                f.write("\n🔍 信頼性の高い境界値\n")
                f.write("-" * 30 + "\n")
                for i, boundary in enumerate(self.boundaries, 1):
                    f.write(f"{i}. 遅延: {boundary['delay']}ms, 損失: {boundary['loss']}%\n")
                    f.write(f"   HTTP/2: {boundary['h2_throughput']:.1f} ± {boundary['h2_std']:.1f} req/s\n")
                    f.write(f"   HTTP/3: {boundary['h3_throughput']:.1f} ± {boundary['h3_std']:.1f} req/s\n")
                    f.write(f"   性能差: {boundary['diff_pct']:.1f}% (信頼度: {boundary['confidence_level']*100:.0f}%)\n")
                    f.write(f"   優位プロトコル: {boundary['superior_protocol']}\n\n")
            else:
                f.write("\n❌ 境界値は検出されませんでした\n")
                f.write("   → すべての条件下で明確な性能差が検出されました\n")
                f.write("   → または、統計的有意性の条件を満たしませんでした\n\n")
        
        print(f"信頼性レポートを保存: {report_file}")
    
    def save_detailed_data(self):
        """詳細データをJSON形式で保存"""
        data_file = self.log_dir / "detailed_measurement_data.json"
        
        # 結果データをJSON形式で保存
        json_data = {
            'measurements': self.results,
            'boundaries': self.boundaries,
            'summary': {
                'total_measurements': len(self.results),
                'boundary_count': len(self.boundaries),
                'protocols_tested': list(set([r['protocol'] for r in self.results])),
                'conditions_tested': list(set([(r['delay'], r['loss'], r['bandwidth']) for r in self.results]))
            }
        }
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"詳細データを保存: {data_file}")

def main():
    parser = argparse.ArgumentParser(description='信頼性向上された境界値分析')
    parser.add_argument('--log_dir', required=True, help='ログディレクトリ')
    parser.add_argument('--test_conditions', nargs='+', 
                       default=['0:0:0', '10:0:0', '20:0:0', '50:1:0', '100:2:0'],
                       help='テスト条件 (delay:loss:bandwidth)')
    
    args = parser.parse_args()
    
    analyzer = ImprovedBoundaryAnalyzer(args.log_dir)
    
    print("信頼性向上された境界値分析を開始...")
    
    # テスト条件の解析と実行
    for condition in args.test_conditions:
        delay, loss, bandwidth = map(float, condition.split(':'))
        
        # HTTP/2テスト
        h2_result = analyzer.run_reliable_benchmark(delay, loss, bandwidth, 'http2')
        if h2_result:
            analyzer.results.append(h2_result)
        
        # HTTP/3テスト
        h3_result = analyzer.run_reliable_benchmark(delay, loss, bandwidth, 'http3')
        if h3_result:
            analyzer.results.append(h3_result)
    
    # 境界値検出
    analyzer.boundaries = analyzer.detect_reliable_boundaries()
    
    # グラフ生成
    analyzer.generate_improved_graphs()
    
    # レポート生成
    analyzer.generate_reliability_report()
    
    # 詳細データ保存
    analyzer.save_detailed_data()
    
    print("信頼性向上された境界値分析完了！")

if __name__ == "__main__":
    main() 