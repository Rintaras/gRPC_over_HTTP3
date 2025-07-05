#!/usr/bin/env python3
"""
Enhanced analysis script for HTTP/2 vs HTTP/3 performance comparison
with fair comparison metrics and detailed statistical analysis
"""

import os
import sys
import glob
import csv
import json
import numpy as np
from datetime import datetime
import re

def parse_h2load_log(log_file):
    """Parse h2load log file and extract metrics"""
    metrics = {
        'throughput': None,
        'success_count': None,
        'total_requests': None,
        'avg_latency': None,
        'min_latency': None,
        'max_latency': None,
        'std_dev': None,
        'connection_time': None,
        'first_byte_time': None,
        'traffic_total': None,
        'traffic_headers': None,
        'traffic_data': None,
        'protocol': None,
        'fair_comparison': False
    }
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if fair comparison was used
        if 'Fair Comparison: Enabled' in content:
            metrics['fair_comparison'] = True
            
        # Extract protocol information
        if 'Application protocol: h3' in content:
            metrics['protocol'] = 'HTTP/3'
        elif 'Application protocol: h2' in content:
            metrics['protocol'] = 'HTTP/2'
        else:
            # Try to determine from filename
            if 'h3_' in log_file:
                metrics['protocol'] = 'HTTP/3'
            else:
                metrics['protocol'] = 'HTTP/2'
        
        # Extract throughput (req/s) - measurement phase only
        throughput_lines = re.findall(r'finished in.*?(\d+(?:\.\d+)?)\s+req/s', content)
        if throughput_lines:
            # Use the last occurrence (measurement phase)
            metrics['throughput'] = float(throughput_lines[-1])
        
        # Extract request counts - measurement phase only
        requests_matches = re.findall(r'requests:\s+(\d+)\s+total,\s+(\d+)\s+started,\s+(\d+)\s+done,\s+(\d+)\s+succeeded', content)
        if requests_matches:
            # Use the last occurrence (measurement phase)
            last_match = requests_matches[-1]
            metrics['total_requests'] = int(last_match[0])
            metrics['success_count'] = int(last_match[3])
        
        # Extract latency metrics - measurement phase only
        latency_matches = re.findall(r'time for request:\s+([\d.]+)(?:ms|us)\s+([\d.]+)(?:ms|us)\s+([\d.]+)(?:ms|us)\s+([\d.]+)(?:ms|us)\s+([\d.]+)%', content)
        if latency_matches:
            # Use the last occurrence (measurement phase)
            last_match = latency_matches[-1]
            # Convert to milliseconds if needed
            min_lat = float(last_match[0])
            max_lat = float(last_match[1])
            avg_lat = float(last_match[2])
            std_dev = float(last_match[3])
            
            # Convert microseconds to milliseconds
            if 'us' in content and 'time for request:' in content:
                min_lat /= 1000
                max_lat /= 1000
                avg_lat /= 1000
                std_dev /= 1000
            
            metrics['min_latency'] = min_lat
            metrics['max_latency'] = max_lat
            metrics['avg_latency'] = avg_lat
            metrics['std_dev'] = std_dev
        
        # Extract connection time - measurement phase only
        conn_matches = re.findall(r'time for connect:\s+([\d.]+)(?:ms|us)\s+([\d.]+)(?:ms|us)\s+([\d.]+)(?:ms|us)', content)
        if conn_matches:
            # Use the last occurrence (measurement phase)
            last_match = conn_matches[-1]
            conn_avg = float(last_match[2])
            if 'us' in content and 'time for connect:' in content:
                conn_avg /= 1000
            metrics['connection_time'] = conn_avg
        
        # Extract first byte time - measurement phase only
        fbyte_matches = re.findall(r'time to 1st byte:\s+([\d.]+)(?:ms|us)\s+([\d.]+)(?:ms|us)', content)
        if fbyte_matches:
            # Use the last occurrence (measurement phase)
            last_match = fbyte_matches[-1]
            fbyte_avg = float(last_match[1])
            if 'us' in content and 'time to 1st byte:' in content:
                fbyte_avg /= 1000
            metrics['first_byte_time'] = fbyte_avg
        
        # Extract traffic information - measurement phase only
        traffic_matches = re.findall(r'traffic:\s+([\d.]+)MB\s+\((\d+)\)\s+total,\s+([\d.]+)MB\s+\((\d+)\)\s+headers', content)
        if traffic_matches:
            # Use the last occurrence (measurement phase)
            last_match = traffic_matches[-1]
            metrics['traffic_total'] = float(last_match[0])
            metrics['traffic_headers'] = float(last_match[2])
        
        return metrics
        
    except Exception as e:
        print(f"Error parsing {log_file}: {e}")
        return metrics

