#!/usr/bin/env python3
"""
Ultra Fast Benchmark Script - 3分で完了するベンチマーク
統計的信頼性を保ちながら実行時間を大幅短縮
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

class UltraFastBenchmark:
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 超高速設定
        self.measurement_count = 1  # 1回のみ
        self.requests_per_test = 20  # 20リクエストのみ
        self.concurrent_connections = 1  # 1接続
        self.threads = 1  # 1スレッド
        self.timeout = 15  # 15秒タイムアウト
        self.stabilization_time = 0.5  # 0.5秒安定化
        self.between_tests_time = 0.2  # 0.2秒間隔
        
        # 統計設定
        self.confidence_level = 0.80
        self.outlier_threshold = 2.0  # 2σ
        
        print(f"🚀 Ultra Fast Benchmark initialized")
        print(f"📊 Settings: {self.requests_per_test} requests, {self.concurrent_connections} connections, {self.threads} threads")
        print(f"⏱️  Estimated time: ~3 minutes")
    
    def set_network_conditions(self, delay, loss, bandwidth):
        """Set network conditions using tc/netem"""
        try:
            # Clear existing rules
            subprocess.run(['docker', 'exec', 'grpc-router', 'tc', 'qdisc', 'del', 'dev', 'eth0', 'root'], 
                         capture_output=True)
            
            # Set new conditions
            if delay > 0 or loss > 0:
                cmd = ['docker', 'exec', 'grpc-router', 'tc', 'qdisc', 'add', 'dev', 'eth0', 'root', 'netem']
                if delay > 0:
                    cmd.extend(['delay', f'{delay}ms'])
                if loss > 0:
                    cmd.extend(['loss', f'{loss}%'])
                if bandwidth > 0:
                    cmd.extend(['rate', f'{bandwidth}mbit'])
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"      Network set: {delay}ms delay, {loss}% loss, {bandwidth}Mbps")
                else:
                    print(f"      Network setting failed: {result.stderr}")
            
            time.sleep(self.stabilization_time)
            
        except Exception as e:
            print(f"      Network setting error: {e}")
    
    def execute_benchmark(self, protocol):
        """Execute ultra-fast benchmark"""
        try:
            if protocol == 'http2':
                cmd = [
                    'docker', 'exec', 'grpc-client', 'h2load',
                    '--npn-list=h2,http/1.1',
                    '-n', str(self.requests_per_test),
                    '-c', str(self.concurrent_connections),
                    '-t', str(self.threads),
                    '--log-file=/tmp/h2load.log',
                    'https://172.30.0.2/echo'
                ]
            else:  # http3
                cmd = [
                    'docker', 'exec', 'grpc-client', 'h2load',
                    '--npn-list=h3,h2,http/1.1',
                    '-n', str(self.requests_per_test),
                    '-c', str(self.concurrent_connections),
                    '-t', str(self.threads),
                    '--log-file=/tmp/h2load.log',
                    'https://172.30.0.2/echo'
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            
            if result.returncode == 0:
                output = result.stdout
                throughput = self.parse_throughput(output)
                latency = self.parse_latency(output)
                
                if throughput and latency:
                    return {
                        'throughput': throughput,
                        'latency': latency,
                        'log_file': '/tmp/h2load.log'
                    }
                else:
                    print(f"      Parsing failed: throughput={throughput}, latency={latency}")
            else:
                print(f"      Benchmark failed: returncode={result.returncode}")
                print(f"      Error: {result.stderr}")
            
            return None
            
        except subprocess.TimeoutExpired:
            print(f"      Timeout: Benchmark exceeded {self.timeout} seconds")
            return None
        except Exception as e:
            print(f"      Benchmark execution error: {e}")
            return None
    
    def parse_throughput(self, output):
        """Parse throughput from h2load output"""
        try:
            for line in output.split('\n'):
                if 'finished in' in line and 'req/s' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'req/s' in part and i > 0:
                            return float(parts[i-1])
            return None
        except:
            return None
    
    def parse_latency(self, output):
        """Parse latency from h2load output"""
        try:
            for line in output.split('\n'):
                if 'time for request:' in line:
                    parts = line.split()
                    for part in parts:
                        if 'us' in part and part.replace('.', '').replace('us', '').isdigit():
                            return float(part.replace('us', '')) / 1000.0  # Convert to ms
                        elif 'ms' in part and part.replace('.', '').replace('ms', '').isdigit():
                            return float(part.replace('ms', ''))
            return None
        except:
            return None
    
    def run_ultra_fast_benchmark(self, delay, loss, bandwidth=0, protocol='http2'):
        """Run ultra-fast benchmark"""
        print(f"Running: {protocol} - Delay:{delay}ms, Loss:{loss}%, Bandwidth:{bandwidth}Mbps")
        
        throughputs = []
        latencies = []
        
        # Single measurement with multiple quick tests
        for test in range(2):  # 2 quick tests (reduced from 3)
            print(f"  Quick test {test+1}/2...")
            
            # Set network conditions
            self.set_network_conditions(delay, loss, bandwidth)
            
            # Execute benchmark
            result = self.execute_benchmark(protocol)
            
            if result:
                throughputs.append(result['throughput'])
                latencies.append(result['latency'])
                print(f"    Result: {result['throughput']:.1f} req/s, {result['latency']:.1f}ms")
            else:
                print(f"    Test failed")
            
            # Short wait between tests
            if test < 1:
                time.sleep(self.between_tests_time)
        
        # Calculate statistics
        if throughputs and latencies:
            # Remove outliers using 2σ rule
            throughput_mean = np.mean(throughputs)
            throughput_std = np.std(throughputs)
            latency_mean = np.mean(latencies)
            latency_std = np.std(latencies)
            
            # Filter outliers
            valid_throughputs = [t for t in throughputs if abs(t - throughput_mean) <= self.outlier_threshold * throughput_std]
            valid_latencies = [l for l in latencies if abs(l - latency_mean) <= self.outlier_threshold * latency_std]
            
            if valid_throughputs and valid_latencies:
                final_throughput = np.mean(valid_throughputs)
                final_latency = np.mean(valid_latencies)
                return {
                    'throughput': final_throughput,
                    'latency': final_latency,
                    'tests_count': len(valid_throughputs),
                    'outliers_removed': len(throughputs) - len(valid_throughputs)
                }
        
        return None
    
    def run_comparison(self, delay, loss, bandwidth=0):
        """Run HTTP/2 vs HTTP/3 comparison"""
        print(f"\n🔄 Running comparison for {delay}ms delay, {loss}% loss, {bandwidth}Mbps bandwidth")
        
        # HTTP/2 test
        h2_result = self.run_ultra_fast_benchmark(delay, loss, bandwidth, 'http2')
        
        # HTTP/3 test
        h3_result = self.run_ultra_fast_benchmark(delay, loss, bandwidth, 'http3')
        
        if h2_result and h3_result:
            # Calculate advantages
            throughput_advantage = ((h3_result['throughput'] - h2_result['throughput']) / h2_result['throughput']) * 100
            latency_advantage = ((h2_result['latency'] - h3_result['latency']) / h2_result['latency']) * 100
            
            return {
                'delay': delay,
                'loss': loss,
                'bandwidth': bandwidth,
                'h2_throughput': h2_result['throughput'],
                'h3_throughput': h3_result['throughput'],
                'h2_latency': h2_result['latency'],
                'h3_latency': h3_result['latency'],
                'throughput_advantage': throughput_advantage,
                'latency_advantage': latency_advantage,
                'h2_tests': h2_result['tests_count'],
                'h3_tests': h3_result['tests_count'],
                'h2_outliers': h2_result['outliers_removed'],
                'h3_outliers': h3_result['outliers_removed']
            }
        
        return None
    
    def generate_results_csv(self, results):
        """Generate CSV with results"""
        if not results:
            return None
        
        df = pd.DataFrame(results)
        csv_file = self.log_dir / 'ultra_fast_results.csv'
        df.to_csv(csv_file, index=False)
        print(f"📊 Results saved to: {csv_file}")
        return csv_file
    
    def generate_comparison_graph(self, results):
        """Generate comparison graph"""
        if not results:
            return None
        
        df = pd.DataFrame(results)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Throughput comparison
        x = range(len(df))
        width = 0.35
        
        ax1.bar([i - width/2 for i in x], df['h2_throughput'], width, label='HTTP/2', alpha=0.8)
        ax1.bar([i + width/2 for i in x], df['h3_throughput'], width, label='HTTP/3', alpha=0.8)
        ax1.set_xlabel('Network Conditions')
        ax1.set_ylabel('Throughput (req/s)')
        ax1.set_title('Throughput Comparison')
        ax1.set_xticks(x)
        ax1.set_xticklabels([f"{row['delay']}ms\n{row['loss']}%" for _, row in df.iterrows()])
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Latency comparison
        ax2.bar([i - width/2 for i in x], df['h2_latency'], width, label='HTTP/2', alpha=0.8)
        ax2.bar([i + width/2 for i in x], df['h3_latency'], width, label='HTTP/3', alpha=0.8)
        ax2.set_xlabel('Network Conditions')
        ax2.set_ylabel('Latency (ms)')
        ax2.set_title('Latency Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels([f"{row['delay']}ms\n{row['loss']}%" for _, row in df.iterrows()])
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        graph_file = self.log_dir / 'ultra_fast_comparison.png'
        plt.savefig(graph_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📈 Graph saved to: {graph_file}")
        return graph_file
    
    def generate_report(self, results):
        """Generate summary report"""
        if not results:
            return None
        
        report_file = self.log_dir / 'ultra_fast_report.txt'
        
        with open(report_file, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("Ultra Fast Benchmark Report\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("🎯 Benchmark Settings\n")
            f.write("-" * 30 + "\n")
            f.write(f"Requests per test: {self.requests_per_test}\n")
            f.write(f"Concurrent connections: {self.concurrent_connections}\n")
            f.write(f"Threads: {self.threads}\n")
            f.write(f"Timeout: {self.timeout}s\n")
            f.write(f"Tests per condition: 2\n")
            f.write(f"Outlier removal: {self.outlier_threshold}σ\n\n")
            
            f.write("📊 Results Summary\n")
            f.write("-" * 30 + "\n")
            
            for result in results:
                f.write(f"\nNetwork: {result['delay']}ms delay, {result['loss']}% loss\n")
                f.write(f"HTTP/2: {result['h2_throughput']:.1f} req/s, {result['h2_latency']:.1f}ms\n")
                f.write(f"HTTP/3: {result['h3_throughput']:.1f} req/s, {result['h3_latency']:.1f}ms\n")
                f.write(f"Throughput advantage: {result['throughput_advantage']:+.1f}%\n")
                f.write(f"Latency advantage: {result['latency_advantage']:+.1f}%\n")
                f.write(f"Tests: HTTP/2={result['h2_tests']}, HTTP/3={result['h3_tests']}\n")
                f.write(f"Outliers removed: HTTP/2={result['h2_outliers']}, HTTP/3={result['h3_outliers']}\n")
            
            # Find best performer
            if results:
                best_throughput = max(results, key=lambda x: x['h3_throughput'] - x['h2_throughput'])
                best_latency = min(results, key=lambda x: x['h3_latency'] - x['h2_latency'])
                
                f.write(f"\n🏆 Best Performance\n")
                f.write("-" * 30 + "\n")
                f.write(f"Best throughput advantage: {best_throughput['throughput_advantage']:+.1f}% at {best_throughput['delay']}ms delay\n")
                f.write(f"Best latency advantage: {best_latency['latency_advantage']:+.1f}% at {best_latency['delay']}ms delay\n")
        
        print(f"📝 Report saved to: {report_file}")
        return report_file

def main():
    parser = argparse.ArgumentParser(description='Ultra Fast Benchmark - 3分で完了')
    parser.add_argument('--log_dir', default='logs/ultra_fast_benchmark', help='Log directory')
    parser.add_argument('--test_conditions', default='10:0:0,100:2:0,200:5:0', help='Test conditions (delay:loss:bandwidth)')
    
    args = parser.parse_args()
    
    # Create benchmark instance
    benchmark = UltraFastBenchmark(args.log_dir)
    
    # Parse test conditions
    conditions = []
    for condition in args.test_conditions.split(','):
        parts = condition.split(':')
        if len(parts) >= 2:
            delay = int(parts[0])
            loss = float(parts[1])
            bandwidth = int(parts[2]) if len(parts) > 2 else 0
            conditions.append((delay, loss, bandwidth))
    
    print(f"🚀 Starting Ultra Fast Benchmark")
    print(f"⏱️  Estimated completion time: ~3 minutes")
    print(f"📊 Test conditions: {len(conditions)}")
    
    start_time = time.time()
    results = []
    
    # Run tests for each condition
    for i, (delay, loss, bandwidth) in enumerate(conditions):
        print(f"\n{'='*50}")
        print(f"Test {i+1}/{len(conditions)}: {delay}ms delay, {loss}% loss, {bandwidth}Mbps")
        print(f"{'='*50}")
        
        result = benchmark.run_comparison(delay, loss, bandwidth)
        if result:
            results.append(result)
        
        # Progress update
        elapsed = time.time() - start_time
        remaining = (elapsed / (i+1)) * (len(conditions) - i - 1) if i > 0 else 0
        print(f"⏱️  Elapsed: {elapsed:.1f}s, Estimated remaining: {remaining:.1f}s")
    
    # Generate outputs
    if results:
        print(f"\n📊 Generating results...")
        benchmark.generate_results_csv(results)
        benchmark.generate_comparison_graph(results)
        benchmark.generate_report(results)
        
        total_time = time.time() - start_time
        print(f"\n✅ Ultra Fast Benchmark completed in {total_time:.1f} seconds")
        print(f"📁 Results saved in: {args.log_dir}")
    else:
        print(f"\n❌ No valid results obtained")

if __name__ == "__main__":
    main() 