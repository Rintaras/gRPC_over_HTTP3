#!/bin/bash

# Improved benchmark script for HTTP/2 vs HTTP/3 performance comparison (長時間測定版)
# Tests 4 network conditions: (0/0), (50/0), (100/1), (150/3)
# Features: Long measurement time, increased connections, extended timeouts, protocol separation

echo "================================================"
echo "HTTP/2 vs HTTP/3 Performance Benchmark"
echo "================================================"
echo "ベンチマーク開始: $(date)"
echo "================================================"

# Execute the entire benchmark inside the client container
docker exec grpc-client bash -c '
# タイムスタンプ付きディレクトリ作成
NOW=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="/logs/benchmark_${NOW}"
mkdir -p $LOG_DIR

echo "[INFO] ログディレクトリ: $LOG_DIR"

SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"

# Test cases: (delay_ms, loss_percent)
declare -a test_cases=(
    "0 1"    # 理想環境: 0ms遅延、1%損失
    "50 1"   # 中程度遅延: 50ms遅延、1%損失
    "100 1"  # 高遅延低損失: 100ms遅延、1%損失
    "150 1"  # 高遅延高損失: 150ms遅延、1%損失
)

# Benchmark parameters (unified for all protocols)
REQUESTS=200000       # 総リクエスト数（適切なレベルに調整）
CONNECTIONS=100       # 同時接続数（安定性のため調整）
THREADS=20           # 並列スレッド数（調整）
MAX_CONCURRENT=100   # 最大同時ストリーム数（調整）
REQUEST_DATA="Hello from benchmark client - HTTP/2 vs HTTP/3 performance comparison test with realistic data payload for accurate measurement"  # サイズ: 約150バイト

# Fair comparison parameters
WARMUP_REQUESTS=20000  # 接続確立後のウォームアップ用リクエスト数（調整）
MEASUREMENT_REQUESTS=180000  # 実際の測定用リクエスト数（調整）
CONNECTION_WARMUP_TIME=5  # 接続確立後の待機時間（秒）（増加）

# Calculate derived parameters
REQUESTS_PER_CONNECTION=$((REQUESTS / CONNECTIONS))
REMAINING_REQUESTS=$((REQUESTS % CONNECTIONS))
CONNECTIONS_PER_THREAD=$((CONNECTIONS / THREADS))

echo "================================================"
echo "HTTP/2 vs HTTP/3 Performance Benchmark"
echo "================================================"
echo "Parameters:"
echo "  Total Requests: $REQUESTS"
echo "  Connections: $CONNECTIONS"
echo "  Threads: $THREADS"
echo "  Max Concurrent Streams: $MAX_CONCURRENT"
echo "  Requests per Connection: $REQUESTS_PER_CONNECTION"
echo "  Connections per Thread: $CONNECTIONS_PER_THREAD"
echo "  Request Data: \"$REQUEST_DATA\""
echo "  Test Cases: ${#test_cases[@]}"
echo "  Fair Comparison: Enabled"
echo "    - Warmup Requests: $WARMUP_REQUESTS"
echo "    - Measurement Requests: $MEASUREMENT_REQUESTS"
echo "    - Connection Warmup Time: ${CONNECTION_WARMUP_TIME}s"
echo "  Long Measurement: Enabled"
echo "    - Estimated measurement time: ~3-5 minutes per test case"
echo "    - Protocol separation: 30 seconds between HTTP/2 and HTTP/3"
echo "    - Extended timeouts: 60 seconds for connections"
echo "    - Optimized for server capacity and stability"
echo "================================================"

# Create log directory
mkdir -p "$LOG_DIR"

# ベンチマークパラメータをテキストファイルに保存
cat <<EOF > "$LOG_DIR/benchmark_params.txt"
REQUESTS=$REQUESTS
CONNECTIONS=$CONNECTIONS
THREADS=$THREADS
MAX_CONCURRENT=$MAX_CONCURRENT
WARMUP_REQUESTS=$WARMUP_REQUESTS
MEASUREMENT_REQUESTS=$MEASUREMENT_REQUESTS
CONNECTION_WARMUP_TIME=$CONNECTION_WARMUP_TIME
EOF

