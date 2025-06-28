#!/usr/bin/env python3
"""
Enhanced result analysis script for HTTP/2 vs HTTP/3 benchmark
Parses h2load and curl logs, extracts metrics, and generates CSV reports
"""

import os
import re
import csv
import json
from datetime import datetime
from pathlib import Path

def parse_h2load_log(log_file):
    """Parse h2load log and extract metrics"""
    metrics = {
        'protocol': 'HTTP/2',
        'file': os.path.basename(log_file),
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0,
        'timeout_requests': 0,
        'total_time': 0,
        'requests_per_sec': 0,
        'transfer_per_sec': 0,
        'min_latency': 0,
        'max_latency': 0,
        'mean_latency': 0,
        'latency_std': 0,
        'connect_time_mean': 0,
        'first_byte_time_mean': 0,
        'network_delay': 0,
        'network_loss': 0,
        'timestamp': '',
        'status_codes': {}
    }
    
    try:
        with open(log_file, 'r') as f:
            content = f.read()
            
        # Extract network conditions
        network_match = re.search(r'Delay: (\d+)ms', content)
        if network_match:
            metrics['network_delay'] = int(network_match.group(1))
            
        loss_match = re.search(r'Loss: (\d+)%', content)
        if loss_match:
            metrics['network_loss'] = int(loss_match.group(1))
            
        # Extract timestamp
        timestamp_match = re.search(r'Timestamp: (.+)', content)
        if timestamp_match:
            metrics['timestamp'] = timestamp_match.group(1)
            
        # Extract main metrics
        requests_match = re.search(r'requests: (\d+) total, (\d+) started, (\d+) done, (\d+) succeeded, (\d+) failed, (\d+) errored, (\d+) timeout', content)
        if requests_match:
            metrics['total_requests'] = int(requests_match.group(1))
            metrics['successful_requests'] = int(requests_match.group(4))
            metrics['failed_requests'] = int(requests_match.group(5))
            metrics['timeout_requests'] = int(requests_match.group(7))
            
        # Extract performance metrics
        req_per_sec_match = re.search(r'(\d+\.\d+) req/s', content)
        if req_per_sec_match:
            metrics['requests_per_sec'] = float(req_per_sec_match.group(1))
            
        transfer_match = re.search(r'(\d+\.\d+)MB/s', content)
        if transfer_match:
            metrics['transfer_per_sec'] = float(transfer_match.group(1))
            
        # Extract latency statistics
        latency_section = re.search(r'time for request:\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)', content)
        if latency_section:
            metrics['min_latency'] = float(latency_section.group(1))
            metrics['max_latency'] = float(latency_section.group(2))
            metrics['mean_latency'] = float(latency_section.group(3))
            metrics['latency_std'] = float(latency_section.group(4))
            
        # Extract connect time
        connect_match = re.search(r'time for connect:\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)', content)
        if connect_match:
            metrics['connect_time_mean'] = float(connect_match.group(3))
            
        # Extract first byte time
        first_byte_match = re.search(r'time to 1st byte:\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)', content)
        if first_byte_match:
            metrics['first_byte_time_mean'] = float(first_byte_match.group(3))
            
        # Extract status codes
        status_match = re.search(r'status codes: (\d+) 2xx, (\d+) 3xx, (\d+) 4xx, (\d+) 5xx', content)
        if status_match:
            metrics['status_codes'] = {
                '2xx': int(status_match.group(1)),
                '3xx': int(status_match.group(2)),
                '4xx': int(status_match.group(3)),
                '5xx': int(status_match.group(4))
            }
            
    except Exception as e:
        print(f"Error parsing {log_file}: {e}")
        
    return metrics

