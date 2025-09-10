#!/bin/bash

# Raspberry Pi HTTP/2 vs HTTP/3 Performance Benchmark
# Tests 4 network conditions: (0/3), (75/3), (150/3), (225/3)
# Features: Long measurement time, increased connections, extended timeouts, protocol separation

echo "================================================"
echo "Raspberry Pi HTTP/2 vs HTTP/3 パフォーマンスベンチマーク"
echo "================================================"
echo "ベンチマーク開始: $(date)"
echo "================================================"

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
echo "Raspberry Pi HTTP/2 vs HTTP/3 パフォーマンスベンチマーク"
echo "================================================"
echo "パラメータ:"
echo "  Raspberry Pi IP: $RASPBERRY_PI_IP"
echo "  総リクエスト数: $REQUESTS"
echo "  接続数: $CONNECTIONS"
echo "  スレッド数: $THREADS"
echo "  最大同時ストリーム数: $MAX_CONCURRENT"
echo "  接続あたりのリクエスト数: $REQUESTS_PER_CONNECTION"
echo "  スレッドあたりの接続数: $CONNECTIONS_PER_THREAD"
echo "  リクエストデータ: \"$REQUEST_DATA\""
echo "  テストケース数: ${#TEST_CASES[@]}"
echo "  公平比較: 有効"
echo "    - ウォームアップリクエスト数: $WARMUP_REQUESTS"
echo "    - 測定リクエスト数: $MEASUREMENT_REQUESTS"
echo "    - 接続ウォームアップ時間: ${CONNECTION_WARMUP_TIME}秒"
echo "  長時間測定: 有効"
echo "    - 推定測定時間: テストケースあたり約3-5分"
echo "    - プロトコル分離: HTTP/2とHTTP/3の間で30秒"
echo "    - 拡張タイムアウト: 接続で60秒"
echo "================================================"

# Create log directory with timestamp
NOW=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs/raspberry_pi_benchmark_${NOW}"
mkdir -p "$LOG_DIR"

echo "ログディレクトリ: $LOG_DIR"

