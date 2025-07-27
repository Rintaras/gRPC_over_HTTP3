#!/bin/bash
# 最適化されたベンチマークスクリプト v2
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
    
    # Dockerコンテナ内でベンチマーク実行
    log_info "Dockerコンテナ内でベンチマーク実行中..."
    
    docker exec grpc-client bash -c "
        # タイムスタンプ付きディレクトリ作成
        NOW=\$(date +\"%Y%m%d_%H%M%S\")
        LOG_DIR=\"/logs/optimized_benchmark_\${NOW}\"
        mkdir -p \$LOG_DIR
        
        echo \"[INFO] ログディレクトリ: \$LOG_DIR\"
        
        SERVER_IP=\"172.30.0.2\"
        ROUTER_IP=\"172.30.0.254\"
        
        # テストケース（性能比較に最適化）
        TEST_CASES=(
            \"0 0\"      # 理想環境
            \"50 0\"     # 中程度遅延
            \"100 0\"    # 高遅延
            \"150 0\"    # 超高遅延
        )
        
        # ベンチマークパラメータ（最適化済み）
        REQUESTS=30000
        CONNECTIONS=50
        THREADS=10
        MAX_CONCURRENT=50
        REQUEST_DATA=\"最適化ベンチマーククライアントからのテスト - HTTP/2 vs HTTP/3 性能比較テスト用の現実的なデータペイロード\"
        
        # フェア比較パラメータ
        WARMUP_REQUESTS=10000
        MEASUREMENT_REQUESTS=20000
        CONNECTION_WARMUP_TIME=15
        CONNECTION_REUSE_ENABLED=true
        
        # システム安定化設定
        SYSTEM_STABILIZATION_TIME=20
        MEMORY_CLEANUP_ENABLED=true
        NETWORK_RESET_ENABLED=true
        
        # 派生パラメータの計算
        REQUESTS_PER_CONNECTION=\$((REQUESTS / CONNECTIONS))
        REMAINING_REQUESTS=\$((REQUESTS % CONNECTIONS))
        CONNECTIONS_PER_THREAD=\$((CONNECTIONS / THREADS))
        
        echo \"================================================\" > \$LOG_DIR/benchmark_summary.txt
        echo \"最適化ベンチマーク実行結果\" >> \$LOG_DIR/benchmark_summary.txt
        echo \"================================================\" >> \$LOG_DIR/benchmark_summary.txt
        echo \"実行時刻: \$(date)\" >> \$LOG_DIR/benchmark_summary.txt
        echo \"パラメータ:\" >> \$LOG_DIR/benchmark_summary.txt
        echo \"  総リクエスト数: \$REQUESTS\" >> \$LOG_DIR/benchmark_summary.txt
        echo \"  同時接続数: \$CONNECTIONS\" >> \$LOG_DIR/benchmark_summary.txt
        echo \"  並列スレッド数: \$THREADS\" >> \$LOG_DIR/benchmark_summary.txt
        echo \"  最大同時ストリーム数: \$MAX_CONCURRENT\" >> \$LOG_DIR/benchmark_summary.txt
        echo \"  システム安定化時間: \${SYSTEM_STABILIZATION_TIME}秒\" >> \$LOG_DIR/benchmark_summary.txt
        echo \"================================================\" >> \$LOG_DIR/benchmark_summary.txt
        
        # 各テストケースでベンチマーク実行
        for test_case in \"\${TEST_CASES[@]}\"; do
            read -r delay loss <<< \"\$test_case\"
            
            echo \"[INFO] テストケース: 遅延=\${delay}ms, 損失=\${loss}%\" >> \$LOG_DIR/benchmark_summary.txt
            
            # ネットワーク条件設定
            /scripts/netem_delay_loss_bandwidth.sh \$delay \$loss 0
            
            # システム安定化
            echo \"[INFO] システム安定化中... (\${SYSTEM_STABILIZATION_TIME}秒)\"
            sleep \$SYSTEM_STABILIZATION_TIME
            
            # HTTP/2 ベンチマーク
            echo \"[INFO] HTTP/2 ベンチマーク実行中...\"
            h2load -n \$REQUESTS -c \$CONNECTIONS -t \$THREADS -m \$MAX_CONCURRENT -w 5 -D 30 -T 30 http://\$SERVER_IP/echo > \$LOG_DIR/h2_\${delay}ms_\${loss}pct.log 2>&1
            
            # 測定間隔
            sleep 10
            
            # HTTP/3 ベンチマーク
            echo \"[INFO] HTTP/3 ベンチマーク実行中...\"
            h2load -n \$REQUESTS -c \$CONNECTIONS -t \$THREADS -m \$MAX_CONCURRENT -w 5 -D 30 -T 30 https://\$SERVER_IP/echo > \$LOG_DIR/h3_\${delay}ms_\${loss}pct.log 2>&1
            
            # 条件間隔
            sleep 15
        done
        
        echo \"[SUCCESS] ベンチマーク完了\"
    "
    
    # 結果ファイルをホストにコピー
    log_info "結果ファイルをホストにコピー中..."
    docker cp grpc-client:/logs/. "$LOG_DIR/"
    
    # 結果解析
    log_info "結果解析中..."
    python3 scripts/generate_performance_graphs.py "$LOG_DIR"
    
    # 終了時刻記録
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    log_success "最適化ベンチマーク完了"
    log_info "実行時間: ${DURATION}秒 ($(($DURATION / 60))分$(($DURATION % 60))秒)"
    log_info "結果保存先: $LOG_DIR"
}

# スクリプト実行
main "$@" 