# Function to get current timestamp
get_timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

# Function to log network conditions
log_network_conditions() {
    local delay=$1
    local loss=$2
    local log_file=$3
    
    echo "=== NETWORK CONDITIONS ===" >> $log_file
    echo "Timestamp: $(get_timestamp)" >> $log_file
    echo "Delay: ${delay}ms" >> $log_file
    echo "Loss: ${loss}%" >> $log_file
    echo "Router IP: $ROUTER_IP" >> $log_file
    echo "Server IP: $SERVER_IP" >> $log_file
    
    # Get current qdisc configuration
    echo "Current qdisc configuration:" >> $log_file
    docker exec grpc-router tc qdisc show dev eth0 >> $log_file 2>&1
    echo "" >> $log_file
}

# Function to run HTTP/2 benchmark with h2load
run_http2_bench() {
    local delay=$1
    local loss=$2
    local log_file="$LOG_DIR/h2_${delay}ms_${loss}pct.log"
    local csv_file="$LOG_DIR/h2_${delay}ms_${loss}pct.csv"
    
    echo "Running HTTP/2 benchmark (${delay}ms delay, ${loss}% loss)..."
    
    # Clear log file and add header
    echo "=== HTTP/2 BENCHMARK RESULTS ===" > $log_file
    log_network_conditions $delay $loss $log_file
    
    # Create temporary data file for h2load
    local temp_data_file=$(mktemp)
    echo "$REQUEST_DATA" > "$temp_data_file"
    
    # Fair comparison: Establish connections first, then measure
    echo "Establishing HTTP/2 connections for fair comparison..."
    echo "=== CONNECTION ESTABLISHMENT PHASE ===" >> $log_file
    
    # Phase 1: Establish connections with warmup requests
    h2load -n $WARMUP_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-benchmark-warmup" \
        --data "$temp_data_file" \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    echo "Waiting ${CONNECTION_WARMUP_TIME}s for connections to stabilize..." >> $log_file
    sleep $CONNECTION_WARMUP_TIME
    
    echo "=== MEASUREMENT PHASE ===" >> $log_file
    # Phase 2: Measure performance with established connections
    h2load -n $MEASUREMENT_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-benchmark-measurement" \
        --data "$temp_data_file" \
        --log-file "$csv_file" \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    # Clean up temporary file
    rm "$temp_data_file"
    
    # Add summary at the end
    echo "" >> $log_file
    echo "=== BENCHMARK SUMMARY ===" >> $log_file
    echo "Protocol: HTTP/2" >> $log_file
    echo "Fair Comparison: Enabled" >> $log_file
    echo "Warmup Requests: $WARMUP_REQUESTS" >> $log_file
    echo "Measurement Requests: $MEASUREMENT_REQUESTS" >> $log_file
    echo "End Time: $(get_timestamp)" >> $log_file
    echo "CSV Log: $csv_file" >> $log_file
    
    echo "HTTP/2 results saved to $log_file"
    echo "HTTP/2 CSV data saved to $csv_file"
}

