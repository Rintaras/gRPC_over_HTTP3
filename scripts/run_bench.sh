#!/bin/bash

# Improved benchmark script for HTTP/2 vs HTTP/3 performance comparison
# Tests 4 network conditions: (0/0), (50/0), (100/1), (150/3)
# Features: Adjusted load, HTTP/3 enforcement, structured logging, network condition recording

SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"
LOG_DIR="/logs"

# Test cases: (delay_ms, loss_percent)
declare -a test_cases=(
    "0 0"    # 理想環境: 0ms遅延、0%損失
    "50 0"   # 中程度遅延: 50ms遅延、0%損失
    "100 1"  # 高遅延低損失: 100ms遅延、1%損失
    "150 3"  # 高遅延高損失: 150ms遅延、3%損失
)

# Benchmark parameters (unified for all protocols)
REQUESTS=10000       # 総リクエスト数
CONNECTIONS=100      # 同時接続数
THREADS=20          # 並列スレッド数
MAX_CONCURRENT=100  # 最大同時ストリーム数
REQUEST_DATA="Hello from benchmark client - HTTP/2 vs HTTP/3 performance comparison test with realistic data payload for accurate measurement"  # サイズ: 約150バイト

# Fair comparison parameters
WARMUP_REQUESTS=1000  # 接続確立後のウォームアップ用リクエスト数
MEASUREMENT_REQUESTS=9000  # 実際の測定用リクエスト数
CONNECTION_WARMUP_TIME=2  # 接続確立後の待機時間（秒）

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
echo "================================================"

# Create log directory
mkdir -p $LOG_DIR