def parse_curl_log(log_file):
    """Parse curl HTTP/3 log and extract metrics (now handles both h2load and curl formats)"""
    metrics = {
        'protocol': 'HTTP/3',
        'file': os.path.basename(log_file),
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0,
        'timeout_requests': 0,
        'total_time': 0,
        'requests_per_sec': 0,
        'transfer_per_sec': 0,
        'min_latency': 0,
        'max_latency': 0,
        'mean_latency': 0,
        'latency_std': 0,
        'connect_time_mean': 0,
        'first_byte_time_mean': 0,
        'network_delay': 0,
        'network_loss': 0,
        'timestamp': '',
        'status_codes': {}
    }
    
    try:
        with open(log_file, 'r') as f:
            content = f.read()
            
        # Extract network conditions
        network_match = re.search(r'Delay: (\d+)ms', content)
        if network_match:
            metrics['network_delay'] = int(network_match.group(1))
            
        loss_match = re.search(r'Loss: (\d+)%', content)
        if loss_match:
            metrics['network_loss'] = int(loss_match.group(1))
            
        # Extract timestamp
        timestamp_match = re.search(r'Timestamp: (.+)', content)
        if timestamp_match:
            metrics['timestamp'] = timestamp_match.group(1)
            
        # Check if this is h2load format (new format)
        if 'finished in' in content and 'requests:' in content:
            # Parse h2load format
            requests_match = re.search(r'requests: (\d+) total, (\d+) started, (\d+) done, (\d+) succeeded, (\d+) failed, (\d+) errored, (\d+) timeout', content)
            if requests_match:
                metrics['total_requests'] = int(requests_match.group(1))
                metrics['successful_requests'] = int(requests_match.group(4))
                metrics['failed_requests'] = int(requests_match.group(5))
                metrics['timeout_requests'] = int(requests_match.group(7))
                
            # Extract performance metrics
            req_per_sec_match = re.search(r'(\d+\.\d+) req/s', content)
            if req_per_sec_match:
                metrics['requests_per_sec'] = float(req_per_sec_match.group(1))
                
            transfer_match = re.search(r'(\d+\.\d+)MB/s', content)
            if transfer_match:
                metrics['transfer_per_sec'] = float(transfer_match.group(1))
                
            # Extract latency statistics
            latency_section = re.search(r'time for request:\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)', content)
            if latency_section:
                metrics['min_latency'] = float(latency_section.group(1))
                metrics['max_latency'] = float(latency_section.group(2))
                metrics['mean_latency'] = float(latency_section.group(3))
                metrics['latency_std'] = float(latency_section.group(4))
                
            # Extract connect time
            connect_match = re.search(r'time for connect:\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)', content)
            if connect_match:
                metrics['connect_time_mean'] = float(connect_match.group(3))
                
            # Extract first byte time
            first_byte_match = re.search(r'time to 1st byte:\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)', content)
            if first_byte_match:
                metrics['first_byte_time_mean'] = float(first_byte_match.group(3))
                
            # Extract status codes
            status_match = re.search(r'status codes: (\d+) 2xx, (\d+) 3xx, (\d+) 4xx, (\d+) 5xx', content)
            if status_match:
                metrics['status_codes'] = {
                    '2xx': int(status_match.group(1)),
                    '3xx': int(status_match.group(2)),
                    '4xx': int(status_match.group(3)),
                    '5xx': int(status_match.group(4))
                }
                
        else:
            # Parse old curl format (individual request results)
            success_lines = re.findall(r'SUCCESS: (\d+), ([\d\.]+), ([\d\.]+), (\d+), (\d+), (\d+)', content)
            failed_lines = re.findall(r'FAILED: (\d+), ([\d\.]+), ([\d\.]+), (\d+), (\d+), (\d+)', content)
            
            metrics['total_requests'] = len(success_lines) + len(failed_lines)
            metrics['successful_requests'] = len(success_lines)
            metrics['failed_requests'] = len(failed_lines)
            
            # Calculate latency statistics from successful requests
            if success_lines:
                latencies = [float(line[2]) for line in success_lines]  # curl time_total
                metrics['min_latency'] = min(latencies)
                metrics['max_latency'] = max(latencies)
                metrics['mean_latency'] = sum(latencies) / len(latencies)
                
                # Calculate standard deviation
                mean = metrics['mean_latency']
                variance = sum((x - mean) ** 2 for x in latencies) / len(latencies)
                metrics['latency_std'] = variance ** 0.5
                
                # Calculate requests per second
                total_time = max(latencies)  # Approximate total time
                if total_time > 0:
                    metrics['requests_per_sec'] = len(success_lines) / total_time
                    
            # Count status codes
            status_counts = {}
            for line in success_lines:
                status_code = int(line[4])
                status_class = f"{status_code//100}xx"
                status_counts[status_class] = status_counts.get(status_class, 0) + 1
            metrics['status_codes'] = status_counts
        
    except Exception as e:
        print(f"Error parsing {log_file}: {e}")
        
    return metrics

