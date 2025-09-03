#!/bin/bash

# HTTP/2 vs HTTP/3 Performance Benchmark Script
# Tests 4 network conditions with 3% packet loss and varying delays

echo "================================================"
echo "HTTP/2 vs HTTP/3 Performance Benchmark"
echo "================================================"
echo "ベンチマーク開始: $(date)"
echo "================================================"

# Execute the entire benchmark inside the client container
docker exec grpc-client bash -c "
# タイムスタンプ付きディレクトリ作成
NOW=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="/logs/benchmark_${NOW}"
mkdir -p $LOG_DIR

echo "[INFO] ログディレクトリ: $LOG_DIR"

SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"

# Test cases with consistent 3% packet loss and varying delays
TEST_CASES=(
    "0 3"      # 0ms delay, 3% loss
    "75 3"     # 75ms delay, 3% loss
    "150 3"    # 150ms delay, 3% loss
    "225 3"    # 225ms delay, 3% loss
)

# Benchmark parameters
REQUESTS=50000        # 総リクエスト数
CONNECTIONS=100       # 同時接続数
THREADS=20           # 並列スレッド数
MAX_CONCURRENT=100   # 最大同時ストリーム数
REQUEST_DATA="Hello from benchmark client - HTTP/2 vs HTTP/3 performance comparison test"

# Fair comparison parameters
WARMUP_REQUESTS=20000   # ウォームアップ用リクエスト数
MEASUREMENT_REQUESTS=30000  # 測定用リクエスト数
CONNECTION_WARMUP_TIME=10   # 接続安定化時間

# System stabilization settings
SYSTEM_STABILIZATION_TIME=30  # システム安定化時間

echo "================================================"
echo "Benchmark Parameters:"
echo "  Total Requests: $REQUESTS"
echo "  Connections: $CONNECTIONS"
echo "  Threads: $THREADS"
echo "  Max Concurrent Streams: $MAX_CONCURRENT"
echo "  Test Cases: ${#TEST_CASES[@]}"
echo "  Fair Comparison: Enabled"
echo "    - Warmup Requests: $WARMUP_REQUESTS"
echo "    - Measurement Requests: $MEASUREMENT_REQUESTS"
echo "    - Connection Warmup Time: ${CONNECTION_WARMUP_TIME}s"
echo "================================================"

# Create log directory
mkdir -p "$LOG_DIR"

# ベンチマークパラメータをテキストファイルに保存
cat > "$LOG_DIR/benchmark_params.txt" << EOF
REQUESTS=$REQUESTS
CONNECTIONS=$CONNECTIONS
THREADS=$THREADS
MAX_CONCURRENT=$MAX_CONCURRENT
WARMUP_REQUESTS=$WARMUP_REQUESTS
MEASUREMENT_REQUESTS=$MEASUREMENT_REQUESTS
CONNECTION_WARMUP_TIME=$CONNECTION_WARMUP_TIME
EOF

# Function to stabilize system before benchmark
stabilize_system() {
    local delay=$1
    local loss=$2
    
    echo "=== SYSTEM STABILIZATION ==="
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Delay: ${delay}ms, Loss: ${loss}%"
    
    # Wait for system stabilization
    echo "Waiting ${SYSTEM_STABILIZATION_TIME}s for system stabilization..."
    sleep $SYSTEM_STABILIZATION_TIME
    
    # Memory cleanup
    echo "Performing memory cleanup..."
    docker exec grpc-client sync 2>/dev/null || true
    docker exec grpc-router sync 2>/dev/null || true
    docker exec grpc-server sync 2>/dev/null || true
    
    # Network reset
    echo "Resetting network connections..."
    docker exec grpc-client ip route flush cache 2>/dev/null || true
    docker exec grpc-router ip route flush cache 2>/dev/null || true
    docker exec grpc-server ip route flush cache 2>/dev/null || true
    
    echo "System stabilization completed"
    echo ""
}