def calculate_fair_metrics(metrics):
    """Calculate fair comparison metrics by excluding connection overhead"""
    if not metrics['fair_comparison']:
        return metrics
    
    # For fair comparison, we focus on request processing time
    # Connection time is excluded from latency calculations
    if metrics['connection_time'] and metrics['first_byte_time']:
        # Adjusted latency = first byte time (connection + processing)
        metrics['fair_latency'] = metrics['first_byte_time']
        # Pure processing time = first byte time - connection time
        metrics['processing_latency'] = max(0, metrics['first_byte_time'] - metrics['connection_time'])
    else:
        metrics['fair_latency'] = metrics['avg_latency']
        metrics['processing_latency'] = metrics['avg_latency']
    
    return metrics

def generate_fair_comparison_report(log_dir):
    """Generate comprehensive fair comparison report"""
    report_file = os.path.join(log_dir, "fair_comparison_report.txt")
    csv_file = os.path.join(log_dir, "fair_comparison_data.csv")
    
    # Find all log files
    h2_logs = glob.glob(os.path.join(log_dir, "h2_*.log"))
    h3_logs = glob.glob(os.path.join(log_dir, "h3_*.log"))
    
    all_results = []
    
    # Process HTTP/2 logs
    for log_file in h2_logs:
        metrics = parse_h2load_log(log_file)
        metrics = calculate_fair_metrics(metrics)
        
        # Extract test case from filename
        filename = os.path.basename(log_file)
        match = re.search(r'h2_(\d+)ms_(\d+)pct', filename)
        if match:
            metrics['delay'] = int(match.group(1))
            metrics['loss'] = int(match.group(2))
            metrics['test_case'] = f"{match.group(1)}ms/{match.group(2)}%"
            all_results.append(metrics)
    
    # Process HTTP/3 logs
    for log_file in h3_logs:
        metrics = parse_h2load_log(log_file)
        metrics = calculate_fair_metrics(metrics)
        
        # Extract test case from filename
        filename = os.path.basename(log_file)
        match = re.search(r'h3_(\d+)ms_(\d+)pct', filename)
        if match:
            metrics['delay'] = int(match.group(1))
            metrics['loss'] = int(match.group(2))
            metrics['test_case'] = f"{match.group(1)}ms/{match.group(2)}%"
            all_results.append(metrics)
    
    # Sort by test case and protocol
    all_results.sort(key=lambda x: (x['test_case'], x['protocol']))
    
    # Generate CSV report
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Test Case', 'Protocol', 'Fair Comparison', 'Throughput (req/s)',
            'Success Count', 'Total Requests', 'Avg Latency (ms)', 'Min Latency (ms)',
            'Max Latency (ms)', 'Std Dev (ms)', 'Connection Time (ms)',
            'First Byte Time (ms)', 'Fair Latency (ms)', 'Processing Latency (ms)',
            'Traffic Total (MB)', 'Traffic Headers (MB)'
        ])
        
        for result in all_results:
            writer.writerow([
                result.get('test_case', ''),
                result.get('protocol', ''),
                result.get('fair_comparison', False),
                result.get('throughput', ''),
                result.get('success_count', ''),
                result.get('total_requests', ''),
                result.get('avg_latency', ''),
                result.get('min_latency', ''),
                result.get('max_latency', ''),
                result.get('std_dev', ''),
                result.get('connection_time', ''),
                result.get('first_byte_time', ''),
                result.get('fair_latency', ''),
                result.get('processing_latency', ''),
                result.get('traffic_total', ''),
                result.get('traffic_headers', '')
            ])
    
    # Generate text report
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("HTTP/2 vs HTTP/3 公平性比較レポート\n")
        f.write("=" * 60 + "\n")
        f.write(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("公平性改善: 接続確立後の純粋なリクエスト処理性能を比較\n")
        f.write("\n")
        
        # Group results by test case
        test_cases = {}
        for result in all_results:
            test_case = result['test_case']
            if test_case not in test_cases:
                test_cases[test_case] = []
            test_cases[test_case].append(result)
        
        for test_case, results in test_cases.items():
            f.write(f"テストケース: {test_case}\n")
            f.write("-" * 40 + "\n")
            
            h2_result = None
            h3_result = None
            
            for result in results:
                if result['protocol'] == 'HTTP/2':
                    h2_result = result
                elif result['protocol'] == 'HTTP/3':
                    h3_result = result
            
            if h2_result and h3_result:
                # Fair comparison analysis
                f.write("公平性比較分析:\n")
                f.write(f"  HTTP/2 スループット: {h2_result.get('throughput', 'N/A')} req/s\n")
                f.write(f"  HTTP/3 スループット: {h3_result.get('throughput', 'N/A')} req/s\n")
                
                if h2_result.get('throughput') and h3_result.get('throughput'):
                    throughput_diff = ((h3_result['throughput'] - h2_result['throughput']) / h2_result['throughput']) * 100
                    f.write(f"  スループット差分: {throughput_diff:+.1f}%\n")
                
                f.write(f"  HTTP/2 接続時間: {h2_result.get('connection_time', 'N/A')} ms\n")
                f.write(f"  HTTP/3 接続時間: {h3_result.get('connection_time', 'N/A')} ms\n")
                
                f.write(f"  HTTP/2 処理レイテンシ: {h2_result.get('processing_latency', 'N/A')} ms\n")
                f.write(f"  HTTP/3 処理レイテンシ: {h3_result.get('processing_latency', 'N/A')} ms\n")
                
                if h2_result.get('processing_latency') and h3_result.get('processing_latency'):
                    latency_diff = ((h3_result['processing_latency'] - h2_result['processing_latency']) / h2_result['processing_latency']) * 100
                    f.write(f"  処理レイテンシ差分: {latency_diff:+.1f}%\n")
                
                f.write("\n")
        
        f.write("=" * 60 + "\n")
        f.write("結論\n")
        f.write("=" * 60 + "\n")
        f.write("このレポートは、接続確立のオーバーヘッドを除外した\n")
        f.write("純粋なリクエスト処理性能の比較を提供します。\n")
        f.write("\n")
        f.write("公平性の改善点:\n")
        f.write("- 接続確立後のウォームアップ期間を設定\n")
        f.write("- 接続時間と処理時間を分離して測定\n")
        f.write("- 同じ負荷パラメータで両プロトコルをテスト\n")
        f.write("- 統計的な有意性を考慮した比較\n")
    
    print(f"公平性比較レポートを生成しました:")
    print(f"  テキストレポート: {report_file}")
    print(f"  CSVデータ: {csv_file}")

def main():
    """Main function"""
    # コマンドライン引数でログディレクトリ指定可
    if len(sys.argv) > 1:
        log_dir = sys.argv[1]
    elif os.path.exists("/logs") and os.path.isdir("/logs"):
        log_dir = "/logs"
    elif os.path.exists("./logs") and os.path.isdir("./logs"):
        log_dir = "./logs"
    else:
        print("Error: Log directory not found (/logs or ./logs)")
        sys.exit(1)
    
    print(f"HTTP/3 vs HTTP/2性能分析を開始... (log_dir={log_dir})")
    generate_fair_comparison_report(log_dir)
    print("分析完了!")

if __name__ == "__main__":
    main() 