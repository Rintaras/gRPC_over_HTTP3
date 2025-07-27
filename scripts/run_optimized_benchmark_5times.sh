#!/bin/bash
# 最適化ベンチマークを5回連続実行するスクリプト

set -e

# 色付きログ関数
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

# 全体開始時刻記録
TOTAL_START_TIME=$(date +%s)
log_info "最適化ベンチマーク5回連続実行開始時刻: $(date)"

# 実行回数
TOTAL_RUNS=5

# 各実行の結果を記録
declare -a RUN_TIMES
declare -a RUN_DIRS

# メイン実行ループ
for run in $(seq 1 $TOTAL_RUNS); do
    log_info "=========================================="
    log_info "実行 $run/$TOTAL_RUNS 開始"
    log_info "=========================================="
    
    # 実行開始時刻
    RUN_START_TIME=$(date +%s)
    
    # 最適化ベンチマーク実行
    if ./scripts/optimized_benchmark_v2.sh; then
        # 実行成功
        RUN_END_TIME=$(date +%s)
        RUN_DURATION=$((RUN_END_TIME - RUN_START_TIME))
        RUN_TIMES[$((run-1))]=$RUN_DURATION
        
        # 最新のログディレクトリを記録
        LATEST_DIR=$(ls -td logs/optimized_benchmark_* 2>/dev/null | head -1 || echo "logs/optimized_benchmark_$(date +%Y%m%d_%H%M%S)")
        RUN_DIRS[$((run-1))]=$LATEST_DIR
        
        log_success "実行 $run/$TOTAL_RUNS 完了"
        log_info "実行時間: ${RUN_DURATION}秒 ($(($RUN_DURATION / 60))分$(($RUN_DURATION % 60))秒)"
        log_info "結果保存先: $LATEST_DIR"
        
    else
        # 実行失敗
        log_error "実行 $run/$TOTAL_RUNS 失敗"
        exit 1
    fi
    
    # 実行間隔（最後の実行以外）
    if [ $run -lt $TOTAL_RUNS ]; then
        log_info "次の実行まで5分待機中..."
        sleep 300
    fi
done

# 全体終了時刻記録
TOTAL_END_TIME=$(date +%s)
TOTAL_DURATION=$((TOTAL_END_TIME - TOTAL_START_TIME))

# 結果サマリー
log_success "=========================================="
log_success "最適化ベンチマーク5回連続実行完了"
log_success "=========================================="

log_info "全体実行時間: ${TOTAL_DURATION}秒 ($(($TOTAL_DURATION / 60))分$(($TOTAL_DURATION % 60))秒)"
log_info "平均実行時間: $(($TOTAL_DURATION / $TOTAL_RUNS))秒"

echo ""
log_info "各実行の詳細:"
for i in $(seq 0 $((TOTAL_RUNS-1))); do
    run_num=$((i+1))
    duration=${RUN_TIMES[$i]}
    dir=${RUN_DIRS[$i]}
    echo "  実行 $run_num: ${duration}秒 - $dir"
done

echo ""
log_info "結果ディレクトリ:"
for dir in "${RUN_DIRS[@]}"; do
    echo "  $dir"
done

# 統合分析の実行
log_info "5回実行結果の統合分析を開始..."
python3 scripts/analyze_5_experiments.py

log_success "5回連続実行と分析完了！" 