# Function to log network conditions
log_network_conditions() {
    local delay=$1
    local loss=$2
    local log_file=$3
    
    echo "=== NETWORK CONDITIONS ===" >> $log_file
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')" >> $log_file
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
    echo "End Time: $(date '+%Y-%m-%d %H:%M:%S')" >> $log_file
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
        echo "End Time: $(date '+%Y-%m-%d %H:%M:%S')" >> $log_file
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
    local http3_test=$(docker exec grpc-client curl -k --http3 https://$SERVER_IP/echo 2>/dev/null | grep -c "HTTP/3")
    
    if [ "$http3_test" -gt 0 ]; then
        echo "✓ HTTP/3 is working correctly"
        return 0
    else
        echo "✗ HTTP/3 is not working"
        return 1
    fi
}

# Main benchmark loop
for test_case in "${TEST_CASES[@]}"; do
    read -r delay loss <<< "$test_case"
    
    echo ""
    echo "================================================"
    echo "Test case: ${delay}ms delay, ${loss}% loss"
    echo "================================================"
    
    # Apply network conditions
    echo "Applying network conditions..."
    docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh $delay $loss
    
    # System stabilization for consistent results
    stabilize_system $delay $loss
    
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
echo "Generated at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Total test cases: ${#TEST_CASES[@]}"
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

# Copy CSV files from Docker container to host
echo "Copying CSV files from Docker container..."
docker cp grpc-client:/logs/h2_0ms_3pct.csv "$LOG_DIR/" 2>/dev/null || echo "h2_0ms_3pct.csv not found"
docker cp grpc-client:/logs/h2_75ms_3pct.csv "$LOG_DIR/" 2>/dev/null || echo "h2_75ms_3pct.csv not found"
docker cp grpc-client:/logs/h2_150ms_3pct.csv "$LOG_DIR/" 2>/dev/null || echo "h2_150ms_3pct.csv not found"
docker cp grpc-client:/logs/h2_225ms_3pct.csv "$LOG_DIR/" 2>/dev/null || echo "h2_225ms_3pct.csv not found"
docker cp grpc-client:/logs/h3_0ms_3pct.csv "$LOG_DIR/" 2>/dev/null || echo "h3_0ms_3pct.csv not found"
docker cp grpc-client:/logs/h3_75ms_3pct.csv "$LOG_DIR/" 2>/dev/null || echo "h3_75ms_3pct.csv not found"
docker cp grpc-client:/logs/h3_150ms_3pct.csv "$LOG_DIR/" 2>/dev/null || echo "h3_150ms_3pct.csv not found"
docker cp grpc-client:/logs/h3_225ms_3pct.csv "$LOG_DIR/" 2>/dev/null || echo "h3_225ms_3pct.csv not found"

echo "CSV files copied successfully"
"

echo "================================================"
echo "ベンチマーク完了: $(date)"
echo "================================================"

# ホスト側で最新のベンチマークディレクトリを取得してグラフ生成
LATEST_LOG_DIR=$(ls -1td logs/benchmark_* | head -n1)
echo "[ホスト] グラフ自動生成: python3 scripts/simple_graph_generator.py $LATEST_LOG_DIR"

# グラフ生成の実行（エラーハンドリング付き）
echo "[ホスト] グラフ生成を開始..."

# グラフ生成を実行
if source venv/bin/activate && python3 scripts/simple_graph_generator.py "$LATEST_LOG_DIR"; then
    echo "✅ グラフ生成が正常に完了しました"
    echo "生成されたグラフファイル:"
    ls -la "$LATEST_LOG_DIR"/*.png 2>/dev/null || echo "グラフファイルが見つかりません"
else
    echo "❌ グラフ生成でエラーが発生しました"
    echo "手動でグラフ生成を実行してください:"
    echo "source venv/bin/activate && python3 scripts/simple_graph_generator.py $LATEST_LOG_DIR"
fi

echo "================================================"
echo "完全自動化完了: $(date)"
echo "ベンチマーク + グラフ生成が正常に完了しました"
echo "結果: $LATEST_LOG_DIR"
echo "================================================"

# 基本的なネットワーク統計を取得
echo "[ホスト] 基本的なネットワーク統計を取得中..."

# クライアント→ルーター
docker exec grpc-client ping -c 5 172.30.0.254 > "$LATEST_LOG_DIR/ping_client_to_router.txt" 2>&1
docker exec grpc-client ip -s link show eth0 > "$LATEST_LOG_DIR/ip_client_eth0.txt" 2>&1

# ルーター→サーバー
docker exec grpc-router ping -c 5 172.30.0.2 > "$LATEST_LOG_DIR/ping_router_to_server.txt" 2>&1
docker exec grpc-server ip -s link show eth0 > "$LATEST_LOG_DIR/ip_server_eth0.txt" 2>&1

echo "[ホスト] ネットワーク統計の取得が完了しました。"
echo "================================================"
echo "ベンチマーク完了: $(date)"
echo "結果: $LATEST_LOG_DIR"
echo "================================================" 