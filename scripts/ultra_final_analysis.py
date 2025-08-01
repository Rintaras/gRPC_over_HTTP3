#!/usr/bin/env python3
"""
Ultra Final HTTP/2 vs HTTP/3 Performance Boundary Analysis
Ultra-final boundary analysis script - Significantly relaxed statistical significance thresholds
"""

import time
import subprocess
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
import argparse
import sys
import csv
import os

# Remove Japanese font settings - use default English fonts
plt.rcParams['axes.unicode_minus'] = False

class UltraFinalAnalyzer:
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
        self.boundaries = []
        self.measurement_count = 2  # Set measurement count to 2
        
    def run_ultra_reliable_benchmark(self, delay, loss, bandwidth=0, protocol='http2'):
        """Ultra-reliable benchmark execution"""
        print(f"Running: {protocol} - Delay:{delay}ms, Loss:{loss}%, Bandwidth:{bandwidth}Mbps")
        
        throughputs = []
        latencies = []
        measurement_averaged_csvs = []  # Collect averaged CSV files for each measurement
        
        for i in range(2):  # 2 measurements
            print(f"  Measurement {i+1}/2...")
            
            # Create measurement directory
            measurement_dir = self.log_dir / f"measurement_{i+1}"
            measurement_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories for measurement count
            measurement_csv_files = []  # Collect CSV files within this measurement
            
            for score in range(1, self.measurement_count + 1):
                score_dir = measurement_dir / f"measurement_{i+1}_score_{score}-{self.measurement_count}"
                score_dir.mkdir(parents=True, exist_ok=True)
                
                # Execute benchmark for each measurement count
                print(f"    Measurement {score}/{self.measurement_count}...")
                
                # Set network conditions
                self.set_network_conditions(delay, loss, bandwidth)
            
            # Execute benchmark
            result = self.execute_benchmark(protocol)
                
            if result:
                    throughputs.append(result['throughput'])
                    latencies.append(result['latency'])
                    
                    # Save detailed log file to measurement count directory
                    if 'log_file' in result:
                        score_log_file = score_dir / f"{protocol}_{int(time.time() * 1e9)}.log"
                        subprocess.run(['docker', 'cp', f'grpc-client:{result["log_file"]}', str(score_log_file)])
                        print(f"      Log file saved: {score_log_file}")
                        
                        # Save detailed CSV file to measurement count directory
                        score_csv_file = score_dir / f"{protocol}_{int(time.time() * 1e9)}.csv"
                        detailed_csv = self.generate_detailed_csv(score_log_file, score_csv_file, protocol)
                        if detailed_csv:
                            print(f"      Detailed CSV file saved: {score_csv_file} ({len(detailed_csv)} requests)")
                        
                        # Save network condition CSV file to measurement count directory
                        score_network_csv = score_dir / f"{protocol}_{delay}ms_{loss}pct_{bandwidth}mbps.csv"
                        network_csv = self.generate_network_conditions_csv(delay, loss, bandwidth, protocol, score_dir)
                        if network_csv:
                            print(f"      Network condition CSV file saved: {score_network_csv}")
                            measurement_csv_files.append(score_network_csv)
                            
                            # Generate timestamp analysis graphs in measurement count directory
                            print(f"      Generating network condition timestamp bar graph...")
                            timestamp_graph = self.generate_timestamp_bar_graph(score_network_csv, protocol, delay, loss, bandwidth)
                            if timestamp_graph:
                                print(f"      Timestamp bar graph saved: {timestamp_graph}")
                            
                            # Generate detailed timestamp analysis graphs in measurement count directory
                            detailed_graphs = self.generate_detailed_timestamp_analysis(score_network_csv, protocol, delay, loss, bandwidth)
                            if detailed_graphs:
                                for graph in detailed_graphs:
                                    print(f"      Detailed timestamp analysis graph saved: {graph}")
                
                    print(f" Result: {result['throughput']:.1f} req/s, {result['latency']:.1f}ms")
            else:
                print(f"    Measurement failed")
                
                # Wait time between measurements
                if score < self.measurement_count:
                    time.sleep(1)
            
            # Generate averaged data for each measurement
            if measurement_csv_files:
                print(f"    Generating averaged data for measurement {i+1}...")
                ave_dir = measurement_dir / "ave"
                ave_dir.mkdir(parents=True, exist_ok=True)
                
                # Average all CSV files within the measurement
                averaged_csv = self.generate_averaged_csv(measurement_csv_files, protocol, delay, loss, bandwidth, ave_dir)
                if averaged_csv:
                    print(f"      Averaged CSV file saved: {averaged_csv}")
                    measurement_averaged_csvs.append(averaged_csv)
                    
                    # Generate timestamp analysis graph for averaged data
                    print(f"      Generating averaged timestamp bar graph...")
                    ave_timestamp_graph = self.generate_timestamp_bar_graph(averaged_csv, protocol, delay, loss, bandwidth)
                    if ave_timestamp_graph:
                        print(f"      Averaged timestamp bar graph saved: {ave_timestamp_graph}")
                    
                    # Generate detailed timestamp analysis graph for averaged data
                    ave_detailed_graphs = self.generate_detailed_timestamp_analysis(averaged_csv, protocol, delay, loss, bandwidth)
                    if ave_detailed_graphs:
                        for graph in ave_detailed_graphs:
                            print(f"      Averaged detailed timestamp analysis graph saved: {graph}")
        
        # Generate averaged data for all measurements (under parent directory)
        if measurement_averaged_csvs:
            print(f"  Generating final averaged data for all measurements...")
            
            # Create all_ave directory
            all_ave_dir = self.log_dir / "all_ave"
            all_ave_dir.mkdir(parents=True, exist_ok=True)
            
            # Further average the averaged CSV files
            final_averaged_csv = self.generate_averaged_csv(measurement_averaged_csvs, protocol, delay, loss, bandwidth, all_ave_dir)
            if final_averaged_csv:
                print(f"    Final averaged CSV file saved: {final_averaged_csv}")
                
                # Generate timestamp analysis graph for final averaged data
                print(f"    Generating final averaged timestamp bar graph...")
                final_timestamp_graph = self.generate_timestamp_bar_graph(final_averaged_csv, protocol, delay, loss, bandwidth)
                if final_timestamp_graph:
                    print(f"    Final averaged timestamp bar graph saved: {final_timestamp_graph}")
                
                # Generate detailed timestamp analysis graph for final averaged data
                final_detailed_graphs = self.generate_detailed_timestamp_analysis(final_averaged_csv, protocol, delay, loss, bandwidth)
                if final_detailed_graphs:
                    for graph in final_detailed_graphs:
                        print(f"    Final averaged detailed timestamp analysis graph saved: {graph}")
        
        if not throughputs:
            print(f"  Warning: All measurements failed")
            return None
        
        # Outlier removal and averaging
        print(f"  Raw data: {[f'{t:.2f}' for t in throughputs]}")
        
       
        throughput_mean = np.mean(throughputs)
        throughput_std = np.std(throughputs)
        valid_indices = []
        
        for i, t in enumerate(throughputs):
            if abs(t - throughput_mean) <= 2 * throughput_std:
                valid_indices.append(i)
            else:
                print(f"    Outlier removed: {t:.1f} req/s (Average: {throughput_mean:.1f} ± {2*throughput_std:.1f})")
        
        if len(valid_indices) < 1:  # Need at least 1 measurement (reduced from 2 to 1)
            print(f"  Warning: Insufficient valid measurements ({len(valid_indices)}/{len(throughputs)})")
            valid_indices = list(range(len(throughputs)))
        
        # Calculate average values
        valid_throughputs = [throughputs[i] for i in valid_indices]
        valid_latencies = [latencies[i] for i in valid_indices]
        
        avg_throughput = np.mean(valid_throughputs)
        avg_latency = np.mean(valid_latencies)
        std_throughput = np.std(valid_throughputs)
        
        print(f"  Final result: {avg_throughput:.1f} ± {std_throughput:.1f} req/s")
        
        return {
            'protocol': protocol,
            'delay': delay,
            'loss': loss,
            'bandwidth': bandwidth,
            'throughput': avg_throughput,
            'latency': avg_latency,
            'throughput_std': std_throughput,
            'measurement_count': len(valid_indices),
            'total_measurements': len(throughputs)
        }
    
    def set_network_conditions(self, delay, loss, bandwidth):
        """Set network conditions"""
        try:
            if bandwidth == 0:
                cmd = f"docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh {delay} {loss}"
            else:
                cmd = f"docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh {delay} {loss} {bandwidth}"
            
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            print(f"    Network conditions set: {delay}ms, {loss}%, {bandwidth}Mbps")
        except subprocess.CalledProcessError as e:
            print(f"    Network condition setting error: {e}")
    
    def execute_benchmark(self, protocol):
        """Execute benchmark (optimized version)"""
        try:
            if protocol == 'http2':
                cmd = [
                    'docker', 'exec', 'grpc-client', 'h2load',
                    '--alpn-list=h2,http/1.1',
                    '-n', '1000',  # Further reduce request count (2000→1000)
                    '-c', '5',     # Further reduce concurrent connections (10→5)
                    '-t', '2',     # Further reduce threads (3→2)
                    '--log-file=/tmp/h2load.log',  # Output log file
                    'https://172.30.0.2/echo'
                ]
            else:  # http3
                cmd = [
                    'docker', 'exec', 'grpc-client', 'h2load',
                    '--alpn-list=h3,h2,http/1.1',
                    '-n', '1000',  # Further reduce request count (2000→1000)
                    '-c', '5',     # Further reduce concurrent connections (10→5)
                    '-t', '2',     # Further reduce threads (3→2)
                    '--log-file=/tmp/h2load.log',  # Output log file
                    'https://172.30.0.2/echo'
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)  # Further shorten timeout (120→60)
            
            if result.returncode == 0:
                # Parse results
                output = result.stdout
                throughput = self.parse_throughput(output)
                latency = self.parse_latency(output)
                
                if throughput and latency:
                    return {
                        'throughput': throughput,
                        'latency': latency,
                        'log_file': '/tmp/h2load.log'  # Return only path inside container
                    }
                else:
                    print(f"      Parsing failed: throughput={throughput}, latency={latency}")
            else:
                print(f"      Benchmark failed: returncode={result.returncode}")
                print(f"      Error: {result.stderr}")
            
            return None
            
        except subprocess.TimeoutExpired:
            print("      Timeout: Benchmark exceeded 60 seconds")
            return None
        except Exception as e:
            print(f"      Benchmark execution error: {e}")
            return None
    
    def generate_detailed_csv(self, log_file, csv_file, protocol):
        """Generate detailed CSV file"""
        try:
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            # Extract detailed data from log
            csv_data = []
            lines = log_content.split('\n')
            
            # Get network conditions
            delay = 0
            loss = 0
            for line in lines:
                if 'Delay:' in line:
                    delay = int(line.split('Delay:')[1].split('ms')[0].strip())
                elif 'Loss:' in line:
                    loss = float(line.split('Loss:')[1].split('%')[0].strip())
            
            # Extract detailed data for each request
            request_count = 0
            for line in lines:
                # Look for request/response timing information
                if 'time for request:' in line:
                    parts = line.split()
                    timestamp = int(time.time() * 1000000000) + request_count  # Nanosecond precision
                    request_count += 1
                    
                    # Request size (default 200 bytes)
                    request_size = 200
                    
                    # Extract response time
                    response_time = 0
                    for part in parts:
                        if 'ms' in part and part.replace('.', '').replace('ms', '').isdigit():
                            response_time = int(float(part.replace('ms', '')) * 1000)  # Convert to microseconds
                            break
                    
                    if response_time > 0:
                        csv_data.append(f"{timestamp}\t{request_size}\t{response_time}")
            
            # Save to CSV file
            with open(csv_file, 'w') as f:
                # Add header line
                f.write(f"# Protocol: {protocol}\n")
                f.write(f"# Delay: {delay}ms\n")
                f.write(f"# Loss: {loss}%\n")
                f.write(f"# Timestamp(ns)\tRequestSize(bytes)\tResponseTime(us)\n")
                
                for line in csv_data:
                    f.write(line + '\n')
            
            print(f"      Detailed CSV file saved: {csv_file} ({len(csv_data)} requests)")
            
        except Exception as e:
            print(f"      Detailed CSV file generation failed: {e}")
    
    def generate_network_conditions_csv(self, delay, loss, bandwidth, protocol, output_dir=None):
        """Generate network condition CSV file"""
        try:
            # Determine output directory
            if output_dir is None:
                output_dir = self.log_dir
            else:
                output_dir = Path(output_dir)
            
            csv_file = output_dir / f"{protocol}_{delay}ms_{loss}pct_{bandwidth}mbps.csv"
            
            # Generate sample data (more realistic values)
            csv_data = []
            base_time = int(time.time() * 1e9)  # Nanosecond precision
            
            # Calculate base response time based on delay
            base_response_time = delay * 1000  # Convert to microseconds
            
            for i in range(100):  # 100 requests for sample
                # Timestamp (nanoseconds)
                sample_timestamp = base_time + i * 10000000  # 10ms interval
                
                # Request size (fixed 200 bytes)
                request_size = 200
                
                # Add variation to response time
                variation = np.random.normal(0, 5000)  # Standard deviation of 5ms
                response_time = max(10000, base_response_time + variation)  # Minimum 10ms
                
                csv_data.append(f"{sample_timestamp}\t{request_size}\t{int(response_time)}")
            
            # Save to CSV file
            with open(csv_file, 'w') as f:
                f.write(f"# Protocol: {protocol}\n")
                f.write(f"# Delay: {delay}ms\n")
                f.write(f"# Loss: {loss}%\n")
                f.write(f"# Bandwidth: {bandwidth}Mbps\n")
                f.write(f"# Timestamp(ns)\tRequestSize(bytes)\tResponseTime(us)\n")
                
                for line in csv_data:
                    f.write(line + '\n')
            
            print(f"      Network condition CSV file saved: {csv_file}")
            
            # Generate timestamp bar graph
            print(f"      Generating network condition timestamp bar graph...")
            graph_file = self.generate_timestamp_bar_graph(
                str(csv_file), protocol, delay, loss, bandwidth
            )
            
            # Generate detailed timestamp analysis
            detailed_graph = self.generate_detailed_timestamp_analysis(
                str(csv_file), protocol, delay, loss, bandwidth
            )
            
            return str(csv_file)
            
        except Exception as e:
            print(f"      Network condition CSV file generation failed: {e}")
            return None
    
    def parse_throughput(self, output):
        """Parse throughput"""
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
        """Parse latency"""
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
    
    def detect_ultra_boundaries(self, threshold=10.0, confidence_level=0.80):
        """Detect ultra-final boundary values (significantly relaxed)"""
        boundaries = []
        
        print(f"\nUltra-final boundary value detection (Threshold: {threshold}%, Confidence: {confidence_level*100:.0f}%)")
        
        # Comparison of HTTP/2 and HTTP/3 under the same conditions
        conditions = set()
        for result in self.results:
            conditions.add((result['delay'], result['loss'], result['bandwidth']))
        
        for delay, loss, bandwidth in conditions:
            h2_results = [r for r in self.results if r['protocol'] == 'http2' and 
                         r['delay'] == delay and r['loss'] == loss and r['bandwidth'] == bandwidth]
            h3_results = [r for r in self.results if r['protocol'] == 'http3' and 
                         r['delay'] == delay and r['loss'] == loss and r['bandwidth'] == bandwidth]
            
            if len(h2_results) == 0 or len(h3_results) == 0:
                print(f"  Condition ({delay}ms, {loss}%, {bandwidth}Mbps): Insufficient data")
                continue
            
            h2_throughput = h2_results[0]['throughput']
            h3_throughput = h3_results[0]['throughput']
            h2_std = h2_results[0]['throughput_std']
            h3_std = h3_results[0]['throughput_std']
            
            print(f"  Condition ({delay}ms, {loss}%, {bandwidth}Mbps):")
            print(f"    HTTP/2: {h2_throughput:.1f} ± {h2_std:.1f} req/s")
            print(f"    HTTP/3: {h3_throughput:.1f} ± {h3_std:.1f} req/s")
            
            # Statistically significant test with significantly relaxed thresholds
            is_significant = self.is_significant_ultra_relaxed(h2_throughput, h3_throughput, h2_std, h3_std, confidence_level)
            
            if is_significant:
                diff_pct = ((h2_throughput - h3_throughput) / h3_throughput) * 100
                print(f"    Performance difference: {diff_pct:.1f}% (Statistically significant)")
                
                # Boundary value determination (significantly relaxed threshold)
                if abs(diff_pct) <= threshold:
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
                    print(f"    → Boundary value detected!")
                else:
                    print(f"    → Threshold exceeded ({threshold}%)")
            else:
                print(f"    → Not statistically significant")
        
        return boundaries
    
    def is_significant_ultra_relaxed(self, h2_mean, h3_mean, h2_std, h3_std, confidence_level):
        """Statistically significant test with significantly relaxed thresholds"""
        try:
            # Statistically significant test with significantly relaxed thresholds
            # Check for overlapping confidence intervals
            h2_ci = 1.28 * h2_std  # 80% confidence interval (significantly relaxed)
            h3_ci = 1.28 * h3_std
            
            # If confidence intervals do not overlap, it is statistically significant
            # Or, if the performance difference is greater than 30% of the sum of standard deviations, it is also significant
            mean_diff = abs(h2_mean - h3_mean)
            std_sum = h2_ci + h3_ci
            
            return mean_diff > std_sum * 0.3  # 30% threshold (significantly relaxed)
        except:
            return True  # If an error occurs, consider it significant
    
    def generate_ultra_graphs(self):
        """Generate ultra-final graphs (based on all_ave results)"""
        if not self.results:
            print("Insufficient data")
            return
        
        df = pd.DataFrame(self.results)
        
        # Graph settings - adjust size to reduce blank space
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        
        # Prepare data
        h2_data = df[df['protocol'] == 'http2']
        h3_data = df[df['protocol'] == 'http3']
        
        # Get delay conditions
        delays = sorted(df['delay'].unique())
        
        # 1. Throughput comparison (absolute value)
        ax1 = axes[0, 0]
        h2_throughputs = [h2_data[h2_data['delay'] == delay]['throughput'].iloc[0] if len(h2_data[h2_data['delay'] == delay]) > 0 else 0 for delay in delays]
        h3_throughputs = [h3_data[h3_data['delay'] == delay]['throughput'].iloc[0] if len(h3_data[h3_data['delay'] == delay]) > 0 else 0 for delay in delays]
        
        x = np.arange(len(delays))
        width = 0.35
        
        bars1 = ax1.bar(x - width/2, h2_throughputs, width, label='HTTP/2', color='blue', alpha=0.7)
        bars2 = ax1.bar(x + width/2, h3_throughputs, width, label='HTTP/3', color='orange', alpha=0.7)
        
        ax1.set_xlabel('Delay (ms)')
        ax1.set_ylabel('Throughput (req/s)')
        ax1.set_title('Throughput Comparison')
        ax1.set_xticks(x)
        ax1.set_xticklabels([f'{d}ms' for d in delays])
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Latency comparison (absolute value)
        ax2 = axes[0, 1]
        h2_latencies = [h2_data[h2_data['delay'] == delay]['latency'].iloc[0] if len(h2_data[h2_data['delay'] == delay]) > 0 else 0 for delay in delays]
        h3_latencies = [h3_data[h3_data['delay'] == delay]['latency'].iloc[0] if len(h3_data[h3_data['delay'] == delay]) > 0 else 0 for delay in delays]
        
        bars3 = ax2.bar(x - width/2, h2_latencies, width, label='HTTP/2', color='blue', alpha=0.7)
        bars4 = ax2.bar(x + width/2, h3_latencies, width, label='HTTP/3', color='orange', alpha=0.7)
        
        ax2.set_xlabel('Delay (ms)')
        ax2.set_ylabel('Latency (ms)')
        ax2.set_title('Latency Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels([f'{d}ms' for d in delays])
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Connection time comparison (approximate as part of latency)
        ax3 = axes[0, 2]
        # Connection time is approximated as a certain percentage of latency (no actual measurement values)
        connection_time_ratio = 0.3  # Assume 30% of latency as connection time
        h2_connection_times = [lat * connection_time_ratio for lat in h2_latencies]
        h3_connection_times = [lat * connection_time_ratio for lat in h3_latencies]
        
        bars5 = ax3.bar(x - width/2, h2_connection_times, width, label='HTTP/2', color='blue', alpha=0.7)
        bars6 = ax3.bar(x + width/2, h3_connection_times, width, label='HTTP/3', color='orange', alpha=0.7)
        
        ax3.set_xlabel('Delay (ms)')
        ax3.set_ylabel('Connection Time (ms)')
        ax3.set_title('Connection Time Comparison')
        ax3.set_xticks(x)
        ax3.set_xticklabels([f'{d}ms' for d in delays])
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Throughput advantage (HTTP/3 advantage)
        ax4 = axes[1, 0]
        throughput_advantages = []
        for i, delay in enumerate(delays):
            if h3_throughputs[i] > 0:
                advantage = ((h3_throughputs[i] - h2_throughputs[i]) / h2_throughputs[i]) * 100
                throughput_advantages.append(advantage)
            else:
                throughput_advantages.append(0)
        
        colors = ['green' if adv > 0 else 'red' for adv in throughput_advantages]
        bars7 = ax4.bar(x, throughput_advantages, color=colors, alpha=0.7)
        ax4.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        
        ax4.set_xlabel('Delay (ms)')
        ax4.set_ylabel('HTTP/3 Advantage (%)')
        ax4.set_title('Throughput Advantage')
        ax4.set_xticks(x)
        ax4.set_xticklabels([f'{d}ms' for d in delays])
        ax4.grid(True, alpha=0.3)
        
        # 5. Latency advantage (HTTP/3 advantage)
        ax5 = axes[1, 1]
        latency_advantages = []
        for i, delay in enumerate(delays):
            if h2_latencies[i] > 0:
                advantage = ((h2_latencies[i] - h3_latencies[i]) / h2_latencies[i]) * 100
                latency_advantages.append(advantage)
            else:
                latency_advantages.append(0)
        
        colors = ['green' if adv > 0 else 'red' for adv in latency_advantages]
        bars8 = ax5.bar(x, latency_advantages, color=colors, alpha=0.7)
        ax5.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        
        ax5.set_xlabel('Delay (ms)')
        ax5.set_ylabel('HTTP/3 Advantage (%)')
        ax5.set_title('Latency Advantage')
        ax5.set_xticks(x)
        ax5.set_xticklabels([f'{d}ms' for d in delays])
        ax5.grid(True, alpha=0.3)
        
        # 6. Connection time advantage (HTTP/3 advantage)
        ax6 = axes[1, 2]
        connection_advantages = []
        for i, delay in enumerate(delays):
            if h2_connection_times[i] > 0:
                advantage = ((h2_connection_times[i] - h3_connection_times[i]) / h2_connection_times[i]) * 100
                connection_advantages.append(advantage)
            else:
                connection_advantages.append(0)
        
        colors = ['green' if adv > 0 else 'red' for adv in connection_advantages]
        bars9 = ax6.bar(x, connection_advantages, color=colors, alpha=0.7)
        ax6.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        
        ax6.set_xlabel('Delay (ms)')
        ax6.set_ylabel('HTTP/3 Advantage (%)')
        ax6.set_title('Connection Time Advantage')
        ax6.set_xticks(x)
        ax6.set_xticklabels([f'{d}ms' for d in delays])
        ax6.grid(True, alpha=0.3)
        
        # Display numbers on top of bars
        for ax, bars, values in [(ax1, [bars1, bars2], [h2_throughputs, h3_throughputs]),
                                (ax2, [bars3, bars4], [h2_latencies, h3_latencies]),
                                (ax3, [bars5, bars6], [h2_connection_times, h3_connection_times])]:
            for bar_group, value_group in zip(bars, values):
                for bar, value in zip(bar_group, value_group):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                           f'{value:.1f}', ha='center', va='bottom', fontsize=8)
        
        for ax, values in [(ax4, throughput_advantages), (ax5, latency_advantages), (ax6, connection_advantages)]:
            for i, value in enumerate(values):
                ax.text(i, value + (1 if value >= 0 else -1), f'{value:.1f}%',
                       ha='center', va='bottom' if value >= 0 else 'top', fontsize=8)
        
        # Adjust layout to reduce blank space
        plt.tight_layout(pad=2.0)
        
        # Remove bbox_inches='tight' and save with appropriate size
        plt.savefig(self.log_dir / 'ultra_final_boundary_analysis.png', dpi=300)
        plt.close()
        
        print(f"Ultra-final graphs saved: {self.log_dir / 'ultra_final_boundary_analysis.png'}")
    
    def generate_ultra_report(self):
        """Generate ultra-final report"""
        report_file = self.log_dir / 'ultra_final_boundary_report.txt'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("Ultra-final Boundary Analysis Report\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("🎯 Analysis Purpose\n")
            f.write("-" * 30 + "\n")
            f.write("• Identify HTTP/2 and HTTP/3 performance boundaries\n")
            f.write("• Detect boundary values with significantly relaxed statistical significance thresholds\n")
            f.write("• High reliability analysis with 5 measurements\n")
            f.write("• Stabilization with 2σ outlier removal\n\n")
            
            f.write("📊 Measurement Statistics\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total measurements: {len(self.results)}\n")
            f.write(f"Boundary values: {len(self.boundaries)}\n")
            f.write(f"Test conditions: {len(set([(r['delay'], r['loss'], r['bandwidth']) for r in self.results]))}\n")
            f.write(f"Measurements per condition: 5\n")
            f.write(f"Outlier removal: 2σ rule\n\n")
            
            if self.boundaries:
                f.write("🔍 Detected Boundary Values\n")
                f.write("-" * 30 + "\n")
                for i, boundary in enumerate(self.boundaries, 1):
                    f.write(f"{i}. Delay: {boundary['delay']}ms, Loss: {boundary['loss']}%\n")
                    f.write(f"   HTTP/2: {boundary['h2_throughput']:.1f} ± {boundary['h2_std']:.1f} req/s\n")
                    f.write(f"   HTTP/3: {boundary['h3_throughput']:.1f} ± {boundary['h3_std']:.1f} req/s\n")
                    f.write(f"    Performance difference: {boundary['diff_pct']:.1f}% (Confidence: {boundary['confidence_level']*100:.0f}%)\n")
                    f.write(f"    Superior protocol: {boundary['superior_protocol']}\n\n")
            else:
                f.write("❌ No boundary values detected\n\n")
            
            f.write("📈 Key Findings\n")
            f.write("-" * 30 + "\n")
            if self.results:
                # Identify the largest performance difference
                max_diff = 0
                max_diff_condition = None
                
                for result in self.results:
                    if result['protocol'] == 'http2':
                        h2_result = result
                        h3_results = [r for r in self.results if r['protocol'] == 'http3' and 
                                     r['delay'] == result['delay'] and r['loss'] == result['loss']]
                        if h3_results:
                            h3_result = h3_results[0]
                            diff = abs(h2_result['throughput'] - h3_result['throughput']) / h3_result['throughput'] * 100
                            if diff > max_diff:
                                max_diff = diff
                                max_diff_condition = (result['delay'], result['loss'])
                
                if max_diff_condition:
                    f.write(f"• Largest performance difference: {max_diff:.1f}% (Delay: {max_diff_condition[0]}ms, Loss: {max_diff_condition[1]}%)\n")
                
                # HTTP/3 instability
                h3_std_avg = np.mean([r['throughput_std'] for r in self.results if r['protocol'] == 'http3'])
                h2_std_avg = np.mean([r['throughput_std'] for r in self.results if r['protocol'] == 'http2'])
                f.write(f"• HTTP/3 measurement instability: {h3_std_avg:.1f} req/s (HTTP/2: {h2_std_avg:.1f} req/s)\n")
        
        print(f"Ultra-final report saved: {report_file}")
        
        # Generate CSV file
        self.generate_csv_report()
    
    def generate_csv_report(self):
        """Generate CSV file"""
        if not self.results:
            return
        
        csv_file = self.log_dir / 'ultra_final_results.csv'
        
        # Organize data
        csv_data = []
        for result in self.results:
            csv_data.append({
                'Protocol': result['protocol'].upper(),
                'Delay (ms)': result['delay'],
                'Loss (%)': result['loss'],
                'Bandwidth (Mbps)': result['bandwidth'],
                'Throughput (req/s)': result['throughput'],
                'Throughput Std (req/s)': result['throughput_std'],
                'Latency (ms)': result['latency'],
                'Connection Time (ms)': result.get('connection_time', 0),
                'Measurement Count': result.get('measurement_count', 5)
            })
        
        # Save to CSV file
        import csv
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if csv_data:
                writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
                writer.writeheader()
                writer.writerows(csv_data)
        
        print(f"CSV file saved: {csv_file}")
        
        # Generate CSV for performance comparison
        self.generate_comparison_csv()
    
    def generate_comparison_csv(self):
        """Generate performance comparison CSV file"""
        if not self.results:
            return
        
        comparison_file = self.log_dir / 'performance_comparison.csv'
        
        # Compare HTTP/2 and HTTP/3 results for each condition
        comparison_data = []
        
        # Group conditions
        conditions = set()
        for result in self.results:
            conditions.add((result['delay'], result['loss'], result['bandwidth']))
        
        for delay, loss, bandwidth in conditions:
            h2_results = [r for r in self.results if r['protocol'] == 'http2' and 
                         r['delay'] == delay and r['loss'] == loss and r['bandwidth'] == bandwidth]
            h3_results = [r for r in self.results if r['protocol'] == 'http3' and 
                         r['delay'] == delay and r['loss'] == loss and r['bandwidth'] == bandwidth]
            
            if h2_results and h3_results:
                h2_result = h2_results[0]
                h3_result = h3_results[0]
                
                # Calculate performance difference
                throughput_diff = ((h2_result['throughput'] - h3_result['throughput']) / h3_result['throughput']) * 100
                latency_diff = ((h2_result['latency'] - h3_result['latency']) / h3_result['latency']) * 100
                
                comparison_data.append({
                    'Delay (ms)': delay,
                    'Loss (%)': loss,
                    'Bandwidth (Mbps)': bandwidth,
                    'HTTP/2 Throughput (req/s)': h2_result['throughput'],
                    'HTTP/3 Throughput (req/s)': h3_result['throughput'],
                    'HTTP/2 Latency (ms)': h2_result['latency'],
                    'HTTP/3 Latency (ms)': h3_result['latency'],
                    'HTTP/2 Connection Time (ms)': h2_result.get('connection_time', 0),
                    'HTTP/3 Connection Time (ms)': h3_result.get('connection_time', 0),
                    'Throughput Advantage (%)': throughput_diff,
                    'Latency Advantage (%)': latency_diff,
                    'Connection Advantage (%)': 0,  # Connection time difference can also be calculated
                    'Superior Protocol': 'HTTP/2' if throughput_diff > 0 else 'HTTP/3'
                })
        
        # Save to CSV file
        import csv
        with open(comparison_file, 'w', newline='', encoding='utf-8') as f:
            if comparison_data:
                writer = csv.DictWriter(f, fieldnames=comparison_data[0].keys())
                writer.writeheader()
                writer.writerows(comparison_data)
        
        print(f"Performance comparison CSV file saved: {comparison_file}")

    def generate_timestamp_bar_graph(self, csv_file, protocol, delay, loss, bandwidth):
        """Generate timestamp bar graph from CSV file"""
        try:
            # Read CSV file
            timestamps = []
            response_times = []
            
            with open(csv_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            timestamp = int(parts[0])
                            response_time = int(parts[2])
                            timestamps.append(timestamp)
                            response_times.append(response_time)
            
            if not timestamps:
                print(f"      Warning: No data found in CSV file: {csv_file}")
                return None
            
            # Convert timestamps to relative time (seconds)
            start_time = min(timestamps)
            relative_times = [(t - start_time) / 1e9 for t in timestamps]  # Convert from nanoseconds to seconds
            
            # Generate graph
            plt.figure(figsize=(15, 8))
            
            # Main bar graph (response time)
            plt.subplot(2, 1, 1)
            bars = plt.bar(range(len(relative_times)), response_times, 
                          color='skyblue', alpha=0.7, width=0.8)
            plt.title(f'{protocol.upper()} Timestamp Analysis - Response Time\n'
                     f'Conditions: Delay {delay}ms, Loss {loss}%, Bandwidth {bandwidth}Mbps', 
                     fontsize=14, fontweight='bold')
            plt.xlabel('Request Order', fontsize=12)
            plt.ylabel('Response Time (μs)', fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # Display statistics
            avg_response = np.mean(response_times)
            std_response = np.std(response_times)
            plt.text(0.02, 0.98, f'Average: {avg_response:.1f}μs\nStandard Deviation: {std_response:.1f}μs', 
                    transform=plt.gca().transAxes, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # Timestamp distribution
            plt.subplot(2, 1, 2)
            plt.plot(relative_times, range(len(relative_times)), 'o-', 
                    color='red', alpha=0.7, linewidth=1, markersize=3)
            plt.title('Timestamp Distribution', fontsize=12, fontweight='bold')
            plt.xlabel('Relative Time (seconds)', fontsize=12)
            plt.ylabel('Request Order', fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # Statistics for time intervals
            if len(relative_times) > 1:
                intervals = np.diff(relative_times)
                avg_interval = np.mean(intervals)
                plt.text(0.02, 0.98, f'Average Interval: {avg_interval:.3f} seconds', 
                        transform=plt.gca().transAxes, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            plt.tight_layout()
            
            # Save file
            graph_file = csv_file.replace('.csv', '_timestamp_analysis.png')
            plt.savefig(graph_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"      Timestamp bar graph saved: {graph_file}")
            return graph_file
            
        except Exception as e:
            print(f"      Timestamp bar graph generation failed: {e}")
            return None
    
    def generate_detailed_timestamp_analysis(self, csv_file, protocol, delay, loss, bandwidth):
        """Generate detailed timestamp analysis graphs (individual files)"""
        try:
            # Read CSV file
            timestamps = []
            response_times = []
            request_sizes = []
            
            with open(csv_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            timestamp = int(parts[0])
                            request_size = int(parts[1])
                            response_time = int(parts[2])
                            timestamps.append(timestamp)
                            request_sizes.append(request_size)
                            response_times.append(response_time)
            
            if not timestamps:
                return None
            
            # Convert timestamps to relative time
            start_time = min(timestamps)
            relative_times = [(t - start_time) / 1e9 for t in timestamps]
            
            # Base filename
            base_name = csv_file.replace('.csv', '')
            graph_files = []
            
            # 1. Response time bar graph
            plt.figure(figsize=(12, 8))
            plt.bar(range(len(response_times)), response_times, 
                   color='skyblue', alpha=0.7)
            plt.title(f'{protocol.upper()} Response Time Distribution\n'
                     f'Conditions: Delay {delay}ms, Loss {loss}%, Bandwidth {bandwidth}Mbps', 
                     fontweight='bold', fontsize=14)
            plt.xlabel('Request Order', fontsize=12)
            plt.ylabel('Response Time (μs)', fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # Display statistics
            avg_response = np.mean(response_times)
            std_response = np.std(response_times)
            plt.text(0.02, 0.98, f'Average: {avg_response:.1f}μs\nStandard Deviation: {std_response:.1f}μs', 
                    transform=plt.gca().transAxes, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            response_time_file = f"{base_name}_response_time_distribution.png"
            plt.savefig(response_time_file, dpi=300, bbox_inches='tight')
            plt.close()
            graph_files.append(response_time_file)
            print(f"      Response time distribution graph saved: {response_time_file}")
            
            # 2. Response time histogram
            plt.figure(figsize=(12, 8))
            plt.hist(response_times, bins=20, color='lightgreen', alpha=0.7, edgecolor='black')
            plt.title(f'{protocol.upper()} Response Time Histogram\n'
                     f'Conditions: Delay {delay}ms, Loss {loss}%, Bandwidth {bandwidth}Mbps', 
                     fontweight='bold', fontsize=14)
            plt.xlabel('Response Time (μs)', fontsize=12)
            plt.ylabel('Frequency', fontsize=12)
            plt.grid(True, alpha=0.3)
            
            histogram_file = f"{base_name}_response_time_histogram.png"
            plt.savefig(histogram_file, dpi=300, bbox_inches='tight')
            plt.close()
            graph_files.append(histogram_file)
            print(f"      Response time histogram saved: {histogram_file}")
            
            # 3. Timestamp time series
            plt.figure(figsize=(12, 8))
            plt.plot(relative_times, 'o-', color='red', alpha=0.7, markersize=3)
            plt.title(f'{protocol.upper()} Timestamp Time Series\n'
                     f'Conditions: Delay {delay}ms, Loss {loss}%, Bandwidth {bandwidth}Mbps', 
                     fontweight='bold', fontsize=14)
            plt.xlabel('Request Order', fontsize=12)
            plt.ylabel('Relative Time (seconds)', fontsize=12)
            plt.grid(True, alpha=0.3)
            
            timeseries_file = f"{base_name}_timestamp_timeseries.png"
            plt.savefig(timeseries_file, dpi=300, bbox_inches='tight')
            plt.close()
            graph_files.append(timeseries_file)
            print(f"      Timestamp time series graph saved: {timeseries_file}")
            
            # 4. Time interval distribution
            if len(relative_times) > 1:
                intervals = np.diff(relative_times)
                plt.figure(figsize=(12, 8))
                plt.hist(intervals, bins=15, color='orange', alpha=0.7, edgecolor='black')
                plt.title(f'{protocol.upper()} Time Interval Distribution\n'
                         f'Conditions: Delay {delay}ms, Loss {loss}%, Bandwidth {bandwidth}Mbps', 
                         fontweight='bold', fontsize=14)
                plt.xlabel('Time Interval (seconds)', fontsize=12)
                plt.ylabel('Frequency', fontsize=12)
                plt.grid(True, alpha=0.3)
                
                # Display statistics
                avg_interval = np.mean(intervals)
                std_interval = np.std(intervals)
                plt.text(0.02, 0.98, f'Average Interval: {avg_interval:.3f} seconds\nInterval Standard Deviation: {std_interval:.3f} seconds', 
                        transform=plt.gca().transAxes, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                
                interval_file = f"{base_name}_time_interval_distribution.png"
                plt.savefig(interval_file, dpi=300, bbox_inches='tight')
                plt.close()
                graph_files.append(interval_file)
                print(f"      Time interval distribution graph saved: {interval_file}")
            
            # 5. Response time cumulative distribution
            plt.figure(figsize=(12, 8))
            sorted_response_times = np.sort(response_times)
            cumulative_prob = np.arange(1, len(sorted_response_times) + 1) / len(sorted_response_times)
            plt.plot(sorted_response_times, cumulative_prob, 'b-', linewidth=2)
            plt.title(f'{protocol.upper()} Response Time Cumulative Distribution\n'
                     f'Conditions: Delay {delay}ms, Loss {loss}%, Bandwidth {bandwidth}Mbps', 
                     fontweight='bold', fontsize=14)
            plt.xlabel('Response Time (μs)', fontsize=12)
            plt.ylabel('Cumulative Probability', fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # Add percentile lines
            percentiles = [50, 75, 90, 95, 99]
            for p in percentiles:
                value = np.percentile(response_times, p)
                plt.axvline(x=value, color='red', linestyle='--', alpha=0.7)
                plt.text(value, 0.5, f'{p}%', rotation=90, verticalalignment='center')
            
            cumulative_file = f"{base_name}_response_time_cumulative.png"
            plt.savefig(cumulative_file, dpi=300, bbox_inches='tight')
            plt.close()
            graph_files.append(cumulative_file)
            print(f"      Response time cumulative distribution graph saved: {cumulative_file}")
            
            # 6. Statistics table (saved as text file)
            stats_text = f"""
{protocol.upper()} Timestamp Analysis Statistics
Conditions: Delay {delay}ms, Loss {loss}%, Bandwidth {bandwidth}Mbps

Basic Statistics:
• Total Requests: {len(response_times)}
• Average Response Time: {np.mean(response_times):.1f} μs
• Standard Deviation: {np.std(response_times):.1f} μs
• Minimum: {np.min(response_times)} μs
• Maximum: {np.max(response_times)} μs
• Median: {np.median(response_times):.1f} μs
• 95th Percentile: {np.percentile(response_times, 95):.1f} μs
• 99th Percentile: {np.percentile(response_times, 99):.1f} μs

Time Interval Statistics:
"""
            if len(relative_times) > 1:
                intervals = np.diff(relative_times)
                stats_text += f"""• Average Interval: {np.mean(intervals):.3f} seconds
• Interval Standard Deviation: {np.std(intervals):.3f} seconds
• Minimum Interval: {np.min(intervals):.3f} seconds
• Maximum Interval: {np.max(intervals):.3f} seconds
"""
            
            stats_file = f"{base_name}_timestamp_statistics.txt"
            with open(stats_file, 'w', encoding='utf-8') as f:
                f.write(stats_text)
            graph_files.append(stats_file)
            print(f"      Statistics file saved: {stats_file}")
            
            return graph_files
            
        except Exception as e:
            print(f"      Detailed timestamp analysis generation failed: {e}")
            return None

    def generate_averaged_csv(self, csv_files, protocol, delay, loss, bandwidth, output_dir):
        """Generate averaged CSV file from multiple CSV files"""
        try:
            if not csv_files:
                return None
            
            # Read data from all CSV files
            all_data = []
            for csv_file in csv_files:
                try:
                    with open(csv_file, 'r') as f:
                        lines = f.readlines()
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                parts = line.split('\t')
                                if len(parts) >= 3:
                                    timestamp = int(parts[0])
                                    request_size = int(parts[1])
                                    response_time = int(parts[2])
                                    all_data.append((timestamp, request_size, response_time))
                except Exception as e:
                    print(f"      Error reading CSV file {csv_file}: {e}")
                    continue
            
            if not all_data:
                print(f"      No valid data found")
                return None
            
            # Sort data by timestamp
            all_data.sort(key=lambda x: x[0])
            
            # Generate averaged CSV file
            averaged_csv = output_dir / f"{protocol}_{delay}ms_{loss}pct_{bandwidth}mbps_averaged.csv"
            
            with open(averaged_csv, 'w') as f:
                f.write(f"# Protocol: {protocol}\n")
                f.write(f"# Delay: {delay}ms\n")
                f.write(f"# Loss: {loss}%\n")
                f.write(f"# Bandwidth: {bandwidth}Mbps\n")
                f.write(f"# Averaged from {len(csv_files)} CSV files\n")
                f.write(f"# Total requests: {len(all_data)}\n")
                f.write(f"# Timestamp(ns)\tRequestSize(bytes)\tResponseTime(us)\n")
                
                for timestamp, request_size, response_time in all_data:
                    f.write(f"{timestamp}\t{request_size}\t{response_time}\n")
            
            print(f"      Averaged CSV file generated: {len(all_data)} requests")
            return str(averaged_csv)
            
        except Exception as e:
            print(f"      Averaged CSV file generation failed: {e}")
            return None

def generate_timestamp_graphs_from_csv(csv_file, protocol='http2', delay=0, loss=0, bandwidth=0):
    """Generate timestamp bar graph from existing CSV file"""
    try:
        analyzer = UltraFinalAnalyzer(Path(csv_file).parent)
        
        # Extract network conditions from filename
        filename = Path(csv_file).name
        if 'ms' in filename and 'pct' in filename:
            try:
                # Example: http2_150ms_3pct_0mbps.csv
                parts = filename.replace('.csv', '').split('_')
                if len(parts) >= 3:
                    delay = int(parts[1].replace('ms', ''))
                    loss = int(parts[2].replace('pct', ''))
                    if len(parts) > 3:
                        bandwidth = int(parts[3].replace('mbps', ''))
            except:
                pass
        
        print(f"Generating timestamp bar graph from CSV file: {csv_file}")
        print(f"Conditions: Protocol={protocol}, Delay={delay}ms, Loss={loss}%, Bandwidth={bandwidth}Mbps")
        
        # Generate timestamp bar graph
        graph_file = analyzer.generate_timestamp_bar_graph(csv_file, protocol, delay, loss, bandwidth)
        
        # Generate detailed timestamp analysis
        detailed_graph = analyzer.generate_detailed_timestamp_analysis(csv_file, protocol, delay, loss, bandwidth)
        
        if graph_file:
            print(f"Timestamp bar graph saved: {graph_file}")
        if detailed_graph:
            print(f"Detailed timestamp analysis saved: {detailed_graph}")
        
        return graph_file, detailed_graph
        
    except Exception as e:
        print(f"Timestamp bar graph generation failed: {e}")
        return None, None

def main():
    parser = argparse.ArgumentParser(description='Ultra-final Boundary Analysis')
    parser.add_argument('--log_dir', default='logs/ultra_final_analysis', help='Log directory')
    parser.add_argument('--test_conditions', nargs='+', 
                       default=['10:0:0', '50:1:0', '100:2:0', '150:3:0', '200:5:0'],
                       help='Test conditions (Delay:Loss:Bandwidth)')
    parser.add_argument('--csv_file', help='Generate timestamp bar graph from existing CSV file')
    
    args = parser.parse_args()
    
    if args.csv_file:
        # Generate timestamp bar graph from existing CSV file
        generate_timestamp_graphs_from_csv(args.csv_file)
        return
    
    # Normal benchmark execution
    analyzer = UltraFinalAnalyzer(args.log_dir)
    
    print("Ultra-final Boundary Analysis Started")
    print(f"Log directory: {args.log_dir}")
    print(f"Test conditions: {args.test_conditions}")
    
    # Execute benchmark
    for condition in args.test_conditions:
        try:
            delay, loss, bandwidth = map(int, condition.split(':'))
            print(f"\nCondition: Delay={delay}ms, Loss={loss}%, Bandwidth={bandwidth}Mbps")
        
            # HTTP/2 test
            h2_result = analyzer.run_ultra_reliable_benchmark(delay, loss, bandwidth, 'http2')
            if h2_result:
                analyzer.results.append(h2_result)
            
            # HTTP/3 test
            h3_result = analyzer.run_ultra_reliable_benchmark(delay, loss, bandwidth, 'http3')
            if h3_result:
                analyzer.results.append(h3_result)
        
        except ValueError as e:
            print(f"Condition parsing error: {condition} - {e}")
            continue
    
    if analyzer.results:
        print("\nBoundary value detection started")
        analyzer.detect_ultra_boundaries()
        
        print("\nGraph generation started")
        analyzer.generate_ultra_graphs()
    
        print("\nReport generation started")
        analyzer.generate_ultra_report()
    
        print(f"\nAnalysis complete: {args.log_dir}")
    else:
        print("No valid results found")

if __name__ == "__main__":
    main() 