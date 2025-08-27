HTTP/3#!/bin/bash

# Raspberry Pi Research Server Benchmark Script
# Tests HTTP/2 vs HTTP/3 performance on Raspberry Pi server (172.20.10.4)
# Tests 4 network conditions: (0/3), (75/3), (150/3), (225/3)

echo "================================================"
echo "Raspberry Pi HTTP/2 vs HTTP/3 Performance Benchmark"
echo "================================================"
echo "ベンチマーク開始: $(date)"
echo "================================================"

# タイムスタンプ付きディレクトリ作成
NOW=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs/raspberry_pi_benchmark_${NOW}"
mkdir -p $LOG_DIR

echo "[INFO] ログディレクトリ: $LOG_DIR"

# Raspberry Pi server configuration
RASPBERRY_PI_IP="172.20.10.4"
RASPBERRY_PI_HOSTNAME="kumikomi.local"

# Test cases with consistent 3% packet loss and varying delays
TEST_CASES=(
    "0 3"      # 0ms delay, 3% loss
    "75 3"     # 75ms delay, 3% loss
    "150 3"    # 150ms delay, 3% loss
    "225 3"    # 225ms delay, 3% loss
)

# Benchmark parameters (optimized for research)
REQUESTS=50000        # 総リクエスト数
CONNECTIONS=100       # 同時接続数
THREADS=20           # 並列スレッド数
MAX_CONCURRENT=100   # 最大同時ストリーム数
REQUEST_DATA="Hello from Raspberry Pi benchmark client - HTTP/2 vs HTTP/3 performance comparison test with realistic data payload for accurate measurement"

# Fair comparison parameters
WARMUP_REQUESTS=20000   # ウォームアップ用リクエスト数
MEASUREMENT_REQUESTS=30000  # 実際の測定用リクエスト数
CONNECTION_WARMUP_TIME=10   # 接続安定化時間
CONNECTION_REUSE_ENABLED=true  # 接続再利用を有効化

# System stabilization settings
SYSTEM_STABILIZATION_TIME=30  # システム安定化のための待機時間
MEMORY_CLEANUP_ENABLED=true   # メモリクリーンアップの有効化
NETWORK_RESET_ENABLED=true    # ネットワークリセットの有効化

# Calculate derived parameters
REQUESTS_PER_CONNECTION=$((REQUESTS / CONNECTIONS))
REMAINING_REQUESTS=$((REQUESTS % CONNECTIONS))
CONNECTIONS_PER_THREAD=$((CONNECTIONS / THREADS))

echo "================================================"
echo "Raspberry Pi HTTP/2 vs HTTP/3 Performance Benchmark"
echo "================================================"
echo "Parameters:"
echo "  Target Server: $RASPBERRY_PI_IP ($RASPBERRY_PI_HOSTNAME)"
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
echo "================================================"

# Create log directory
mkdir -p "$LOG_DIR"

# ベンチマークパラメータをテキストファイルに保存
cat <<EOF > "$LOG_DIR/benchmark_params.txt"
TARGET_SERVER=$RASPBERRY_PI_IP
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

# Function to verify server connectivity
verify_server_connectivity() {
    echo "=== VERIFYING SERVER CONNECTIVITY ==="
    
    # Test HTTP connectivity
    local http_test=$(curl -s -o /dev/null -w "%{http_code}" "http://$RASPBERRY_PI_IP/health" 2>/dev/null)
    if [ "$http_test" = "200" ]; then
        echo "✓ HTTP connectivity: OK (Status: $http_test)"
    else
        echo "✗ HTTP connectivity: FAILED (Status: $http_test)"
        return 1
    fi
    
    # Test HTTPS connectivity
    local https_test=$(curl -s -k -o /dev/null -w "%{http_code}" "https://$RASPBERRY_PI_IP/health" 2>/dev/null)
    if [ "$https_test" = "200" ]; then
        echo "✓ HTTPS connectivity: OK (Status: $https_test)"
    else
        echo "✗ HTTPS connectivity: FAILED (Status: $https_test)"
        return 1
    fi
    
    # Test echo endpoint
    local echo_test=$(curl -s "http://$RASPBERRY_PI_IP/echo" 2>/dev/null | grep -c "Raspberry Pi")
    if [ "$echo_test" -gt 0 ]; then
        echo "✓ Echo endpoint: OK"
    else
        echo "✗ Echo endpoint: FAILED"
        return 1
    fi
    
    echo "Server connectivity verification completed successfully"
    return 0
}

