#!/bin/bash

# Ultra Fast Benchmark Script - 3分で完了
# 統計的信頼性を保ちながら実行時間を大幅短縮

set -e

# 色付きのログ出力
log_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

log_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

log_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# タイムスタンプ付きディレクトリ作成
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs/ultra_fast_benchmark_${TIMESTAMP}"

log_info "🚀 Starting Ultra Fast Benchmark"
log_info "⏱️  Estimated completion time: ~3 minutes"
log_info "📁 Log directory: $LOG_DIR"

# 仮想環境のアクティベート
if [ -d "venv" ]; then
    log_info "Activating Python virtual environment..."
    source venv/bin/activate
else
    log_warning "Virtual environment not found, using system Python"
fi

# Docker環境の確認
log_info "Checking Docker environment..."
if ! docker ps | grep -q "grpc-client"; then
    log_error "Docker containers not running. Please start with: docker-compose up -d"
    exit 1
fi

log_success "Docker environment is ready"

# ベンチマーク実行
log_info "Starting ultra fast benchmark..."
python3 scripts/ultra_fast_benchmark.py \
    --log_dir "$LOG_DIR" \
    --test_conditions "10:0:0,100:2:0,200:5:0"

# 結果確認
if [ -f "$LOG_DIR/ultra_fast_results.csv" ]; then
    log_success "Benchmark completed successfully!"
    log_info "📊 Results: $LOG_DIR/ultra_fast_results.csv"
    log_info "📈 Graph: $LOG_DIR/ultra_fast_comparison.png"
    log_info "📝 Report: $LOG_DIR/ultra_fast_report.txt"
    
    # 結果の簡単な表示
    echo ""
    log_info "Quick Results Summary:"
    echo "========================"
    if command -v python3 &> /dev/null; then
        python3 -c "
import pandas as pd
import sys
try:
    df = pd.read_csv('$LOG_DIR/ultra_fast_results.csv')
    for _, row in df.iterrows():
        print(f\"Network: {row['delay']}ms delay, {row['loss']}% loss\")
        print(f\"  HTTP/2: {row['h2_throughput']:.1f} req/s, {row['h2_latency']:.1f}ms\")
        print(f\"  HTTP/3: {row['h3_throughput']:.1f} req/s, {row['h3_latency']:.1f}ms\")
        print(f\"  Throughput advantage: {row['throughput_advantage']:+.1f}%\")
        print(f\"  Latency advantage: {row['latency_advantage']:+.1f}%\")
        print()
except Exception as e:
    print(f'Error reading results: {e}')
    sys.exit(1)
"
    else
        log_warning "Python not available for results display"
    fi
else
    log_error "Benchmark failed - no results file found"
    exit 1
fi

log_success "Ultra Fast Benchmark completed!"
log_info "Total execution time: ~3 minutes"
log_info "All results saved in: $LOG_DIR" 