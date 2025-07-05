#!/usr/bin/env python3
"""
Extreme conditions analysis script
for HTTP/3 vs HTTP/2 performance comparison
"""

import os
import sys
import glob
import csv
import json
import numpy as np
from datetime import datetime
import re

def parse_extreme_conditions_log(log_file):
    """Parse extreme conditions test log file and extract metrics"""
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
        'protocol': None,
        'delay': None,
        'loss': None,
        'bandwidth': None,
        'description': None,
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
            if 'h3_extreme_' in log_file:
                metrics['protocol'] = 'HTTP/3'
            else:
                metrics['protocol'] = 'HTTP/2'
        
        # Extract network conditions from log
        delay_match = re.search(r'Delay: (\d+)ms', content)
        if delay_match:
            metrics['delay'] = int(delay_match.group(1))
            
        loss_match = re.search(r'Loss: (\d+)%', content)
        if loss_match:
            metrics['loss'] = int(loss_match.group(1))
            
        bandwidth_match = re.search(r'Bandwidth: (\d+)Mbps', content)
        if bandwidth_match:
            metrics['bandwidth'] = int(bandwidth_match.group(1))
            
        description_match = re.search(r'Description: (.+)', content)
        if description_match:
            metrics['description'] = description_match.group(1).strip()
        
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

def calculate_http3_advantage(h2_metrics, h3_metrics):
    """Calculate HTTP/3 advantage over HTTP/2"""
    if not h2_metrics or not h3_metrics:
        return None
    
    advantage = {}
    
    # Throughput advantage (higher is better)
    if h2_metrics.get('throughput') and h3_metrics.get('throughput'):
        h2_tp = h2_metrics['throughput']
        h3_tp = h3_metrics['throughput']
        advantage['throughput'] = ((h3_tp - h2_tp) / h2_tp) * 100
    
    # Latency advantage (lower is better)
    if h2_metrics.get('avg_latency') and h3_metrics.get('avg_latency'):
        h2_lat = h2_metrics['avg_latency']
        h3_lat = h3_metrics['avg_latency']
        advantage['latency'] = ((h2_lat - h3_lat) / h2_lat) * 100
    
    # Connection time advantage (lower is better)
    if h2_metrics.get('connection_time') and h3_metrics.get('connection_time'):
        h2_conn = h2_metrics['connection_time']
        h3_conn = h3_metrics['connection_time']
        advantage['connection_time'] = ((h2_conn - h3_conn) / h2_conn) * 100
    
    return advantage

