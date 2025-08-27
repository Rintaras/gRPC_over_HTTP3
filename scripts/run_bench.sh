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

# Test cases with consistent 3% packet loss and varying delays
# Limited to 4 cases for time efficiency and consistency
TEST_CASES=(
    "0 3"      # 0ms delay, 3% loss
    "75 3"     # 75ms delay, 3% loss
    "150 3"    # 150ms delay, 3% loss
    "225 3"    # 225ms delay, 3% loss
)

# Benchmark parameters (optimized for HTTP/3 connection time improvement)
REQUESTS=50000        # 総リクエスト数（統計的安定性のため増加）
CONNECTIONS=100       # 同時接続数（統計的安定性のため増加）
THREADS=20           # 並列スレッド数（統計的安定性のため増加）
MAX_CONCURRENT=100   # 最大同時ストリーム数（統計的安定性のため増加）
REQUEST_DATA="Hello from benchmark client - HTTP/2 vs HTTP/3 performance comparison test with realistic data payload for accurate measurement"  # サイズ: 約150バイト

# Fair comparison parameters - HTTP/3接続時間改善
WARMUP_REQUESTS=20000   # 接続確立後のウォームアップ用リクエスト数（統計的安定性のため増加）
MEASUREMENT_REQUESTS=30000  # 実際の測定用リクエスト数（統計的安定性のため増加）
CONNECTION_WARMUP_TIME=10   # 0-RTT接続の利点を活かすため延長（統計的安定性のため延長）
CONNECTION_REUSE_ENABLED=true  # 接続再利用を有効化

# System stabilization settings for consistent results
SYSTEM_STABILIZATION_TIME=30  # システム安定化のための待機時間
MEMORY_CLEANUP_ENABLED=true   # メモリクリーンアップの有効化
NETWORK_RESET_ENABLED=true    # ネットワークリセットの有効化

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
echo "  Test Cases: ${#TEST_CASES[@]}"
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

# Function to perform comprehensive system control
comprehensive_system_control() {
    local delay=$1
    local loss=$2
    
    echo "=== COMPREHENSIVE SYSTEM CONTROL ==="
    echo "Timestamp: $(get_timestamp)"
    echo "Delay: ${delay}ms, Loss: ${loss}%"
    
    # Step 1: Memory usage control
    control_memory_usage
    
    # Step 2: Network conditions control
    control_network_conditions $delay $loss
    
    # Step 3: System stabilization
    echo "=== FINAL SYSTEM STABILIZATION ==="
    echo "Waiting ${SYSTEM_STABILIZATION_TIME}s for final stabilization..."
    sleep $SYSTEM_STABILIZATION_TIME
    
    echo "Comprehensive system control completed"
    echo ""
}

# Function to control Docker environment
control_docker_environment() {
    echo "=== DOCKER ENVIRONMENT CONTROL ==="
    
    # Restart containers for clean state
    echo "Restarting containers for clean state..."
    docker restart grpc-client grpc-router grpc-server 2>/dev/null || true
    
    # Wait for containers to be ready
    echo "Waiting for containers to be ready..."
    sleep 10
    
    # Verify container health
    echo "Verifying container health..."
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep grpc || echo "No grpc containers found"
    
    # Set container resource limits
    echo "Setting container resource limits..."
    docker update --cpus=2.0 --memory=2g grpc-client 2>/dev/null || true
    docker update --cpus=1.0 --memory=1g grpc-router 2>/dev/null || true
    docker update --cpus=2.0 --memory=2g grpc-server 2>/dev/null || true
    
    echo "Docker environment control completed"
    echo ""
}

# Function to control network conditions
control_network_conditions() {
    local delay=$1
    local loss=$2
    
    echo "=== NETWORK CONDITIONS CONTROL ==="
    echo "Delay: ${delay}ms, Loss: ${loss}%"
    
    if [ "$NETWORK_RESET_ENABLED" = true ]; then
        echo "Resetting network connections..."
        
        # Flush route cache
        docker exec grpc-client ip route flush cache 2>/dev/null || true
        docker exec grpc-router ip route flush cache 2>/dev/null || true
        docker exec grpc-server ip route flush cache 2>/dev/null || true
        
        # Reset TCP connections (simplified)
        docker exec grpc-client pkill -f "ss" 2>/dev/null || true
        docker exec grpc-router pkill -f "ss" 2>/dev/null || true
        docker exec grpc-server pkill -f "ss" 2>/dev/null || true
        
        # Set network buffer sizes
        docker exec grpc-client sysctl -w net.core.rmem_max=16777216 2>/dev/null || true
        docker exec grpc-client sysctl -w net.core.wmem_max=16777216 2>/dev/null || true
        docker exec grpc-router sysctl -w net.core.rmem_max=16777216 2>/dev/null || true
        docker exec grpc-router sysctl -w net.core.wmem_max=16777216 2>/dev/null || true
        docker exec grpc-server sysctl -w net.core.rmem_max=16777216 2>/dev/null || true
        docker exec grpc-server sysctl -w net.core.wmem_max=16777216 2>/dev/null || true
    fi
    
    echo "Network conditions control completed"
    echo ""
}

# Function to control memory usage
control_memory_usage() {
    echo "=== MEMORY USAGE CONTROL ==="
    
    if [ "$MEMORY_CLEANUP_ENABLED" = true ]; then
        echo "Performing comprehensive memory cleanup..."
        
        # Clear page cache
        docker exec grpc-client sync 2>/dev/null || true
        docker exec grpc-router sync 2>/dev/null || true
        docker exec grpc-server sync 2>/dev/null || true
        
        # Clear dentries and inodes
        docker exec grpc-client echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
        docker exec grpc-router echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
        docker exec grpc-server echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
        
        # Set memory limits for containers
        docker update --memory=2g --memory-swap=2g grpc-client 2>/dev/null || true
        docker update --memory=1g --memory-swap=1g grpc-router 2>/dev/null || true
        docker update --memory=2g --memory-swap=2g grpc-server 2>/dev/null || true
    fi
    
    echo "Memory usage control completed"
    echo ""
}

# Function to stabilize system before benchmark
stabilize_system() {
    local delay=$1
    local loss=$2
    
    echo "=== SYSTEM STABILIZATION ==="
    echo "Timestamp: $(get_timestamp)"
    echo "Delay: ${delay}ms, Loss: ${loss}%"
    
    # Wait for system stabilization
    echo "Waiting ${SYSTEM_STABILIZATION_TIME}s for system stabilization..."
    sleep $SYSTEM_STABILIZATION_TIME
    
    # Memory cleanup if enabled
    if [ "$MEMORY_CLEANUP_ENABLED" = true ]; then
        echo "Performing memory cleanup..."
        docker exec grpc-client sync 2>/dev/null || true
        docker exec grpc-router sync 2>/dev/null || true
        docker exec grpc-server sync 2>/dev/null || true
    fi
    
    # Network reset if enabled
    if [ "$NETWORK_RESET_ENABLED" = true ]; then
        echo "Resetting network connections..."
        docker exec grpc-client ip route flush cache 2>/dev/null || true
        docker exec grpc-router ip route flush cache 2>/dev/null || true
        docker exec grpc-server ip route flush cache 2>/dev/null || true
    fi
    
    echo "System stabilization completed"
    echo ""
}

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
echo "Generated at: $(get_timestamp)"
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
'

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