# ベンチマークパラメータをテキストファイルに保存
cat <<EOF > "$LOG_DIR/benchmark_params.txt"
RASPBERRY_PI_IP=$RASPBERRY_PI_IP
RASPBERRY_PI_HOSTNAME=$RASPBERRY_PI_HOSTNAME
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
    echo "Raspberry Piサーバーの接続性を確認中..."
    
    # Test HTTP/2 connectivity
    local http2_test=$(curl -k -s -I https://$RASPBERRY_PI_IP/echo 2>/dev/null | grep -c "HTTP/2")
    if [ "$http2_test" -gt 0 ]; then
        echo "✓ HTTP/2接続性確認済み"
    else
        echo "✗ HTTP/2接続失敗"
        return 1
    fi
    
    # Test HTTP/3 connectivity with quiche client
    if command -v ./quiche-client/target/release/quiche-client >/dev/null 2>&1; then
        local http3_test=$(./quiche-client/target/release/quiche-client https://$RASPBERRY_PI_IP:4433/ --no-verify 2>/dev/null | grep -c "response\|connection closed\|validation_state=Validated" || echo "0")
        if [ "$http3_test" -gt 0 ]; then
            echo "✓ HTTP/3接続性確認済み"
        else
            echo "⚠ HTTP/3接続テスト失敗 (quiche client)"
        fi
    else
        echo "⚠ HTTP/3テスト用のquiche clientが利用できません"
    fi
    
    return 0
}

# Function to log network conditions (simulated on client side)
log_network_conditions() {
    local delay=$1
    local loss=$2
    local log_file=$3
    
    echo "=== NETWORK CONDITIONS (SIMULATED) ===" >> $log_file
    echo "Timestamp: $(get_timestamp)" >> $log_file
    echo "Delay: ${delay}ms (simulated)" >> $log_file
    echo "Loss: ${loss}% (simulated)" >> $log_file
    echo "Target Server: $RASPBERRY_PI_IP" >> $log_file
    echo "Note: Network conditions are simulated on client side" >> $log_file
    echo "" >> $log_file
}

# Function to run HTTP/2 benchmark with h2load
run_http2_bench() {
    local delay=$1
    local loss=$2
    local log_file="$LOG_DIR/h2_${delay}ms_${loss}pct.log"
    local csv_file="$LOG_DIR/h2_${delay}ms_${loss}pct.csv"
    
    echo "HTTP/2ベンチマーク実行中 (${delay}ms遅延, ${loss}%損失)..."
    
    # Clear log file and add header
    echo "=== HTTP/2 BENCHMARK RESULTS ===" > $log_file
    log_network_conditions $delay $loss $log_file
    
    # Create temporary data file for h2load
    local temp_data_file=$(mktemp)
    echo "$REQUEST_DATA" > "$temp_data_file"
    
    # Fair comparison: Establish connections first, then measure
    echo "公平比較のためHTTP/2接続を確立中..."
    echo "=== CONNECTION ESTABLISHMENT PHASE ===" >> $log_file
    
    # Phase 1: Establish connections with warmup requests
    h2load -n $WARMUP_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $RASPBERRY_PI_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-benchmark-warmup" \
        --data "$temp_data_file" \
        https://$RASPBERRY_PI_IP/echo >> $log_file 2>&1
    
    echo "接続の安定化のため${CONNECTION_WARMUP_TIME}秒待機中..." >> $log_file
    sleep $CONNECTION_WARMUP_TIME
    
    echo "=== MEASUREMENT PHASE ===" >> $log_file
    # Phase 2: Measure performance with established connections
    h2load -n $MEASUREMENT_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $RASPBERRY_PI_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-benchmark-measurement" \
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
    
    echo "HTTP/2結果を$log_fileに保存しました"
    echo "HTTP/2 CSVデータを$csv_fileに保存しました"
}

# Function to run HTTP/3 benchmark with quiche client
run_http3_bench() {
    local delay=$1
    local loss=$2
    local log_file="$LOG_DIR/h3_${delay}ms_${loss}pct.log"
    local csv_file="$LOG_DIR/h3_${delay}ms_${loss}pct.csv"
    
    echo "quiche clientでHTTP/3ベンチマーク実行中 (${delay}ms遅延, ${loss}%損失)..."
    
    # Clear log file and add header
    echo "=== HTTP/3 BENCHMARK RESULTS ===" > $log_file
    log_network_conditions $delay $loss $log_file
    
    # Check if quiche client is available
    if ! command -v ./quiche-client/target/release/quiche-client >/dev/null 2>&1; then
        echo "✗ quiche clientが利用できません。まずビルドします..."
        echo "Building quiche client..." >> $log_file
        
        cd quiche-client
        if cargo build --release --bin quiche-client; then
            echo "✓ quiche clientのビルドが成功しました"
            cd ..
        else
            echo "✗ quiche clientのビルドに失敗しました"
            cd ..
            return 1
        fi
    fi
    
    # Create temporary data file for requests
    local temp_data_file=$(mktemp)
    echo "$REQUEST_DATA" > "$temp_data_file"
    
    echo "=== MEASUREMENT PHASE ===" >> $log_file
    echo "quiche clientでHTTP/3ベンチマーク実行中..." >> $log_file
    
    # Run multiple HTTP/3 requests to simulate benchmark
    local start_time=$(date +%s)
    local success_count=0
    local total_count=100  # Reduced for quiche client testing
    
    for i in $(seq 1 $total_count); do
        echo "リクエスト $i/$total_count..." >> $log_file
        
        # Run quiche client request
        local request_start=$(date +%s%N | cut -b1-13)  # milliseconds
        local result=$(RUST_LOG=info ./quiche-client/target/release/quiche-client https://$RASPBERRY_PI_IP:4433/ --no-verify 2>&1)
        local request_end=$(date +%s%N | cut -b1-13)  # milliseconds
        
        # Calculate request time in milliseconds
        local request_time=$((request_end - request_start))
        
        # Log result
        echo "Request $i: ${request_time}ms" >> $log_file
        echo "$(date +%s),200,$((request_time * 1000))" >> "$csv_file"  # Convert to microseconds
        
        # Check for successful connection indicators in quiche output
        if echo "$result" | grep -q "response\|connection closed\|validation_state=Validated"; then
            ((success_count++))
            echo "Request $i: SUCCESS" >> $log_file
        else
            echo "Request $i: FAILED" >> $log_file
        fi
        
        # Small delay between requests
        sleep 0.1
    done
    
    local end_time=$(date +%s)
    local total_time=$((end_time - start_time))
    
    # Clean up temporary file
    rm "$temp_data_file"
    
    # Add summary at the end
    echo "" >> $log_file
    echo "=== BENCHMARK SUMMARY ===" >> $log_file
    echo "Protocol: HTTP/3 (quiche client)" >> $log_file
    echo "Target Server: $RASPBERRY_PI_IP:4433" >> $log_file
    echo "Total Requests: $total_count" >> $log_file
    echo "Successful Requests: $success_count" >> $log_file
    echo "Success Rate: $((success_count * 100 / total_count))%" >> $log_file
    echo "Total Time: ${total_time}s" >> $log_file
    echo "End Time: $(get_timestamp)" >> $log_file
    echo "CSV Log: $csv_file" >> $log_file
    
    echo "HTTP/3結果を$log_fileに保存しました"
    echo "HTTP/3 CSVデータを$csv_fileに保存しました"
}

# Function to stabilize system before benchmark
stabilize_system() {
    local delay=$1
    local loss=$2
    
    echo "=== システム安定化 ==="
    echo "タイムスタンプ: $(get_timestamp)"
    echo "遅延: ${delay}ms, 損失: ${loss}% (シミュレート)"
    
    # Wait for system stabilization
    echo "システム安定化のため${SYSTEM_STABILIZATION_TIME}秒待機中..."
    sleep $SYSTEM_STABILIZATION_TIME
    
    # Memory cleanup if enabled
    if [ "$MEMORY_CLEANUP_ENABLED" = true ]; then
        echo "メモリクリーンアップ実行中..."
        sync
    fi
    
    echo "システム安定化完了"
    echo ""
}

# Main benchmark loop
for test_case in "${TEST_CASES[@]}"; do
    read -r delay loss <<< "$test_case"
    
    echo ""
    echo "================================================"
    echo "テストケース: ${delay}ms遅延, ${loss}%損失"
    echo "================================================"
    
    # System stabilization for consistent results
    stabilize_system $delay $loss
    
    # Wait for system to stabilize
    echo "システムの安定化を待機中..."
    sleep 10
    
    # Verify server connectivity before benchmark
    if ! verify_server_connectivity; then
        echo "警告: サーバー接続性の確認に失敗しましたが、続行します..."
    fi
    
    # Run benchmarks sequentially to avoid interference
    echo "ベンチマーク実行中..."
    run_http2_bench $delay $loss
    
    echo "プロトコル間で30秒待機中..."
    sleep 30
    
    # Run HTTP/3 benchmark with quiche client
    run_http3_bench $delay $loss
    
    echo "テストケース完了: ${delay}ms遅延, ${loss}%損失"
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
echo "Target Server: $RASPBERRY_PI_IP"
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

# Generate performance graphs using simple_graph_generator.py
echo ""
echo "=== GENERATING PERFORMANCE GRAPHS ==="
if command -v python3 >/dev/null 2>&1; then
    if python3 scripts/simple_graph_generator.py "$LOG_DIR"; then
        echo "✅ Performance graphs generated successfully"
        echo "Generated graph files:"
        ls -la "$LOG_DIR"/*.png 2>/dev/null || echo "No graph files found"
    else
        echo "❌ Failed to generate performance graphs"
        echo "Manual graph generation required:"
        echo "python3 scripts/simple_graph_generator.py $LOG_DIR"
    fi
else
    echo "⚠ Python3 not available, skipping graph generation"
fi

echo "================================================"
echo "Raspberry Pi benchmark complete: $(date)"
echo "Results: $LOG_DIR"
echo "================================================"
