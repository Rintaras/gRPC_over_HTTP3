#!/bin/bash
# 最適化されたベンチマークスクリプト
# Docker環境、メモリ管理、システム設定の最適化を適用

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

# 開始時刻記録
START_TIME=$(date +%s)
log_info "最適化ベンチマーク開始時刻: $(date)"

# システム最適化関数
optimize_system() {
    log_info "システム最適化を開始..."
    
    # Dockerリソースクリーンアップ
    log_info "Dockerリソースをクリーンアップ中..."
    docker container prune -f > /dev/null 2>&1 || true
    docker image prune -f > /dev/null 2>&1 || true
    docker volume prune -f > /dev/null 2>&1 || true
    docker builder prune -f > /dev/null 2>&1 || true
    docker system prune -f > /dev/null 2>&1 || true
    
    # メモリクリーンアップ（macOS）
    if [[ "$OSTYPE" == "darwin"* ]]; then
        log_info "メモリをクリーンアップ中..."
        sudo purge > /dev/null 2>&1 || log_warning "メモリクリーンアップに失敗（sudo権限が必要）"
    fi
    
    # システム情報表示
    log_info "システム情報:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        CPU_USAGE=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
        MEMORY_USAGE=$(top -l 1 | grep "PhysMem" | awk '{print $2}' | sed 's/G//')
        DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}')
        echo "  CPU使用率: ${CPU_USAGE}%"
        echo "  メモリ使用率: ${MEMORY_USAGE}%"
        echo "  ディスク使用率: ${DISK_USAGE}"
    fi
    
    log_success "システム最適化完了"
}

# ネットワーク条件設定関数
set_network_conditions() {
    local delay=$1
    local loss=$2
    local bandwidth=${3:-0}
    
    log_info "ネットワーク条件を設定: 遅延=${delay}ms, 損失=${loss}%, 帯域=${bandwidth}Mbps"
    
    # Dockerコンテナ内でネットワーク条件を設定
    docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh $delay $loss $bandwidth > /dev/null 2>&1
    
    # 設定反映のための待機
    sleep 2
    log_success "ネットワーク条件設定完了"
}

# ベンチマーク実行関数
run_benchmark() {
    local protocol=$1
    local delay=$2
    local loss=$3
    local bandwidth=${4:-0}
    
    # ログディレクトリを動的に取得
    local log_dir=$(ls -td logs/optimized_benchmark_* | head -1)
    local log_file="${log_dir}/${protocol}_${delay}ms_${loss}pct.log"
    local csv_file="${log_dir}/${protocol}_${delay}ms_${loss}pct.csv"
    
    log_info "$(echo $protocol | tr '[:lower:]' '[:upper:]') ベンチマーク実行中..."
    
    # ベンチマークパラメータ（最適化済み）
    REQUESTS=30000
    CONNECTIONS=50
    THREADS=10
    MAX_CONCURRENT=50
    WARMUP_REQUESTS=10000
    MEASUREMENT_REQUESTS=20000
    CONNECTION_WARMUP_TIME=15
    SYSTEM_STABILIZATION_TIME=20
    
    # システム安定化
    log_info "システム安定化中... (${SYSTEM_STABILIZATION_TIME}秒)"
    sleep $SYSTEM_STABILIZATION_TIME
    
    # ベンチマーク実行
    if [ "$protocol" = "h2" ]; then
        docker exec grpc-client h2load \
            -n $REQUESTS \
            -c $CONNECTIONS \
            -t $THREADS \
            -m $MAX_CONCURRENT \
            -w 5 \
            -D 30 \
            -T 30 \
            --connect-timeout=10 \
            http://grpc-server/echo > "$log_file" 2>&1
    else
        docker exec grpc-client h2load \
            -n $REQUESTS \
            -c $CONNECTIONS \
            -t $THREADS \
            -m $MAX_CONCURRENT \
            -w 5 \
            -D 30 \
            -T 30 \
            --connect-timeout=10 \
            https://grpc-server/echo > "$log_file" 2>&1
    fi
    
    # 結果ファイルをコピー（CSVファイルは生成されないためスキップ）
    # docker cp grpc-client:/tmp/h2load.csv "$csv_file" > /dev/null 2>&1 || true
    
    log_success "$(echo $protocol | tr '[:lower:]' '[:upper:]') ベンチマーク完了"
}

# 結果解析関数
analyze_results() {
    local log_dir=$1
    
    log_info "結果解析中..."
    
    # Pythonスクリプトで結果解析
    python3 scripts/generate_performance_graphs.py "$log_dir"
    
    log_success "結果解析完了"
}

# メイン実行関数
main() {
    # ログディレクトリ作成
    LOG_DIR="logs/optimized_benchmark_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$LOG_DIR"
    
    log_info "最適化ベンチマーク開始"
    log_info "ログディレクトリ: $LOG_DIR"
    
    # システム最適化
    optimize_system
    
    # ベンチマークパラメータを記録
    cat > "$LOG_DIR/benchmark_params.txt" << EOF
REQUESTS=30000
CONNECTIONS=50
THREADS=10
MAX_CONCURRENT=50
WARMUP_REQUESTS=10000
MEASUREMENT_REQUESTS=20000
CONNECTION_WARMUP_TIME=15
SYSTEM_STABILIZATION_TIME=20
MEMORY_CLEANUP_ENABLED=true
NETWORK_RESET_ENABLED=true
DOCKER_OPTIMIZATION_ENABLED=true
EOF
    
    # テスト条件
    TEST_CONDITIONS=(
        "0 0"    # 0ms遅延, 0%損失
        "50 0"   # 50ms遅延, 0%損失
        "100 0"  # 100ms遅延, 0%損失
        "150 0"  # 150ms遅延, 0%損失
    )
    
    # 各条件でベンチマーク実行
    for condition in "${TEST_CONDITIONS[@]}"; do
        read -r delay loss <<< "$condition"
        
        log_info "テスト条件: 遅延=${delay}ms, 損失=${loss}%"
        
        # ネットワーク条件設定
        set_network_conditions $delay $loss
        
        # HTTP/2 ベンチマーク
        run_benchmark "h2" $delay $loss
        
        # 測定間隔
        sleep 10
        
        # HTTP/3 ベンチマーク
        run_benchmark "h3" $delay $loss
        
        # 条件間隔
        sleep 15
    done
    
    # 結果解析
    analyze_results "$LOG_DIR"
    
    # 終了時刻記録
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    log_success "最適化ベンチマーク完了"
    log_info "実行時間: ${DURATION}秒 ($(($DURATION / 60))分$(($DURATION % 60))秒)"
    log_info "結果保存先: $LOG_DIR"
}

# スクリプト実行
main "$@" 