def generate_extreme_conditions_report(log_dir):
    """Generate comprehensive extreme conditions analysis report"""
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    report_file = os.path.join(log_dir, "extreme_conditions_report.txt")
    csv_file = os.path.join(log_dir, "extreme_conditions_data.csv")
    
    # Find all extreme conditions test log files
    h2_logs = glob.glob(os.path.join(log_dir, "h2_extreme_*.log"))
    h3_logs = glob.glob(os.path.join(log_dir, "h3_extreme_*.log"))
    
    all_results = []
    comparison_results = []
    
    # Process HTTP/2 logs
    h2_results = {}
    for log_file in h2_logs:
        metrics = parse_extreme_conditions_log(log_file)
        
        # Create key for matching
        if metrics.get('delay') is not None and metrics.get('bandwidth') is not None:
            key = f"{metrics['delay']}_{metrics['bandwidth']}"
            h2_results[key] = metrics
            all_results.append(metrics)
    
    # Process HTTP/3 logs
    h3_results = {}
    for log_file in h3_logs:
        metrics = parse_extreme_conditions_log(log_file)
        
        # Create key for matching
        if metrics.get('delay') is not None and metrics.get('bandwidth') is not None:
            key = f"{metrics['delay']}_{metrics['bandwidth']}"
            h3_results[key] = metrics
            all_results.append(metrics)
    
    # Generate comparisons
    for key in h2_results:
        if key in h3_results:
            h2_metrics = h2_results[key]
            h3_metrics = h3_results[key]
            
            advantage = calculate_http3_advantage(h2_metrics, h3_metrics)
            
            comparison = {
                'test_case': h2_metrics.get('description', f"{h2_metrics.get('delay', 0)}ms/{h2_metrics.get('bandwidth', 0)}Mbps"),
                'delay': h2_metrics.get('delay'),
                'loss': h2_metrics.get('loss'),
                'bandwidth': h2_metrics.get('bandwidth'),
                'h2_throughput': h2_metrics.get('throughput'),
                'h3_throughput': h3_metrics.get('throughput'),
                'h2_latency': h2_metrics.get('avg_latency'),
                'h3_latency': h3_metrics.get('avg_latency'),
                'h2_connection_time': h2_metrics.get('connection_time'),
                'h3_connection_time': h3_metrics.get('connection_time'),
                'throughput_advantage': advantage.get('throughput') if advantage else None,
                'latency_advantage': advantage.get('latency') if advantage else None,
                'connection_advantage': advantage.get('connection_time') if advantage else None
            }
            comparison_results.append(comparison)
    
    # Sort by delay and bandwidth
    comparison_results.sort(key=lambda x: (x['delay'], x['bandwidth']))
    
    # Generate CSV report
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Test Case', 'Delay (ms)', 'Loss (%)', 'Bandwidth (Mbps)',
            'HTTP/2 Throughput (req/s)', 'HTTP/3 Throughput (req/s)',
            'HTTP/2 Latency (ms)', 'HTTP/3 Latency (ms)',
            'HTTP/2 Connection Time (ms)', 'HTTP/3 Connection Time (ms)',
            'Throughput Advantage (%)', 'Latency Advantage (%)', 'Connection Advantage (%)'
        ])
        
        for result in comparison_results:
            writer.writerow([
                result.get('test_case', ''),
                result.get('delay', ''),
                result.get('loss', ''),
                result.get('bandwidth', ''),
                result.get('h2_throughput', ''),
                result.get('h3_throughput', ''),
                result.get('h2_latency', ''),
                result.get('h3_latency', ''),
                result.get('h2_connection_time', ''),
                result.get('h3_connection_time', ''),
                result.get('throughput_advantage', ''),
                result.get('latency_advantage', ''),
                result.get('connection_advantage', '')
            ])
    
    # Generate text report
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("極端なネットワーク条件でのHTTP/3 vs HTTP/2性能比較レポート\n")
        f.write("=" * 80 + "\n")
        f.write(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("目的: 極端な高遅延・高損失・低帯域条件でのHTTP/3優位性の検証\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("テストケース別詳細分析\n")
        f.write("=" * 80 + "\n\n")
        
        for result in comparison_results:
            f.write(f"テストケース: {result['test_case']}\n")
            f.write("-" * 60 + "\n")
            f.write(f"ネットワーク条件: {result['delay']}ms遅延, {result['loss']}%損失, {result['bandwidth']}Mbps帯域\n\n")
            
            # Throughput comparison
            if result['h2_throughput'] and result['h3_throughput']:
                f.write("スループット比較:\n")
                f.write(f"  HTTP/2: {result['h2_throughput']:.2f} req/s\n")
                f.write(f"  HTTP/3: {result['h3_throughput']:.2f} req/s\n")
                if result['throughput_advantage']:
                    if result['throughput_advantage'] > 0:
                        f.write(f"  HTTP/3優位: +{result['throughput_advantage']:.1f}%\n")
                    else:
                        f.write(f"  HTTP/2優位: {result['throughput_advantage']:.1f}%\n")
                f.write("\n")
            
            # Latency comparison
            if result['h2_latency'] and result['h3_latency']:
                f.write("レイテンシ比較:\n")
                f.write(f"  HTTP/2: {result['h2_latency']:.3f} ms\n")
                f.write(f"  HTTP/3: {result['h3_latency']:.3f} ms\n")
                if result['latency_advantage']:
                    if result['latency_advantage'] > 0:
                        f.write(f"  HTTP/3優位: +{result['latency_advantage']:.1f}%\n")
                    else:
                        f.write(f"  HTTP/2優位: {result['latency_advantage']:.1f}%\n")
                f.write("\n")
            
            # Connection time comparison
            if result['h2_connection_time'] and result['h3_connection_time']:
                f.write("接続時間比較:\n")
                f.write(f"  HTTP/2: {result['h2_connection_time']:.3f} ms\n")
                f.write(f"  HTTP/3: {result['h3_connection_time']:.3f} ms\n")
                if result['connection_advantage']:
                    if result['connection_advantage'] > 0:
                        f.write(f"  HTTP/3優位: +{result['connection_advantage']:.1f}%\n")
                    else:
                        f.write(f"  HTTP/2優位: {result['connection_advantage']:.1f}%\n")
                f.write("\n")
            
            f.write("\n")
        
        # Summary analysis
        f.write("=" * 80 + "\n")
        f.write("総合分析\n")
        f.write("=" * 80 + "\n\n")
        
        # Count advantages
        throughput_advantages = [r['throughput_advantage'] for r in comparison_results if r['throughput_advantage'] is not None]
        latency_advantages = [r['latency_advantage'] for r in comparison_results if r['latency_advantage'] is not None]
        connection_advantages = [r['connection_advantage'] for r in comparison_results if r['connection_advantage'] is not None]
        
        if throughput_advantages:
            avg_throughput_adv = np.mean(throughput_advantages)
            f.write(f"平均スループット優位性: {avg_throughput_adv:.1f}%\n")
            if avg_throughput_adv > 0:
                f.write("→ HTTP/3がスループットで優位\n")
            else:
                f.write("→ HTTP/2がスループットで優位\n")
        
        if latency_advantages:
            avg_latency_adv = np.mean(latency_advantages)
            f.write(f"平均レイテンシ優位性: {avg_latency_adv:.1f}%\n")
            if avg_latency_adv > 0:
                f.write("→ HTTP/3がレイテンシで優位\n")
            else:
                f.write("→ HTTP/2がレイテンシで優位\n")
        
        if connection_advantages:
            avg_connection_adv = np.mean(connection_advantages)
            f.write(f"平均接続時間優位性: {avg_connection_adv:.1f}%\n")
            if avg_connection_adv > 0:
                f.write("→ HTTP/3が接続時間で優位\n")
            else:
                f.write("→ HTTP/2が接続時間で優位\n")
        
        f.write("\n")
        
        # Extreme conditions analysis
        extreme_results = [r for r in comparison_results if r['delay'] >= 400 and r['loss'] >= 7]
        if extreme_results:
            f.write("極端な条件（400ms以上遅延、7%以上損失）での分析:\n")
            f.write("-" * 50 + "\n")
            
            extp_advantages = [r['throughput_advantage'] for r in extreme_results if r['throughput_advantage'] is not None]
            exlat_advantages = [r['latency_advantage'] for r in extreme_results if r['latency_advantage'] is not None]
            
            if extp_advantages:
                avg_extp = np.mean(extp_advantages)
                f.write(f"極端な条件での平均スループット優位性: {avg_extp:.1f}%\n")
            
            if exlat_advantages:
                avg_exlat = np.mean(exlat_advantages)
                f.write(f"極端な条件での平均レイテンシ優位性: {avg_exlat:.1f}%\n")
            
            f.write("\n")
        
        # Very low bandwidth analysis
        very_low_bw_results = [r for r in comparison_results if r['bandwidth'] <= 5]
        if very_low_bw_results:
            f.write("極低帯域環境（5Mbps以下）での分析:\n")
            f.write("-" * 40 + "\n")
            
            vlbw_tp_advantages = [r['throughput_advantage'] for r in very_low_bw_results if r['throughput_advantage'] is not None]
            vlbw_lat_advantages = [r['latency_advantage'] for r in very_low_bw_results if r['latency_advantage'] is not None]
            
            if vlbw_tp_advantages:
                avg_vlbw_tp = np.mean(vlbw_tp_advantages)
                f.write(f"極低帯域環境での平均スループット優位性: {avg_vlbw_tp:.1f}%\n")
            
            if vlbw_lat_advantages:
                avg_vlbw_lat = np.mean(vlbw_lat_advantages)
                f.write(f"極低帯域環境での平均レイテンシ優位性: {avg_vlbw_lat:.1f}%\n")
            
            f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("結論\n")
        f.write("=" * 80 + "\n")
        f.write("このレポートは、極端なネットワーク条件での\n")
        f.write("HTTP/3とHTTP/2の性能比較を提供します。\n\n")
        
        f.write("論文の仮説検証:\n")
        f.write("- 極端な高遅延環境でのHTTP/3優位性\n")
        f.write("- 極端な高損失環境でのHTTP/3優位性\n")
        f.write("- 極低帯域環境でのHTTP/3優位性\n")
        f.write("- ネットワーク制約下でのプロトコル選択指針\n\n")
        
        f.write("詳細なCSVデータ: " + csv_file + "\n")
    
    print(f"極端な条件分析レポート生成完了:")
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
    
    print(f"極端なネットワーク条件でのHTTP/3 vs HTTP/2性能分析を開始... (log_dir={log_dir})")
    generate_extreme_conditions_report(log_dir)
    print("分析完了!")

if __name__ == "__main__":
    main() 