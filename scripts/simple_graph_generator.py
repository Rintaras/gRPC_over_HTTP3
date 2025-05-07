#!/usr/bin/env python3
"""
Simple Performance Graph Generator for HTTP/2 vs HTTP/3 Benchmark Results
Compatible with Python 3.13+
"""

import os
import sys
import csv
import statistics
import argparse
from pathlib import Path

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available, graphs will not be generated")

def parse_csv_data(csv_file):
    """Parse CSV data and extract response times"""
    response_times = []
    try:
        with open(csv_file, 'r') as f:
            # Try comma first, then tab as fallback
            content = f.read()
            if ',' in content:
                delimiter = ','
            else:
                delimiter = '\t'
            
            f.seek(0)  # Reset file pointer
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                if len(row) >= 3:
                    try:
                        # Third column is response time in microseconds
                        response_time = float(row[2])
                        response_times.append(response_time)
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")
        return []
    
    return response_times

def calculate_statistics(response_times):
    """Calculate basic statistics from response times"""
    if not response_times:
        return None
    
    # Convert microseconds to milliseconds
    times_ms = [t / 1000.0 for t in response_times]
    
    stats = {
        'count': len(times_ms),
        'mean': statistics.mean(times_ms),
        'median': statistics.median(times_ms),
        'min': min(times_ms),
        'max': max(times_ms),
        'std': statistics.stdev(times_ms) if len(times_ms) > 1 else 0
    }
    
    return stats

def generate_graphs(benchmark_dir, debug: bool, dpi: int, only_conditions: list[str] | None = None):
    """Generate performance comparison graphs"""
    if not MATPLOTLIB_AVAILABLE:
        print("Skipping graph generation - matplotlib not available")
        return
    
    # Find all CSV files
    csv_files = []
    for file in os.listdir(benchmark_dir):
        if file.endswith('.csv'):
            csv_files.append(file)
    
    if not csv_files:
        print("No CSV files found for graph generation")
        return
    
    # Group files by protocol
    h2_files = [f for f in csv_files if f.startswith('h2_')]
    h3_files = [f for f in csv_files if f.startswith('h3_')]
    
    # Extract network conditions
    conditions = []
    for h2_file in h2_files:
        condition = h2_file.replace('h2_', '').replace('.csv', '')
        if f"h3_{condition}.csv" in h3_files:
            if only_conditions is None or condition in only_conditions:
                conditions.append(condition)
    
    if not conditions:
        print("No matching HTTP/2 and HTTP/3 files found")
        return
    
    # Prepare data for plotting
    h2_means = []
    h3_means = []
    h2_stds = []
    h3_stds = []
    condition_labels = []
    
    for condition in sorted(conditions):
        h2_file = os.path.join(benchmark_dir, f"h2_{condition}.csv")
        h3_file = os.path.join(benchmark_dir, f"h3_{condition}.csv")
        
        h2_stats = calculate_statistics(parse_csv_data(h2_file))
        h3_stats = calculate_statistics(parse_csv_data(h3_file))
        
        if h2_stats and h3_stats:
            h2_means.append(h2_stats['mean'])
            h3_means.append(h3_stats['mean'])
            h2_stds.append(h2_stats['std'])
            h3_stds.append(h3_stats['std'])
            
            # Format condition label
            if 'ms' in condition and 'pct' in condition:
                delay = condition.split('ms')[0]
                loss = condition.split('pct')[0].split('_')[-1]
                condition_labels.append(f"{delay}ms, {loss}% loss")
            else:
                condition_labels.append(condition)
    
    if not h2_means:
        print("No valid data for graph generation")
        return
    
    if debug:
        print(f"Debug: Found {len(conditions)} conditions: {conditions}")
        print(f"Debug: h2_means: {h2_means}")
        print(f"Debug: h3_means: {h3_means}")
        print(f"Debug: condition_labels: {condition_labels}")
    
    # Create the graph
    plt.figure(figsize=(12, 8))
    
    x = range(len(conditions))
    width = 0.35
    
    # Create bars without error bars
    bars1 = plt.bar([i - width/2 for i in x], h2_means, width, 
                    label='HTTP/2', color='#1f77b4', alpha=0.8)
    bars2 = plt.bar([i + width/2 for i in x], h3_means, width, 
                    label='HTTP/3', color='#ff7f0e', alpha=0.8)
    
    # Customize the graph
    plt.xlabel('Network Conditions', fontsize=12)
    plt.ylabel('Mean Response Time (ms)', fontsize=12)
    plt.title('HTTP/2 vs HTTP/3 Performance Comparison\nResponse Time by Network Conditions', fontsize=14, fontweight='bold')
    plt.xticks(x, condition_labels, rotation=45, ha='right')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for i, (h2_mean, h3_mean) in enumerate(zip(h2_means, h3_means)):
        plt.text(i - width/2, h2_mean + 50, f'{h2_mean:.0f}', 
                ha='center', va='bottom', fontsize=10)
        plt.text(i + width/2, h3_mean + 50, f'{h3_mean:.0f}', 
                ha='center', va='bottom', fontsize=10)
    
    # Add performance improvement annotations
    for i, (h2_mean, h3_mean) in enumerate(zip(h2_means, h3_means)):
        if h3_mean > 0:
            improvement = ((h2_mean - h3_mean) / h2_mean) * 100
            if abs(improvement) > 5:  # Only show significant differences
                if improvement > 0:
                    plt.annotate(f'HTTP/3\n+{improvement:.1f}%', 
                                xy=(i + width/2, h3_mean), xytext=(i + width/2, h3_mean + max(h3_means) * 0.1),
                                ha='center', va='bottom', fontsize=9, fontweight='bold',
                                arrowprops=dict(arrowstyle='->', color='green', lw=1.5))
                else:
                    plt.annotate(f'HTTP/2\n+{abs(improvement):.1f}%', 
                                xy=(i - width/2, h2_mean), xytext=(i - width/2, h2_mean + max(h2_means) * 0.1),
                                ha='center', va='bottom', fontsize=9, fontweight='bold',
                                arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))
    
    plt.tight_layout()
    
    # Save the graph
    graph_file = os.path.join(benchmark_dir, 'performance_comparison_graph.png')
    plt.savefig(graph_file, dpi=dpi, bbox_inches='tight')
    plt.close()
    
    print(f"Performance graph generated: {graph_file}")
    
    # Generate summary statistics graph
    generate_summary_graph(benchmark_dir, conditions, h2_means, h3_means, h2_stds, h3_stds, dpi)

