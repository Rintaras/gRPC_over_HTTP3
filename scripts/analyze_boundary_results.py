#!/usr/bin/env python3
"""
HTTP/2 vs HTTP/3 Performance Boundary Analysis
境界値分析結果の解析とレポート生成
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

# 日本語フォント設定
plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Hiragino Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_boundary_data(log_dir):
    """境界値分析データを読み込み"""
    csv_files = list(Path(log_dir).glob("*.csv"))
    all_data = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            df['test_case'] = csv_file.stem
            all_data.append(df)
            print(f"✓ データ読み込み: {csv_file.name} ({len(df)} records)")
        except Exception as e:
            print(f"✗ データ読み込みエラー: {csv_file.name} - {e}")
    
    if not all_data:
        raise ValueError("有効なCSVファイルが見つかりません")
    
    return pd.concat(all_data, ignore_index=True)

def detect_boundaries(df, threshold=5.0):
    """性能境界値を検出（性能逆転点を探す）"""
    boundaries = []
    
    # 同じネットワーク条件下でのHTTP/2とHTTP/3の比較
    for delay in df['delay_ms'].unique():
        for loss in df['loss_pct'].unique():
            for bandwidth in df['bandwidth_mbps'].unique():
                
                # 同じ条件下のデータを取得
                condition_data = df[
                    (df['delay_ms'] == delay) & 
                    (df['loss_pct'] == loss) & 
                    (df['bandwidth_mbps'] == bandwidth)
                ]
                
                if len(condition_data) < 2:
                    continue
                
                # HTTP/2とHTTP/3のデータを分離
                h2_data = condition_data[condition_data['protocol'] == 'http2']
                h3_data = condition_data[condition_data['protocol'] == 'http3']
                
                if len(h2_data) == 0 or len(h3_data) == 0:
                    continue
                
                # 平均スループットを計算
                h2_avg = h2_data['throughput_req_s'].mean()
                h3_avg = h3_data['throughput_req_s'].mean()
                
                # 性能差を計算
                if h3_avg > 0:
                    diff_pct = ((h2_avg - h3_avg) / h3_avg) * 100
                else:
                    continue
                
                # 境界値の条件を修正
                # 1. 性能差が閾値以内（逆転の可能性）
                # 2. または、HTTP/3がHTTP/2を上回る場合
                is_boundary = (
                    abs(diff_pct) <= threshold or  # 性能差が小さい
                    diff_pct < 0  # HTTP/3が優位
                )
                
                if is_boundary:
                    superior_protocol = 'HTTP/3' if diff_pct < 0 else 'HTTP/2'
                    boundaries.append({
                        'delay_ms': delay,
                        'loss_pct': loss,
                        'bandwidth_mbps': bandwidth,
                        'h2_throughput': h2_avg,
                        'h3_throughput': h3_avg,
                        'throughput_diff_pct': diff_pct,
                        'superior_protocol': superior_protocol,
                        'boundary_type': 'performance_crossover' if diff_pct < 0 else 'close_performance'
                    })
    
    return boundaries

def analyze_boundary_patterns(df, boundaries):
    """境界値パターンを分析"""
    analysis = {
        'total_tests': len(df),
        'total_boundaries': len(boundaries),
        'statistics': {}
    }
    
    if boundaries:
        # 境界値の統計
        diff_values = [b['throughput_diff_pct'] for b in boundaries]
        analysis['statistics'] = {
            'avg_throughput_diff': np.mean(diff_values),
            'max_throughput_diff': np.max(diff_values),
            'min_throughput_diff': np.min(diff_values),
            'std_throughput_diff': np.std(diff_values)
        }
        
        # 境界値タイプの分類
        crossovers = [b for b in boundaries if b['boundary_type'] == 'performance_crossover']
        close_performance = [b for b in boundaries if b['boundary_type'] == 'close_performance']
        
        analysis['crossover_count'] = len(crossovers)
        analysis['close_performance_count'] = len(close_performance)
        
        # 遅延範囲の分析
        if boundaries:
            delays = [b['delay_ms'] for b in boundaries]
            analysis['delay_ranges'] = {
                'min_delay': min(delays),
                'max_delay': max(delays),
                'avg_delay': np.mean(delays)
            }
    
    return analysis

def generate_boundary_graphs(df, boundaries, output_dir):
    """境界値分析グラフを生成"""
    # 日本語フォント設定
    plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Hiragino Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    plt.style.use('seaborn-v0_8')
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # データ準備
    h2_data = df[df['protocol'] == 'http2']
    h3_data = df[df['protocol'] == 'http3']
    
    # 1. スループット比較グラフ
    ax1 = axes[0, 0]
    ax1.scatter(h2_data['delay_ms'], h2_data['throughput_req_s'], 
                c='blue', s=30, alpha=0.6, label='HTTP/2', marker='o')
    ax1.scatter(h3_data['delay_ms'], h3_data['throughput_req_s'], 
                c='red', s=30, alpha=0.6, label='HTTP/3', marker='s')
    
    # 境界値をマーク
    if boundaries:
        boundary_df = pd.DataFrame(boundaries)
        # 性能逆転点（HTTP/3優位）
        crossovers = boundary_df[boundary_df['boundary_type'] == 'performance_crossover']
        if not crossovers.empty:
            ax1.scatter(crossovers['delay_ms'], crossovers['h3_throughput'], 
                       c='red', s=200, marker='*', edgecolors='black', linewidth=2, 
                       label='性能逆転点 (HTTP/3優位)', zorder=5)
        
        # 性能接近点
        close_points = boundary_df[boundary_df['boundary_type'] == 'close_performance']
        if not close_points.empty:
            ax1.scatter(close_points['delay_ms'], close_points['h2_throughput'], 
                       c='orange', s=150, marker='^', edgecolors='black', linewidth=2, 
                       label='性能接近点', zorder=5)
    
    ax1.set_xlabel('遅延 (ms)')
    ax1.set_ylabel('スループット (req/s)')
    ax1.set_title('HTTP/2 vs HTTP/3 スループット比較')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 性能差異グラフ
    ax2 = axes[0, 1]
    # 全データポイントの性能差を計算
    performance_diff = []
    for delay in df['delay_ms'].unique():
        delay_data = df[df['delay_ms'] == delay]
        h2_avg = delay_data[delay_data['protocol'] == 'http2']['throughput_req_s'].mean()
        h3_avg = delay_data[delay_data['protocol'] == 'http3']['throughput_req_s'].mean()
        if h3_avg > 0:
            diff = ((h2_avg - h3_avg) / h3_avg) * 100
            performance_diff.append({'delay': delay, 'diff': diff})
    
    if performance_diff:
        diff_df = pd.DataFrame(performance_diff)
        ax2.scatter(diff_df['delay'], diff_df['diff'], c='purple', s=50, alpha=0.7)
        
        # 境界線を追加
        ax2.axhline(y=0, color='red', linestyle='--', alpha=0.7, label='性能均衡線')
        ax2.axhline(y=5, color='orange', linestyle=':', alpha=0.7, label='+5%境界')
        ax2.axhline(y=-5, color='orange', linestyle=':', alpha=0.7, label='-5%境界')
        
        # 境界値ポイントを強調
        if boundaries:
            boundary_df = pd.DataFrame(boundaries)
            crossovers = boundary_df[boundary_df['boundary_type'] == 'performance_crossover']
            if not crossovers.empty:
                ax2.scatter(crossovers['delay_ms'], crossovers['throughput_diff_pct'], 
                           c='red', s=200, marker='*', edgecolors='black', linewidth=2, zorder=5)
            
            close_points = boundary_df[boundary_df['boundary_type'] == 'close_performance']
            if not close_points.empty:
                ax2.scatter(close_points['delay_ms'], close_points['throughput_diff_pct'], 
                           c='orange', s=150, marker='^', edgecolors='black', linewidth=2, zorder=5)
    
    ax2.set_xlabel('遅延 (ms)')
    ax2.set_ylabel('性能差 (%)')
    ax2.set_title('HTTP/2 vs HTTP/3 性能差異')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 境界値マップ
    ax3 = axes[1, 0]
    if boundaries:
        boundary_df = pd.DataFrame(boundaries)
        
        # 境界値の種類別にプロット
        crossovers = boundary_df[boundary_df['boundary_type'] == 'performance_crossover']
        close_points = boundary_df[boundary_df['boundary_type'] == 'close_performance']
        
        if not crossovers.empty:
            ax3.scatter(crossovers['delay_ms'], crossovers['loss_pct'], 
                       c='red', s=200, marker='*', edgecolors='black', linewidth=2, 
                       label='性能逆転点', zorder=5)
        
        if not close_points.empty:
            ax3.scatter(close_points['delay_ms'], close_points['loss_pct'], 
                       c='orange', s=150, marker='^', edgecolors='black', linewidth=2, 
                       label='性能接近点', zorder=5)
        
        # 境界線を描画
        if not crossovers.empty:
            # 性能逆転点の境界線
            crossover_delays = sorted(crossovers['delay_ms'].unique())
            if len(crossover_delays) > 1:
                ax3.plot(crossover_delays, [0] * len(crossover_delays), 
                        'r--', linewidth=2, alpha=0.7, label='逆転境界線')
    
    ax3.set_xlabel('遅延 (ms)')
    ax3.set_ylabel('パケット損失率 (%)')
    ax3.set_title('境界値マップ')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 境界値詳細
    ax4 = axes[1, 1]
    if boundaries:
        boundary_df = pd.DataFrame(boundaries)
        
        # 境界値の分布
        crossovers = boundary_df[boundary_df['boundary_type'] == 'performance_crossover']
        close_points = boundary_df[boundary_df['boundary_type'] == 'close_performance']
        
        if not crossovers.empty:
            ax4.scatter(crossovers['delay_ms'], crossovers['throughput_diff_pct'], 
                       c='red', s=200, marker='*', edgecolors='black', linewidth=2, 
                       label='性能逆転点', zorder=5)
        
        if not close_points.empty:
            ax4.scatter(close_points['delay_ms'], close_points['throughput_diff_pct'], 
                       c='orange', s=150, marker='^', edgecolors='black', linewidth=2, 
                       label='性能接近点', zorder=5)
        
        # 境界線
        ax4.axhline(y=0, color='red', linestyle='--', alpha=0.7, label='均衡線')
        ax4.axhline(y=5, color='orange', linestyle=':', alpha=0.7, label='+5%線')
        ax4.axhline(y=-5, color='orange', linestyle=':', alpha=0.7, label='-5%線')
        
        # 境界値にラベルを追加
        for _, boundary in boundary_df.iterrows():
            if boundary['boundary_type'] == 'performance_crossover':
                ax4.annotate(f"HTTP/3\n{boundary['throughput_diff_pct']:.1f}%", 
                            (boundary['delay_ms'], boundary['throughput_diff_pct']),
                            xytext=(10, 10), textcoords='offset points',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.7),
                            fontsize=8, color='white')
            else:
                ax4.annotate(f"接近\n{boundary['throughput_diff_pct']:.1f}%", 
                            (boundary['delay_ms'], boundary['throughput_diff_pct']),
                            xytext=(10, 10), textcoords='offset points',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='orange', alpha=0.7),
                            fontsize=8, color='white')
    
    ax4.set_xlabel('遅延 (ms)')
    ax4.set_ylabel('性能差 (%)')
    ax4.set_title('境界値詳細')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/boundary_analysis_overview.png", dpi=300, bbox_inches='tight')
    print("✓ グラフ保存: boundary_analysis_overview.png")
    plt.close()

def generate_boundary_report(boundaries, analysis, output_dir):
    """境界値分析レポートを生成"""
    report_file = os.path.join(output_dir, "boundary_analysis_report.txt")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("HTTP/2 vs HTTP/3 性能境界値分析レポート\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("📊 分析概要\n")
        f.write("-" * 30 + "\n")
        f.write(f"総テスト数: {analysis['total_tests']}\n")
        f.write(f"境界値数: {len(boundaries)}\n")
        
        # 境界値の分類
        crossover_count = len([b for b in boundaries if b['boundary_type'] == 'performance_crossover'])
        close_count = len([b for b in boundaries if b['boundary_type'] == 'close_performance'])
        
        f.write(f"性能逆転点: {crossover_count} 個\n")
        f.write(f"性能接近点: {close_count} 個\n\n")
        
        f.write("🔍 境界値詳細\n")
        f.write("-" * 30 + "\n")
        
        if boundaries:
            # 性能逆転点を優先表示
            crossovers = [b for b in boundaries if b['boundary_type'] == 'performance_crossover']
            if crossovers:
                f.write("🚨 性能逆転点 (HTTP/3 > HTTP/2):\n")
                for i, boundary in enumerate(crossovers[:10], 1):  # 上位10件
                    f.write(f"  {i}. 遅延: {boundary['delay_ms']}ms, "
                           f"損失: {boundary['loss_pct']}%, "
                           f"帯域: {boundary['bandwidth_mbps']}Mbps\n")
                    f.write(f"     HTTP/2: {boundary['h2_throughput']:.1f} req/s, "
                           f"HTTP/3: {boundary['h3_throughput']:.1f} req/s\n")
                    f.write(f"     性能差: {boundary['throughput_diff_pct']:.1f}%\n\n")
            
            # 性能接近点
            close_performance = [b for b in boundaries if b['boundary_type'] == 'close_performance']
            if close_performance:
                f.write("⚖️ 性能接近点 (差5%以内):\n")
                for i, boundary in enumerate(close_performance[:10], 1):  # 上位10件
                    f.write(f"  {i}. 遅延: {boundary['delay_ms']}ms, "
                           f"損失: {boundary['loss_pct']}%, "
                           f"帯域: {boundary['bandwidth_mbps']}Mbps\n")
                    f.write(f"     HTTP/2: {boundary['h2_throughput']:.1f} req/s, "
                           f"HTTP/3: {boundary['h3_throughput']:.1f} req/s\n")
                    f.write(f"     性能差: {boundary['throughput_diff_pct']:.1f}%\n\n")
        else:
            f.write("❌ 境界値は検出されませんでした\n")
            f.write("   → すべての条件下でHTTP/2が明確に優位\n\n")
        
        f.write("📈 統計情報\n")
        f.write("-" * 30 + "\n")
        f.write(f"平均性能差: {analysis['statistics']['avg_throughput_diff']:.2f}%\n")
        f.write(f"最大性能差: {analysis['statistics']['max_throughput_diff']:.2f}%\n")
        f.write(f"最小性能差: {analysis['statistics']['min_throughput_diff']:.2f}%\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("レポート終了\n")
        f.write("=" * 60 + "\n")
    
    print(f"✓ レポート生成: {report_file}")

def main():
    parser = argparse.ArgumentParser(description='境界値分析結果の解析')
    parser.add_argument('log_dir', help='ログディレクトリパス')
    parser.add_argument('--output', '-o', help='出力ディレクトリ（デフォルト: ログディレクトリ）')
    
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir)
    output_dir = Path(args.output) if args.output else log_dir
    
    if not log_dir.exists():
        print(f"エラー: ログディレクトリが見つかりません: {log_dir}")
        sys.exit(1)
    
    print("=" * 60)
    print("HTTP/2 vs HTTP/3 境界値分析")
    print("=" * 60)
    
    try:
        # データ読み込み
        print("📂 データ読み込み中...")
        df = load_boundary_data(log_dir)
        print(f"✓ 総データ数: {len(df)} records")
        
        # 境界値検出
        print("\n🔍 境界値検出中...")
        boundaries = detect_boundaries(df)
        print(f"✓ 検出された境界値: {len(boundaries)} 個")
        
        # パターン分析
        print("\n📊 パターン分析中...")
        analysis = analyze_boundary_patterns(df, boundaries)
        
        # グラフ生成
        print("\n📈 グラフ生成中...")
        generate_boundary_graphs(df, boundaries, output_dir)
        
        # レポート生成
        print("\n📝 レポート生成中...")
        generate_boundary_report(boundaries, analysis, output_dir)
        
        # JSON出力
        try:
            # 境界値データの型変換
            serializable_boundaries = []
            for boundary in boundaries:
                serializable_boundary = {
                    'delay_ms': float(boundary['delay_ms']),
                    'loss_percent': float(boundary['loss_pct']), # Changed from loss_pct to loss_percent
                    'bandwidth_mbps': float(boundary['bandwidth_mbps']),
                    'h2_throughput': float(boundary['h2_throughput']),
                    'h3_throughput': float(boundary['h3_throughput']),
                    'throughput_diff': float(boundary['throughput_diff_pct']), # Changed from throughput_diff_pct to throughput_diff
                    'superior_protocol': boundary['superior_protocol']
                }
                serializable_boundaries.append(serializable_boundary)
            
            with open(os.path.join(output_dir, 'boundary_analysis_results.json'), 'w', encoding='utf-8') as f:
                json.dump({
                    'summary': {
                        'total_tests': int(len(df)),
                        'boundary_count': int(len(boundaries)),
                        'h2_superior_count': int(len([b for b in boundaries if b['superior_protocol'] == 'HTTP/2'])),
                        'h3_superior_count': int(len([b for b in boundaries if b['superior_protocol'] == 'HTTP/3'])),
                        'avg_performance_diff': float(analysis['statistics']['avg_throughput_diff']),
                        'max_performance_diff': float(analysis['statistics']['max_throughput_diff'])
                    },
                    'boundaries': serializable_boundaries
                }, f, ensure_ascii=False, indent=2)
            print("✓ JSON出力: boundary_analysis_results.json")
        except Exception as e:
            print(f"✗ JSON出力エラー: {e}")
        
        print("\n" + "=" * 60)
        print("境界値分析完了！")
        print(f"結果: {output_dir}")
        print("=" * 60)
        
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 