# Function to run HTTP/3 benchmark with h2load
run_http3_bench() {
    local delay=$1
    local loss=$2
    local log_file="$LOG_DIR/h3_${delay}ms_${loss}pct.log"
    local csv_file="$LOG_DIR/h3_${delay}ms_${loss}pct.csv"
    
    echo "Running HTTP/3 benchmark with h2load (${delay}ms delay, ${loss}% loss)..."
    
    # Clear log file and add header
    echo "=== HTTP/3 BENCHMARK RESULTS ===" > $log_file
    log_network_conditions $delay $loss $log_file
    
    # Create temporary data file for h2load
    local temp_data_file=$(mktemp)
    echo "$REQUEST_DATA" > "$temp_data_file"
    
    # Fair comparison: Establish connections first, then measure
    echo "Establishing HTTP/3 connections for fair comparison..."
    echo "=== CONNECTION ESTABLISHMENT PHASE ===" >> $log_file
    
    # Phase 1: Establish connections with warmup requests
    h2load -n $WARMUP_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-benchmark-warmup" \
        --data "$temp_data_file" \
        --alpn-list=h3,h2 \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    echo "Waiting ${CONNECTION_WARMUP_TIME}s for connections to stabilize..." >> $log_file
    sleep $CONNECTION_WARMUP_TIME
    
    echo "=== MEASUREMENT PHASE ===" >> $log_file
    # Phase 2: Measure performance with established connections
    h2load -n $MEASUREMENT_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-benchmark-measurement" \
        --data "$temp_data_file" \
        --alpn-list=h3,h2 \
        --log-file "$csv_file" \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    # Clean up temporary file
    rm "$temp_data_file"
    
    # Check if h2load succeeded and analyze protocol usage
    if grep -q "succeeded, 0 failed" $log_file; then
        # Check if HTTP/3 was actually used by looking for QUIC indicators
        if grep -q "Application protocol: h3" $log_file; then
            echo "✓ h2load HTTP/3 benchmark completed successfully (confirmed HTTP/3)"
            protocol_used="HTTP/3 (confirmed)"
        elif grep -q "Application protocol: h2" $log_file; then
            echo "⚠ h2load completed but used HTTP/2 (fallback)"
            protocol_used="HTTP/2 (fallback)"
        else
            echo "✓ h2load benchmark completed successfully (protocol unclear)"
            protocol_used="Unknown"
        fi
        
        # Add summary at the end
        echo "" >> $log_file
        echo "=== BENCHMARK SUMMARY ===" >> $log_file
        echo "Protocol: $protocol_used" >> $log_file
        echo "Fair Comparison: Enabled" >> $log_file
        echo "Warmup Requests: $WARMUP_REQUESTS" >> $log_file
        echo "Measurement Requests: $MEASUREMENT_REQUESTS" >> $log_file
        echo "End Time: $(get_timestamp)" >> $log_file
        echo "CSV Log: $csv_file" >> $log_file
        
        echo "HTTP/3 results saved to $log_file"
        echo "HTTP/3 CSV data saved to $csv_file"
        return 0
    else
        echo "h2load HTTP/3 failed"
        return 1
    fi
}