def generate_summary_graph(benchmark_dir, conditions, h2_means, h3_means, h2_stds, h3_stds, dpi: int):
    """Generate a summary statistics graph with 2-panel layout"""
    if not MATPLOTLIB_AVAILABLE:
        return
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    x = range(len(conditions))
    width = 0.35
    
    # Response time comparison (top panel)
    bars1 = ax1.bar([i - width/2 for i in x], h2_means, width, 
                    label='HTTP/2', color='#1f77b4', alpha=0.8)
    bars2 = ax1.bar([i + width/2 for i in x], h3_means, width, 
                    label='HTTP/3', color='#ff7f0e', alpha=0.8)
    
    ax1.set_ylabel('Response Time (ms)', fontsize=12)
    ax1.set_title('Response Time Comparison', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Performance improvement percentage (bottom panel)
    improvements = []
    for h2_mean, h3_mean in zip(h2_means, h3_means):
        if h2_mean > 0:
            improvement = ((h2_mean - h3_mean) / h2_mean) * 100
            improvements.append(improvement)
        else:
            improvements.append(0)
    
    # Use red color for negative improvements (HTTP/3 slower)
    colors = ['red' for _ in improvements]  # All red as per image
    bars3 = ax2.bar(x, improvements, color=colors, alpha=0.7)
    
    ax2.set_xlabel('Network Conditions', fontsize=12)
    ax2.set_ylabel('Performance Improvement (%)', fontsize=12)
    ax2.set_title('HTTP/3 Performance Improvement vs HTTP/2', fontsize=14, fontweight='bold')
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax2.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for i, improvement in enumerate(improvements):
        # Position labels above/below bars based on value
        if improvement >= 0:
            ax2.text(i, improvement + 1, f'{improvement:.1f}%', 
                    ha='center', va='bottom', fontsize=10)
        else:
            ax2.text(i, improvement - 1, f'{improvement:.1f}%', 
                    ha='center', va='top', fontsize=10)
    
    # Set x-axis labels for both panels
    condition_labels = []
    for condition in conditions:
        if 'ms' in condition and 'pct' in condition:
            delay = condition.split('ms')[0]
            loss = condition.split('pct')[0].split('_')[-1]
            condition_labels.append(f"{delay}ms\n{loss}% loss")
        else:
            condition_labels.append(condition)
    
    # Set x-axis for both panels
    ax1.set_xticks(x)
    ax1.set_xticklabels(condition_labels, rotation=0)
    ax2.set_xticks(x)
    ax2.set_xticklabels(condition_labels, rotation=0)
    
    plt.tight_layout()
    
    # Save the summary graph
    summary_graph_file = os.path.join(benchmark_dir, 'performance_summary_graph.png')
    plt.savefig(summary_graph_file, dpi=dpi, bbox_inches='tight')
    plt.close()
    
    print(f"Summary graph generated: {summary_graph_file}")

def generate_text_report(benchmark_dir, summary_csv_path: str | None = None, delimiter_hint: str | None = None):
    """Generate a text-based performance report"""
    report_file = os.path.join(benchmark_dir, 'performance_report.txt')
    
    # Find all CSV files
    csv_files = []
    for file in os.listdir(benchmark_dir):
        if file.endswith('.csv'):
            csv_files.append(file)
    
    if not csv_files:
        print("No CSV files found")
        return
    
    # Group files by protocol
    h2_files = [f for f in csv_files if f.startswith('h2_')]
    h3_files = [f for f in csv_files if f.startswith('h3_')]
    
    with open(report_file, 'w') as f:
        f.write("HTTP/2 vs HTTP/3 Performance Benchmark Report\n")
        f.write("=" * 50 + "\n\n")
        
        # Process HTTP/2 files
        f.write("HTTP/2 Results:\n")
        f.write("-" * 20 + "\n")
        for csv_file in sorted(h2_files):
            file_path = os.path.join(benchmark_dir, csv_file)
            response_times = parse_csv_data(file_path)
            stats = calculate_statistics(response_times)
            
            if stats:
                f.write(f"\n{csv_file}:\n")
                f.write(f"  Requests: {stats['count']}\n")
                f.write(f"  Mean Response Time: {stats['mean']:.2f} ms\n")
                f.write(f"  Median Response Time: {stats['median']:.2f} ms\n")
                f.write(f"  Min Response Time: {stats['min']:.2f} ms\n")
                f.write(f"  Max Response Time: {stats['max']:.2f} ms\n")
                f.write(f"  Standard Deviation: {stats['std']:.2f} ms\n")
        
        f.write("\n" + "=" * 50 + "\n\n")
        
        # Process HTTP/3 files
        f.write("HTTP/3 Results:\n")
        f.write("-" * 20 + "\n")
        for csv_file in sorted(h3_files):
            file_path = os.path.join(benchmark_dir, csv_file)
            response_times = parse_csv_data(file_path)
            stats = calculate_statistics(response_times)
            
            if stats:
                f.write(f"\n{csv_file}:\n")
                f.write(f"  Requests: {stats['count']}\n")
                f.write(f"  Mean Response Time: {stats['mean']:.2f} ms\n")
                f.write(f"  Median Response Time: {stats['median']:.2f} ms\n")
                f.write(f"  Min Response Time: {stats['min']:.2f} ms\n")
                f.write(f"  Max Response Time: {stats['max']:.2f} ms\n")
                f.write(f"  Standard Deviation: {stats['std']:.2f} ms\n")
        
        # Performance comparison
        f.write("\n" + "=" * 50 + "\n\n")
        f.write("Performance Comparison:\n")
        f.write("-" * 25 + "\n")
        
        # Compare same network conditions
        comparison_rows = []
        for h2_file in sorted(h2_files):
            # Extract network conditions from filename
            conditions = h2_file.replace('h2_', '').replace('.csv', '')
            h3_file = f"h3_{conditions}.csv"
            
            if h3_file in h3_files:
                h2_path = os.path.join(benchmark_dir, h2_file)
                h3_path = os.path.join(benchmark_dir, h3_file)
                
                h2_stats = calculate_statistics(parse_csv_data(h2_path))
                h3_stats = calculate_statistics(parse_csv_data(h3_path))
                
                if h2_stats and h3_stats:
                    f.write(f"\n{conditions}:\n")
                    f.write(f"  HTTP/2 Mean: {h2_stats['mean']:.2f} ms\n")
                    f.write(f"  HTTP/3 Mean: {h3_stats['mean']:.2f} ms\n")
                    
                    if h3_stats['mean'] > 0:
                        improvement = ((h2_stats['mean'] - h3_stats['mean']) / h2_stats['mean']) * 100
                        if improvement > 0:
                            f.write(f"  HTTP/3 Improvement: {improvement:.1f}%\n")
                        else:
                            f.write(f"  HTTP/2 Better by: {abs(improvement):.1f}%\n")
                        comparison_rows.append([
                            conditions,
                            f"{h2_stats['mean']:.2f}",
                            f"{h3_stats['mean']:.2f}",
                            f"{improvement:.1f}"
                        ])
    
    print(f"Performance report generated: {report_file}")

    # Optional: write summary CSV
    if summary_csv_path and comparison_rows:
        try:
            with open(summary_csv_path, 'w', newline='') as sf:
                writer = csv.writer(sf)
                writer.writerow(["condition", "http2_mean_ms", "http3_mean_ms", "improvement_pct"])
                writer.writerows(comparison_rows)
            print(f"Summary CSV written: {summary_csv_path}")
        except Exception as e:
            print(f"Failed to write summary CSV: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate performance report and graphs for HTTP/2 vs HTTP/3 benchmarks")
    parser.add_argument("benchmark_directory", help="Directory containing h2_*.csv and h3_*.csv")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for saved figures (default: 300)")
    parser.add_argument("--summary-csv", dest="summary_csv", default=None, help="Optional path to write comparison summary CSV")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--only", help="Comma-separated condition keys to include (e.g., '0ms_3pct,75ms_3pct')")
    args = parser.parse_args()

    benchmark_dir = args.benchmark_directory

    if not os.path.exists(benchmark_dir):
        print(f"Directory not found: {benchmark_dir}")
        sys.exit(1)

    print(f"Generating performance report and graphs for: {benchmark_dir}")

    # Generate text report and optional CSV
    generate_text_report(benchmark_dir, summary_csv_path=args.summary_csv)

    # Generate graphs with options
    only = None
    if args.only:
        only = [c.strip() for c in args.only.split(',') if c.strip()]
    generate_graphs(benchmark_dir, debug=args.debug, dpi=args.dpi, only_conditions=only)

    print("Report and graph generation completed!")

if __name__ == "__main__":
    main()
