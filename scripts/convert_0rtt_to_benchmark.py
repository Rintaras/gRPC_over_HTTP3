#!/usr/bin/env python3

import os
import sys
import glob
import re
from datetime import datetime

def parse_0rtt_results(log_dir):
    """0-RTTテスト結果を解析してベンチマーク形式に変換"""
    
    results = []
    
    # HTTP/2結果を解析
    h2_files = glob.glob(os.path.join(log_dir, "http2_*.log"))
    for file in h2_files:
        with open(file, 'r') as f:
            content = f.read()
            
        # 接続時間を抽出
        connect_match = re.search(r'Connection time for http2.*: ([\d.]+)s', content)
        if connect_match:
            connect_time = float(connect_match.group(1))
            
            # ファイル名からテストタイプを抽出
            test_type = os.path.basename(file).replace('.log', '')
            
            results.append({
                'protocol': 'HTTP/2',
                'test_type': test_type,
                'connect_time': connect_time,
                'throughput': 0,  # 0-RTTテストではスループットは測定していない
                'latency': connect_time * 1000,  # msに変換
                'delay': 0,
                'loss': 0
            })
    
    # HTTP/3結果を解析
    h3_files = glob.glob(os.path.join(log_dir, "http3_*.log"))
    for file in h3_files:
        with open(file, 'r') as f:
            content = f.read()
            
        # 接続時間を抽出
        connect_match = re.search(r'Connection time for http3.*: ([\d.]+)s', content)
        if connect_match:
            connect_time = float(connect_match.group(1))
            
            # ファイル名からテストタイプを抽出
            test_type = os.path.basename(file).replace('.log', '')
            
            results.append({
                'protocol': 'HTTP/3',
                'test_type': test_type,
                'connect_time': connect_time,
                'throughput': 0,  # 0-RTTテストではスループットは測定していない
                'latency': connect_time * 1000,  # msに変換
                'delay': 0,
                'loss': 0
            })
    
    return results

def create_benchmark_csv(results, output_dir):
    """結果をCSV形式で保存"""
    
    # ベンチマーク形式のCSVを作成
    csv_content = []
    csv_content.append("Protocol,Test_Type,Connect_Time,Throughput,Latency,Delay,Loss")
    
    for result in results:
        csv_content.append(f"{result['protocol']},{result['test_type']},{result['connect_time']:.6f},{result['throughput']},{result['latency']:.2f},{result['delay']},{result['loss']}")
    
    # CSVファイルを保存
    csv_file = os.path.join(output_dir, "0rtt_benchmark_results.csv")
    with open(csv_file, 'w') as f:
        f.write('\n'.join(csv_content))
    
    print(f"CSV file created: {csv_file}")
    return csv_file

def create_summary_report(results, output_dir):
    """サマリーレポートを作成"""
    
    # 統計を計算
    h2_connect_times = [r['connect_time'] for r in results if r['protocol'] == 'HTTP/2']
    h3_connect_times = [r['connect_time'] for r in results if r['protocol'] == 'HTTP/3']
    
    if h2_connect_times and h3_connect_times:
        h2_avg = sum(h2_connect_times) / len(h2_connect_times)
        h3_avg = sum(h3_connect_times) / len(h3_connect_times)
        advantage = ((h2_avg - h3_avg) / h2_avg * 100) if h2_avg > 0 else 0
        
        report_content = f"""
================================================================================
0-RTT Connection Performance Analysis Report
================================================================================
Generated Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 Connection Time Analysis
----------------------------------------
• HTTP/2 Average Connection Time: {h2_avg:.6f}s
• HTTP/3 Average Connection Time: {h3_avg:.6f}s
• HTTP/3 Advantage: {advantage:.2f}%

🎯 Key Findings
----------------------------------------
• HTTP/3 0-RTT Connection Performance: {'Superior' if advantage > 0 else 'Inferior'}
• Connection Time Difference: {abs(h2_avg - h3_avg):.6f}s
• Performance Ratio: {h3_avg/h2_avg:.2f}x

📈 Detailed Results
----------------------------------------
"""
        
        for result in results:
            report_content += f"• {result['protocol']} {result['test_type']}: {result['connect_time']:.6f}s\n"
        
        report_content += f"""
🔍 Analysis
----------------------------------------
• 0-RTT Connection Advantage: {'Confirmed' if advantage > 0 else 'Not Confirmed'}
• Connection Establishment: HTTP/3 {'Faster' if advantage > 0 else 'Slower'}
• Practical Impact: {'Significant' if abs(advantage) > 10 else 'Minor'}

📁 Files Generated
----------------------------------------
• 0rtt_benchmark_results.csv - Detailed connection time data
• This report - Performance analysis summary
"""
        
        report_file = os.path.join(output_dir, "0rtt_performance_summary.txt")
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        print(f"Summary report created: {report_file}")
        return report_file
    
    return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 convert_0rtt_to_benchmark.py <log_directory>")
        sys.exit(1)
    
    log_dir = sys.argv[1]
    
    if not os.path.exists(log_dir):
        print(f"Error: Directory {log_dir} does not exist")
        sys.exit(1)
    
    print(f"Converting 0-RTT results from: {log_dir}")
    
    # 結果を解析
    results = parse_0rtt_results(log_dir)
    
    if not results:
        print("No results found in the specified directory")
        sys.exit(1)
    
    print(f"Found {len(results)} test results")
    
    # CSVファイルを作成
    csv_file = create_benchmark_csv(results, log_dir)
    
    # サマリーレポートを作成
    report_file = create_summary_report(results, log_dir)
    
    print("Conversion completed successfully!")
    print(f"Results saved in: {log_dir}")

if __name__ == "__main__":
    main() 