def calculate_success_rate(metrics):
    """Calculate success rate percentage"""
    if metrics['total_requests'] > 0:
        return (metrics['successful_requests'] / metrics['total_requests']) * 100
    return 0

def generate_csv_report(log_dir, output_file):
    """Generate comprehensive CSV report from all log files"""
    all_metrics = []
    
    # Process all log files
    for log_file in Path(log_dir).glob('h*_*.log'):
        if 'h2_' in log_file.name:
            metrics = parse_h2load_log(str(log_file))
        elif 'h3_' in log_file.name:
            metrics = parse_curl_log(str(log_file))
        else:
            continue
            
        # Add success rate
        metrics['success_rate'] = calculate_success_rate(metrics)
        all_metrics.append(metrics)
    
    # Sort by network conditions and protocol
    all_metrics.sort(key=lambda x: (x['network_delay'], x['network_loss'], x['protocol']))
    
    # Write CSV report
    if all_metrics:
        fieldnames = [
            'protocol', 'file', 'timestamp', 'network_delay', 'network_loss',
            'total_requests', 'successful_requests', 'failed_requests', 'timeout_requests',
            'success_rate', 'total_time', 'requests_per_sec', 'transfer_per_sec',
            'min_latency', 'max_latency', 'mean_latency', 'latency_std',
            'connect_time_mean', 'first_byte_time_mean'
        ]
        
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for metrics in all_metrics:
                # Flatten status codes
                row = {k: v for k, v in metrics.items() if k not in ['status_codes']}
                writer.writerow(row)
                
        print(f"CSV report generated: {output_file}")
        print(f"Processed {len(all_metrics)} log files")
        
        # Print summary
        print("\n=== SUMMARY ===")
        for metrics in all_metrics:
            print(f"{metrics['protocol']} - {metrics['network_delay']}ms/{metrics['network_loss']}%: "
                  f"{metrics['success_rate']:.1f}% success, {metrics['requests_per_sec']:.1f} req/s")
    else:
        print("No log files found to process")

def generate_comparison_report(log_dir, output_file):
    """Generate side-by-side comparison report"""
    metrics_by_condition = {}
    
    # Group metrics by network condition
    for log_file in Path(log_dir).glob('h*_*.log'):
        if 'h2_' in log_file.name:
            metrics = parse_h2load_log(str(log_file))
        elif 'h3_' in log_file.name:
            metrics = parse_curl_log(str(log_file))
        else:
            continue
            
        metrics['success_rate'] = calculate_success_rate(metrics)
        condition = f"{metrics['network_delay']}ms_{metrics['network_loss']}pct"
        
        if condition not in metrics_by_condition:
            metrics_by_condition[condition] = {}
        metrics_by_condition[condition][metrics['protocol']] = metrics
    
    # Generate comparison CSV
    if metrics_by_condition:
        fieldnames = [
            'network_condition', 'protocol', 'success_rate', 'requests_per_sec',
            'mean_latency', 'latency_std', 'connect_time_mean', 'first_byte_time_mean'
        ]
        
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for condition, protocols in metrics_by_condition.items():
                for protocol, metrics in protocols.items():
                    row = {
                        'network_condition': condition,
                        'protocol': protocol,
                        'success_rate': metrics['success_rate'],
                        'requests_per_sec': metrics['requests_per_sec'],
                        'mean_latency': metrics['mean_latency'],
                        'latency_std': metrics['latency_std'],
                        'connect_time_mean': metrics['connect_time_mean'],
                        'first_byte_time_mean': metrics['first_byte_time_mean']
                    }
                    writer.writerow(row)
                    
        print(f"Comparison report generated: {output_file}")

def main():
    log_dir = "/logs"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Generate reports
    csv_report = f"/logs/benchmark_results_{timestamp}.csv"
    comparison_report = f"/logs/comparison_{timestamp}.csv"
    
    print("=== HTTP/2 vs HTTP/3 Benchmark Analysis ===")
    print(f"Log directory: {log_dir}")
    print(f"Timestamp: {timestamp}")
    
    generate_csv_report(log_dir, csv_report)
    generate_comparison_report(log_dir, comparison_report)
    
    print("\n=== Analysis Complete ===")
    print(f"Detailed results: {csv_report}")
    print(f"Comparison report: {comparison_report}")

if __name__ == "__main__":
    main() 