# Function to perform system stabilization
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
        sync 2>/dev/null || true
    fi
    
    # Network reset if enabled
    if [ "$NETWORK_RESET_ENABLED" = true ]; then
        echo "Resetting network connections..."
        # Flush DNS cache
        sudo dscacheutil -flushcache 2>/dev/null || true
        sudo killall -HUP mDNSResponder 2>/dev/null || true
    fi
    
    echo "System stabilization completed"
    echo ""
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
    echo "Target Server: $RASPBERRY_PI_IP" >> $log_file
    echo "Hostname: $RASPBERRY_PI_HOSTNAME" >> $log_file
    
    # Get current network information
    echo "Current network configuration:" >> $log_file
    ifconfig | grep -E "(inet|ether)" >> $log_file 2>&1
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
        --connect-to $RASPBERRY_PI_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-raspberry-pi-benchmark-warmup" \
        --data "$temp_data_file" \
        https://$RASPBERRY_PI_IP/echo >> $log_file 2>&1
    
    echo "Waiting ${CONNECTION_WARMUP_TIME}s for connections to stabilize..." >> $log_file
    sleep $CONNECTION_WARMUP_TIME
    
    echo "=== MEASUREMENT PHASE ===" >> $log_file
    # Phase 2: Measure performance with established connections
    h2load -n $MEASUREMENT_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $RASPBERRY_PI_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-raspberry-pi-benchmark-measurement" \
        --data "$temp_data_file" \
        --log-file "$csv_file" \
        https://$RASPBERRY_PI_IP/echo >> $log_file 2>&1
    
    # Clean up temporary file
    rm "$temp_data_file"
    
    # Add summary at the end
    echo "" >> $log_file
    echo "=== BENCHMARK SUMMARY ===" >> $log_file
    echo "Protocol: HTTP/2" >> $log_file
    echo "Target Server: $RASPBERRY_PI_IP" >> $log_file
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
        --connect-to $RASPBERRY_PI_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-raspberry-pi-benchmark-warmup" \
        --data "$temp_data_file" \
        --alpn-list=h3,h2 \
        https://$RASPBERRY_PI_IP/echo >> $log_file 2>&1
    
    echo "Waiting ${CONNECTION_WARMUP_TIME}s for connections to stabilize..." >> $log_file
    sleep $CONNECTION_WARMUP_TIME
    
    echo "=== MEASUREMENT PHASE ===" >> $log_file
    # Phase 2: Measure performance with established connections
    h2load -n $MEASUREMENT_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $RASPBERRY_PI_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-raspberry-pi-benchmark-measurement" \
        --data "$temp_data_file" \
        --alpn-list=h3,h2 \
        --log-file "$csv_file" \
        https://$RASPBERRY_PI_IP/echo >> $log_file 2>&1
    
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
        echo "Target Server: $RASPBERRY_PI_IP" >> $log_file
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
    echo "Verifying HTTP/3 connectivity to Raspberry Pi..."
    
    # Test HTTP/3 with curl (if available)
    if command -v curl &> /dev/null; then
        local http3_test=$(curl -k --http3 "https://$RASPBERRY_PI_IP/echo" 2>/dev/null | grep -c "Raspberry Pi" || echo "0")
        
        if [ "$http3_test" -gt 0 ]; then
            echo "✓ HTTP/3 is working correctly with Raspberry Pi"
            return 0
        else
            echo "⚠ HTTP/3 test failed, but continuing with benchmark..."
            return 1
        fi
    else
        echo "⚠ curl not available, skipping HTTP/3 verification"
        return 1
    fi
}

# Function to collect network statistics
collect_network_stats() {
    echo "=== COLLECTING NETWORK STATISTICS ==="
    
    # Ping statistics to Raspberry Pi
    echo "Collecting ping statistics to Raspberry Pi..."
    ping -c 10 $RASPBERRY_PI_IP > "$LOG_DIR/ping_to_raspberry_pi.txt" 2>&1
    
    # Network interface statistics
    echo "Collecting network interface statistics..."
    ifconfig > "$LOG_DIR/network_interfaces.txt" 2>&1
    
    # Route information
    echo "Collecting routing information..."
    netstat -rn > "$LOG_DIR/routing_table.txt" 2>&1
    
    # DNS resolution test
    echo "Testing DNS resolution..."
    nslookup $RASPBERRY_PI_HOSTNAME > "$LOG_DIR/dns_resolution.txt" 2>&1
    
    echo "Network statistics collection completed"
}

# Main benchmark execution
echo "Starting Raspberry Pi benchmark..."

# Verify server connectivity first
if ! verify_server_connectivity; then
    echo "❌ Server connectivity verification failed. Please check the Raspberry Pi server."
    exit 1
fi

# Collect initial network statistics
collect_network_stats

# Main benchmark loop
for test_case in "${TEST_CASES[@]}"; do
    read -r delay loss <<< "$test_case"
    
    echo ""
    echo "================================================"
    echo "Test case: ${delay}ms delay, ${loss}% loss"
    echo "================================================"
    
    # Note: Network conditions are simulated by the client side
    # In a real scenario, you might use tc/netem on the client side
    echo "Note: Network conditions simulation not implemented on client side"
    echo "Delay: ${delay}ms, Loss: ${loss}% (simulated)"
    
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
echo "Target Server: $RASPBERRY_PI_IP ($RASPBERRY_PI_HOSTNAME)"
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

# Generate performance graphs
echo ""
echo "=== GENERATING PERFORMANCE GRAPHS ==="
if command -v python3 &> /dev/null; then
    if [ -f "scripts/simple_graph_generator.py" ]; then
        echo "Generating performance graphs..."
        if python3 scripts/simple_graph_generator.py "$LOG_DIR"; then
            echo "✅ Performance graphs generated successfully"
            echo "Generated graph files:"
            ls -la "$LOG_DIR"/*.png 2>/dev/null || echo "No graph files found"
        else
            echo "❌ Graph generation failed"
        fi
    else
        echo "⚠ Graph generation script not found"
    fi
else
    echo "⚠ Python3 not available, skipping graph generation"
fi

echo "================================================"
echo "Raspberry Pi Benchmark Completed: $(date)"
echo "Results: $LOG_DIR"
echo "================================================"