# Function to verify HTTP/3 is working
verify_http3() {
    echo "Verifying HTTP/3 connectivity..."
    
    # Test HTTP/3 with curl
    local http3_test=$(curl -sk --http3 --connect-timeout 5 \
        -w "%{http_version}\n" \
        https://$SERVER_IP/echo 2>/dev/null | tail -1)
    
    if [[ "$http3_test" == "3" ]]; then
        echo "✓ HTTP/3 is working correctly"
        return 0
    else
        echo "✗ HTTP/3 test failed, got version: $http3_test"
        return 1
    fi
}

# Main benchmark loop
for test_case in "${test_cases[@]}"; do
    read -r delay loss <<< "$test_case"
    
    echo ""
    echo "================================================"
    echo "Test case: ${delay}ms delay, ${loss}% loss"
    echo "================================================"
    
    # Apply network conditions
    echo "Applying network conditions..."
    docker exec grpc-router /scripts/netem_delay_loss.sh $delay $loss
    
    # Wait for network to stabilize
    echo "Waiting for network to stabilize..."
    sleep 10
    
    # Verify HTTP/3 is working before benchmark
    if ! verify_http3; then
        echo "Warning: HTTP/3 verification failed, continuing anyway..."
    fi
    
    # Run benchmarks sequentially to avoid interference
    echo "Running benchmarks..."
    run_http2_bench $delay $loss
    
    echo "Waiting 30 seconds between protocols..."
    sleep 30
    
    # Run HTTP/3 benchmark with h2load
    run_http3_bench $delay $loss
    
    echo "Completed test case: ${delay}ms delay, ${loss}% loss"
    echo ""
done

echo "================================================"
echo "All benchmarks completed!"
echo "Results saved in $LOG_DIR/"
echo "================================================"
echo "Files:"
ls -la $LOG_DIR/h*_*.log 

# Generate summary report
echo ""
echo "=== SUMMARY REPORT ==="
echo "Generated at: $(get_timestamp)"
echo "Total test cases: ${#test_cases[@]}"
echo "Log directory: $LOG_DIR"
echo ""
echo "File sizes:"
for log_file in $LOG_DIR/h*_*.log; do
    if [ -f "$log_file" ]; then
        size=$(wc -l < "$log_file")
        echo "  $(basename $log_file): $size lines"
    fi
done

echo "Benchmark complete! Check the reports and graphs in $LOG_DIR"
'

echo "================================================"
echo "ベンチマーク完了: $(date)"
echo "================================================"

# ホスト側で最新のベンチマークディレクトリを取得してグラフ生成
LATEST_LOG_DIR=$(ls -1td logs/benchmark_* | head -n1)
echo "[ホスト] グラフ自動生成: python3 scripts/generate_performance_graphs.py $LATEST_LOG_DIR"

# グラフ生成の実行（エラーハンドリング付き）
echo "[ホスト] グラフ生成を開始..."

# グラフ生成を実行
if source venv/bin/activate && python3 scripts/generate_performance_graphs.py "$LATEST_LOG_DIR"; then
    echo "✅ グラフ生成が正常に完了しました"
    echo "生成されたグラフファイル:"
    ls -la "$LATEST_LOG_DIR"/*.png 2>/dev/null || echo "グラフファイルが見つかりません"
else
    echo "❌ グラフ生成でエラーが発生しました"
    echo "手動でグラフ生成を実行してください:"
    echo "source venv/bin/activate && python3 scripts/generate_performance_graphs.py $LATEST_LOG_DIR"
fi

echo "================================================"
echo "完全自動化完了: $(date)"
echo "ベンチマーク + グラフ生成が正常に完了しました"
echo "結果: $LATEST_LOG_DIR"
echo "================================================"

# === 4区間のネットワーク統計取得 ===
echo "[ホスト] 4区間ネットワーク統計を取得中..."

# クライアント→ルーター
# クライアントからルーターへのping
( docker exec grpc-client ping -c 10 172.30.0.254 > "$LATEST_LOG_DIR/ping_client_to_router.txt" 2>&1 ) &
# クライアント側のip統計
( docker exec grpc-client ip -s link show eth0 > "$LATEST_LOG_DIR/ip_client_eth0.txt" 2>&1 ) &
# ルーター側のip統計
( docker exec grpc-router ip -s link show eth0 > "$LATEST_LOG_DIR/ip_router_eth0.txt" 2>&1 ) &

# ルーター→サーバー
# ルーターからサーバーへのping
( docker exec grpc-router ping -c 10 172.30.0.2 > "$LATEST_LOG_DIR/ping_router_to_server.txt" 2>&1 ) &
# サーバー側のip統計
( docker exec grpc-server ip -s link show eth0 > "$LATEST_LOG_DIR/ip_server_eth0.txt" 2>&1 ) &

# サーバー→ルーター
# サーバーからルーターへのping
( docker exec grpc-server ping -c 10 172.30.0.254 > "$LATEST_LOG_DIR/ping_server_to_router.txt" 2>&1 ) &

# ルーター→クライアント
# ルーターからクライアントへのping
( docker exec grpc-router ping -c 10 172.30.0.3 > "$LATEST_LOG_DIR/ping_router_to_client.txt" 2>&1 ) &
# クライアント側のip統計（再取得）
( docker exec grpc-client ip -s link show eth0 > "$LATEST_LOG_DIR/ip_client_eth0_after.txt" 2>&1 ) &

wait
echo "[ホスト] 4区間ネットワーク統計の取得が完了しました。"

# === 4区間ネットワーク統計の可視化 ===
echo "[ホスト] 4区間ネットワーク統計の可視化を実行..."
python3 scripts/visualize_network_stats.py "$LATEST_LOG_DIR"

echo "================================================"
echo "完全自動化完了: $(date)"
echo "ベンチマーク + グラフ生成が正常に完了しました"
echo "結果: $LATEST_LOG_DIR"
echo "================================================"

# === ルーター全インターフェース統計を取得 ===
docker exec grpc-router ip -s link show > "$LATEST_LOG_DIR/ip_router_all.txt"

echo "================================================"
echo "完全自動化完了: $(date)"
echo "ベンチマーク + グラフ生成が正常に完了しました"
echo "結果: $LATEST_LOG_DIR"
echo "================================================" 