# Function to get current timestamp
get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
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
        --connection-active-timeout 30 \
        --connection-inactivity-timeout 30 \
        --header "User-Agent: h2load-benchmark-warmup" \
        --data "$temp_data_file" \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    echo "Waiting ${CONNECTION_WARMUP_TIME}s for connections to stabilize..." >> $log_file
    sleep $CONNECTION_WARMUP_TIME
    
    echo "=== MEASUREMENT PHASE ===" >> $log_file
    # Phase 2: Measure performance with established connections
    h2load -n $MEASUREMENT_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 30 \
        --connection-inactivity-timeout 30 \
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
        --connection-active-timeout 30 \
        --connection-inactivity-timeout 30 \
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
        --connection-active-timeout 30 \
        --connection-inactivity-timeout 30 \
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
    sleep 5
    
    # Verify HTTP/3 is working before benchmark
    if ! verify_http3; then
        echo "Warning: HTTP/3 verification failed, continuing anyway..."
    fi
    
    # Run benchmarks sequentially to avoid interference
    echo "Running benchmarks..."
    run_http2_bench $delay $loss
    
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

    # Generate comprehensive comparison report
    generate_comparison_report() {
        local report_file="$LOG_DIR/comparison_report.txt"
        local csv_file="$LOG_DIR/comparison_data.csv"
        
        echo "包括的比較レポートを生成中..."
        
        # Run Python analysis script for detailed statistics and fair comparison
        if command -v python3 >/dev/null 2>&1; then
            echo "Python解析スクリプトを実行中..."
            python3 /scripts/analyze_results.py "$LOG_DIR"
        else
            echo "Python3が見つかりません。詳細解析をスキップします。"
        fi
    
         # Create detailed text report
     {
         echo "================================================"
         echo "HTTP/2 vs HTTP/3 性能比較レポート"
         echo "================================================"
         echo "生成時刻: $(get_timestamp)"
         echo "テストパラメータ:"
         echo "  総リクエスト数: $REQUESTS"
         echo "  接続数: $CONNECTIONS"
         echo "  スレッド数: $THREADS"
         echo "  最大同時ストリーム数: $MAX_CONCURRENT"
         echo ""
         
         echo "================================================"
         echo "サマリーテーブル"
         echo "================================================"
         printf "%-15s %-8s %-8s %-12s %-12s %-12s %-12s %-12s %-12s\n" \
             "テストケース" "プロトコル" "成功数" "スループット" "平均レイテンシ" "最小レイテンシ" "最大レイテンシ" "標準偏差" "+/- SD"
         echo "--------------------------------------------------------------------------------------------------------"
        
        # Process each test case
        for test_case in "${test_cases[@]}"; do
            read -r delay loss <<< "$test_case"
            
            # HTTP/2 results
            h2_log="$LOG_DIR/h2_${delay}ms_${loss}pct.log"
            if [ -f "$h2_log" ]; then
                                 # Extract HTTP/2 metrics
                 h2_throughput=$(grep "finished in" "$h2_log" | awk '{print $4}' | sed 's/,//')
                 h2_success=$(grep "requests:" "$h2_log" | awk '{print $6}')
                 h2_avg_latency=$(grep "time for request:" "$h2_log" | awk '{print $4}' | sed 's/ms//' | sed 's/us//')
                 h2_min_latency=$(grep "time for request:" "$h2_log" | awk '{print $2}' | sed 's/ms//' | sed 's/us//')
                 h2_max_latency=$(grep "time for request:" "$h2_log" | awk '{print $3}' | sed 's/ms//' | sed 's/us//')
                 h2_std_dev=$(grep "time for request:" "$h2_log" | awk '{print $5}' | sed 's/ms//' | sed 's/us//')
                 h2_within_sd=$(grep "time for request:" "$h2_log" | awk '{print $6}' | sed 's/%//')
                
                printf "%-15s %-8s %-8s %-12s %-12s %-12s %-12s %-12s %-12s\n" \
                    "${delay}ms/${loss}%" "HTTP/2" "$h2_success" "$h2_throughput" "$h2_avg_latency" "$h2_min_latency" "$h2_max_latency" "$h2_std_dev" "$h2_within_sd%"
            fi
            
            # HTTP/3 results
            h3_log="$LOG_DIR/h3_${delay}ms_${loss}pct.log"
            if [ -f "$h3_log" ]; then
                                 # Extract HTTP/3 metrics
                 h3_throughput=$(grep "finished in" "$h3_log" | awk '{print $4}' | sed 's/,//')
                 h3_success=$(grep "requests:" "$h3_log" | awk '{print $6}')
                 h3_avg_latency=$(grep "time for request:" "$h3_log" | awk '{print $4}' | sed 's/ms//' | sed 's/us//')
                 h3_min_latency=$(grep "time for request:" "$h3_log" | awk '{print $2}' | sed 's/ms//' | sed 's/us//')
                 h3_max_latency=$(grep "time for request:" "$h3_log" | awk '{print $3}' | sed 's/ms//' | sed 's/us//')
                 h3_std_dev=$(grep "time for request:" "$h3_log" | awk '{print $5}' | sed 's/ms//' | sed 's/us//')
                 h3_within_sd=$(grep "time for request:" "$h3_log" | awk '{print $6}' | sed 's/%//')
                
                printf "%-15s %-8s %-8s %-12s %-12s %-12s %-12s %-12s %-12s\n" \
                    "${delay}ms/${loss}%" "HTTP/3" "$h3_success" "$h3_throughput" "$h3_avg_latency" "$h3_min_latency" "$h3_max_latency" "$h3_std_dev" "$h3_within_sd%"
            fi
        done
        
                 echo ""
         echo "================================================"
         echo "テストケース別詳細メトリクス"
         echo "================================================"
         
         for test_case in "${test_cases[@]}"; do
             read -r delay loss <<< "$test_case"
             echo ""
             echo "テストケース: ${delay}ms遅延, ${loss}%損失"
             echo "----------------------------------------"
            
                         # HTTP/2 details
             h2_log="$LOG_DIR/h2_${delay}ms_${loss}pct.log"
             if [ -f "$h2_log" ]; then
                 echo "HTTP/2 結果:"
                 echo "  スループット: $(grep 'finished in' "$h2_log" | awk '{print $4, $5, $6}')"
                 echo "  リクエスト: $(grep 'requests:' "$h2_log" | awk '{print $2, $3, $4, $5, $6, $7, $8, $9, $10}')"
                 echo "  トラフィック: $(grep 'traffic:' "$h2_log")"
                 echo "  リクエスト時間: $(grep 'time for request:' "$h2_log" | awk '{print $2, $3, $4, $5, $6}')"
                 echo "  接続時間: $(grep 'time for connect:' "$h2_log" | awk '{print $2, $3, $4, $5, $6}')"
                 echo "  初回バイト時間: $(grep 'time to 1st byte:' "$h2_log" | awk '{print $2, $3, $4, $5, $6}')"
                 if grep -q "req/s" "$h2_log"; then
                     echo "  リクエスト/秒: $(grep 'req/s' "$h2_log" | awk '{print $2, $3, $4, $5, $6}')"
                 fi
             fi
            
                         # HTTP/3 details
             h3_log="$LOG_DIR/h3_${delay}ms_${loss}pct.log"
             if [ -f "$h3_log" ]; then
                 echo "HTTP/3 結果:"
                 echo "  スループット: $(grep 'finished in' "$h3_log" | awk '{print $4, $5, $6}')"
                 echo "  リクエスト: $(grep 'requests:' "$h3_log" | awk '{print $2, $3, $4, $5, $6, $7, $8, $9, $10}')"
                 echo "  トラフィック: $(grep 'traffic:' "$h3_log")"
                 echo "  リクエスト時間: $(grep 'time for request:' "$h3_log" | awk '{print $2, $3, $4, $5, $6}')"
                 echo "  接続時間: $(grep 'time for connect:' "$h3_log" | awk '{print $2, $3, $4, $5, $6}')"
                 echo "  初回バイト時間: $(grep 'time to 1st byte:' "$h3_log" | awk '{print $2, $3, $4, $5, $6}')"
                 if grep -q "req/s" "$h3_log"; then
                     echo "  リクエスト/秒: $(grep 'req/s' "$h3_log" | awk '{print $2, $3, $4, $5, $6}')"
                 fi
             fi
        done
        
                 echo ""
         echo "================================================"
         echo "パフォーマンス分析"
         echo "================================================"
         
         for test_case in "${test_cases[@]}"; do
             read -r delay loss <<< "$test_case"
             h2_log="$LOG_DIR/h2_${delay}ms_${loss}pct.log"
             h3_log="$LOG_DIR/h3_${delay}ms_${loss}pct.log"
             
             if [ -f "$h2_log" ] && [ -f "$h3_log" ]; then
                 echo ""
                 echo "テストケース: ${delay}ms遅延, ${loss}%損失"
                 echo "----------------------------------------"
                
                # Extract throughput values for comparison
                h2_throughput_num=$(grep "finished in" "$h2_log" | awk '{print $4}' | sed 's/,//')
                h3_throughput_num=$(grep "finished in" "$h3_log" | awk '{print $4}' | sed 's/,//')
                
                                 if [ -n "$h2_throughput_num" ] && [ -n "$h3_throughput_num" ]; then
                     # Calculate percentage difference
                     if (( $(echo "$h2_throughput_num > 0" | bc -l) )); then
                         throughput_diff=$(echo "scale=2; ($h3_throughput_num - $h2_throughput_num) * 100 / $h2_throughput_num" | bc -l)
                         echo "  スループット比較:"
                         echo "    HTTP/2: $h2_throughput_num req/s"
                         echo "    HTTP/3: $h3_throughput_num req/s"
                         echo "    差分: ${throughput_diff}% (HTTP/3 vs HTTP/2)"
                         
                         if (( $(echo "$throughput_diff > 0" | bc -l) )); then
                             echo "    HTTP/3はHTTP/2より${throughput_diff}%高速"
                         else
                             echo "    HTTP/2はHTTP/3より${throughput_diff#-}%高速"
                         fi
                     fi
                 fi
                
                # Extract latency values for comparison
                h2_avg_latency=$(grep "time for request:" "$h2_log" | awk '{print $4}' | sed 's/ms//')
                h3_avg_latency=$(grep "time for request:" "$h3_log" | awk '{print $4}' | sed 's/ms//')
                
                                 if [ -n "$h2_avg_latency" ] && [ -n "$h3_avg_latency" ]; then
                     if (( $(echo "$h2_avg_latency > 0" | bc -l) )); then
                         latency_diff=$(echo "scale=2; ($h3_avg_latency - $h2_avg_latency) * 100 / $h2_avg_latency" | bc -l)
                         echo "  レイテンシ比較:"
                         echo "    HTTP/2: ${h2_avg_latency}ms"
                         echo "    HTTP/3: ${h3_avg_latency}ms"
                         echo "    差分: ${latency_diff}% (HTTP/3 vs HTTP/2)"
                         
                         if (( $(echo "$latency_diff < 0" | bc -l) )); then
                             echo "    HTTP/3はHTTP/2より${latency_diff#-}%低レイテンシ"
                         else
                             echo "    HTTP/2はHTTP/3より${latency_diff}%低レイテンシ"
                         fi
                     fi
                 fi
            fi
        done
        
                 echo ""
         echo "================================================"
         echo "結論"
         echo "================================================"
         echo "このレポートは、異なるネットワーク条件下でのHTTP/2とHTTP/3の"
         echo "包括的な性能比較を提供します。"
         echo ""
         echo "分析された主要メトリクス:"
         echo "- スループット（1秒あたりのリクエスト数）"
         echo "- レイテンシ（平均、最小、最大）"
         echo "- 標準偏差と分布"
         echo "- 接続時間と初回バイト時間"
         echo "- 成功率とエラー処理"
         echo ""
         echo "テストされたネットワーク条件:"
         for test_case in "${test_cases[@]}"; do
             read -r delay loss <<< "$test_case"
             echo "- ${delay}ms遅延, ${loss}%パケット損失"
         done
        
    } > "$report_file"
    
         # Create CSV file for easy data analysis
     {
         echo "テストケース,プロトコル,成功数,スループット_req_s,平均レイテンシ_ms,最小レイテンシ_ms,最大レイテンシ_ms,標準偏差_ms,標準偏差内_パーセント,接続時間_ms,初回バイト時間_ms"
        
        for test_case in "${test_cases[@]}"; do
            read -r delay loss <<< "$test_case"
            test_case_name="${delay}ms_${loss}pct"
            
            # HTTP/2 data
            h2_log="$LOG_DIR/h2_${delay}ms_${loss}pct.log"
            if [ -f "$h2_log" ]; then
                h2_throughput=$(grep "finished in" "$h2_log" | awk '{print $4}' | sed 's/,//')
                h2_success=$(grep "requests:" "$h2_log" | awk '{print $6}')
                h2_avg_latency=$(grep "time for request:" "$h2_log" | awk '{print $4}' | sed 's/ms//')
                h2_min_latency=$(grep "time for request:" "$h2_log" | awk '{print $2}' | sed 's/ms//')
                h2_max_latency=$(grep "time for request:" "$h2_log" | awk '{print $3}' | sed 's/ms//')
                h2_std_dev=$(grep "time for request:" "$h2_log" | awk '{print $5}' | sed 's/ms//')
                h2_within_sd=$(grep "time for request:" "$h2_log" | awk '{print $6}' | sed 's/%//')
                                 h2_connect=$(grep "time for connect:" "$h2_log" | awk '{print $4}' | sed 's/ms//' | sed 's/us//')
                 h2_first_byte=$(grep "time to 1st byte:" "$h2_log" | awk '{print $4}' | sed 's/ms//' | sed 's/us//')
                
                echo "$test_case_name,HTTP/2,$h2_success,$h2_throughput,$h2_avg_latency,$h2_min_latency,$h2_max_latency,$h2_std_dev,$h2_within_sd,$h2_connect,$h2_first_byte"
            fi
            
            # HTTP/3 data
            h3_log="$LOG_DIR/h3_${delay}ms_${loss}pct.log"
            if [ -f "$h3_log" ]; then
                h3_throughput=$(grep "finished in" "$h3_log" | awk '{print $4}' | sed 's/,//')
                h3_success=$(grep "requests:" "$h3_log" | awk '{print $6}')
                h3_avg_latency=$(grep "time for request:" "$h3_log" | awk '{print $4}' | sed 's/ms//')
                h3_min_latency=$(grep "time for request:" "$h3_log" | awk '{print $2}' | sed 's/ms//')
                h3_max_latency=$(grep "time for request:" "$h3_log" | awk '{print $3}' | sed 's/ms//')
                h3_std_dev=$(grep "time for request:" "$h3_log" | awk '{print $5}' | sed 's/ms//')
                h3_within_sd=$(grep "time for request:" "$h3_log" | awk '{print $6}' | sed 's/%//')
                                 h3_connect=$(grep "time for connect:" "$h3_log" | awk '{print $4}' | sed 's/ms//' | sed 's/us//')
                 h3_first_byte=$(grep "time to 1st byte:" "$h3_log" | awk '{print $4}' | sed 's/ms//' | sed 's/us//')
                
                echo "$test_case_name,HTTP/3,$h3_success,$h3_throughput,$h3_avg_latency,$h3_min_latency,$h3_max_latency,$h3_std_dev,$h3_within_sd,$h3_connect,$h3_first_byte"
            fi
        done
        
    } > "$csv_file"
    
         echo "包括的比較レポートが生成されました:"
     echo "  テキストレポート: $report_file"
     echo "  CSVデータ: $csv_file"
}

# Generate the comparison report
generate_comparison_report 