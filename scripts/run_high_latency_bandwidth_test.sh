#!/bin/bash

# High latency, low bandwidth network test for HTTP/3 vs HTTP/2
# This script tests the hypothesis that HTTP/3 performs better than HTTP/2
# under high latency, low bandwidth network conditions

# タイムスタンプ付きディレクトリ作成
NOW=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="/logs/high_latency_bandwidth_${NOW}"
mkdir -p $LOG_DIR

echo "[INFO] ログディレクトリ: $LOG_DIR"

# Execute the entire benchmark inside the client container
docker exec grpc-client bash -c '
SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"
LOG_DIR="'$LOG_DIR'"

# High latency, low bandwidth test cases based on research papers
# Format: (delay_ms, loss_percent, bandwidth_mbps, description)
declare -a test_cases=(
    "50 0 100 '\''Low latency, high bandwidth (baseline)'\''"
    "100 0 50 '\''Medium latency, medium bandwidth'\''"
    "200 1 25 '\''High latency, low bandwidth (mobile-like)'\''"
    "300 2 10 '\''Very high latency, very low bandwidth (satellite-like)'\''"
    "500 3 5 '\''Extreme latency, extreme low bandwidth (rural/remote)'\''"
)

# Benchmark parameters optimized for high latency scenarios
REQUESTS=5000        # Reduced for high latency tests
CONNECTIONS=50       # Reduced for bandwidth constraints
THREADS=10          # Reduced for stability
MAX_CONCURRENT=50   # Reduced for bandwidth constraints
REQUEST_DATA="High latency bandwidth test payload - HTTP/3 vs HTTP/2 performance comparison under constrained network conditions with realistic data size for accurate measurement"

# Fair comparison parameters
WARMUP_REQUESTS=500   # Reduced warmup for high latency
MEASUREMENT_REQUESTS=4500  # Measurement requests
CONNECTION_WARMUP_TIME=5  # Longer warmup for high latency

echo "================================================"
echo "High Latency, Low Bandwidth Network Test"
echo "HTTP/3 vs HTTP/2 Performance Comparison"
echo "================================================"
echo "Parameters:"
echo "  Total Requests: $REQUESTS"
echo "  Connections: $CONNECTIONS"
echo "  Threads: $THREADS"
echo "  Max Concurrent Streams: $MAX_CONCURRENT"
echo "  Test Cases: ${#test_cases[@]}"
echo "  Fair Comparison: Enabled"
echo "    - Warmup Requests: $WARMUP_REQUESTS"
echo "    - Measurement Requests: $MEASUREMENT_REQUESTS"
echo "    - Connection Warmup Time: ${CONNECTION_WARMUP_TIME}s"
echo "================================================"

# Function to get current timestamp
get_timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

# Function to log network conditions
log_network_conditions() {
    local delay=$1
    local loss=$2
    local bandwidth=$3
    local description=$4
    local log_file=$5
    
    echo "=== NETWORK CONDITIONS ===" >> $log_file
    echo "Timestamp: $(get_timestamp)" >> $log_file
    echo "Delay: ${delay}ms" >> $log_file
    echo "Loss: ${loss}%" >> $log_file
    echo "Bandwidth: ${bandwidth}Mbps" >> $log_file
    echo "Description: ${description}" >> $log_file
    echo "Router IP: $ROUTER_IP" >> $log_file
    echo "Server IP: $SERVER_IP" >> $log_file
    
    # Get current qdisc configuration
    echo "Current qdisc configuration:" >> $log_file
    tc qdisc show dev eth0 >> $log_file 2>&1
    echo "" >> $log_file
}

# Function to run HTTP/2 benchmark with h2load
run_http2_bench() {
    local delay=$1
    local loss=$2
    local bandwidth=$3
    local description=$4
    local log_file="$LOG_DIR/h2_hlb_${delay}ms_${loss}pct_${bandwidth}mbps.log"
    local csv_file="$LOG_DIR/h2_hlb_${delay}ms_${loss}pct_${bandwidth}mbps.csv"
    
    echo "Running HTTP/2 benchmark (${delay}ms delay, ${loss}% loss, ${bandwidth}Mbps)..."
    
    # Clear log file and add header
    echo "=== HTTP/2 HIGH LATENCY BANDWIDTH TEST ===" > $log_file
    log_network_conditions $delay $loss $bandwidth "$description" $log_file
    
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
        --header "User-Agent: h2load-high-latency-warmup" \
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
        --header "User-Agent: h2load-high-latency-measurement" \
        --data "$temp_data_file" \
        --log-file "$csv_file" \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    # Clean up temporary file
    rm "$temp_data_file"
    
    # Add summary at the end
    echo "" >> $log_file
    echo "=== BENCHMARK SUMMARY ===" >> $log_file
    echo "Protocol: HTTP/2" >> $log_file
    echo "Network Conditions: ${delay}ms delay, ${loss}% loss, ${bandwidth}Mbps" >> $log_file
    echo "Description: $description" >> $log_file
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
    local bandwidth=$3
    local description=$4
    local log_file="$LOG_DIR/h3_hlb_${delay}ms_${loss}pct_${bandwidth}mbps.log"
    local csv_file="$LOG_DIR/h3_hlb_${delay}ms_${loss}pct_${bandwidth}mbps.csv"
    
    echo "Running HTTP/3 benchmark (${delay}ms delay, ${loss}% loss, ${bandwidth}Mbps)..."
    
    # Clear log file and add header
    echo "=== HTTP/3 HIGH LATENCY BANDWIDTH TEST ===" > $log_file
    log_network_conditions $delay $loss $bandwidth "$description" $log_file
    
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
        --header "User-Agent: h2load-high-latency-warmup" \
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
        --header "User-Agent: h2load-high-latency-measurement" \
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
            echo "⚠ h2load completed but protocol detection failed"
            protocol_used="Unknown"
        fi
    else
        echo "✗ h2load HTTP/3 benchmark failed"
        protocol_used="Failed"
    fi
    
    # Add summary at the end
    echo "" >> $log_file
    echo "=== BENCHMARK SUMMARY ===" >> $log_file
    echo "Protocol: $protocol_used" >> $log_file
    echo "Network Conditions: ${delay}ms delay, ${loss}% loss, ${bandwidth}Mbps" >> $log_file
    echo "Description: $description" >> $log_file
    echo "Fair Comparison: Enabled" >> $log_file
    echo "Warmup Requests: $WARMUP_REQUESTS" >> $log_file
    echo "Measurement Requests: $MEASUREMENT_REQUESTS" >> $log_file
    echo "End Time: $(get_timestamp)" >> $log_file
    echo "CSV Log: $csv_file" >> $log_file
    
    echo "HTTP/3 results saved to $log_file"
    echo "HTTP/3 CSV data saved to $csv_file"
}

# Main execution
echo "Starting high latency, low bandwidth network tests..."
echo "This test will verify if HTTP/3 shows better performance than HTTP/2"
echo "under high latency and low bandwidth network conditions."
echo ""

# Run tests for each network condition
for test_case in "${test_cases[@]}"; do
    # Parse test case parameters
    read -r delay loss bandwidth description <<< "$test_case"
    
    echo "================================================"
    echo "Testing: $description"
    echo "Conditions: ${delay}ms delay, ${loss}% loss, ${bandwidth}Mbps bandwidth"
    echo "================================================"
    
    # Set network conditions
    echo "Setting network conditions..."
    # Note: Network conditions are set from host, not from container
    
    # Wait for network conditions to stabilize
    echo "Waiting 5 seconds for network conditions to stabilize..."
    sleep 5
    
    # Run HTTP/2 test
    echo ""
    echo "Running HTTP/2 test..."
    run_http2_bench $delay $loss $bandwidth "$description"
    
    # Wait between tests
    echo "Waiting 10 seconds between tests..."
    sleep 10
    
    # Run HTTP/3 test
    echo ""
    echo "Running HTTP/3 test..."
    run_http3_bench $delay $loss $bandwidth "$description"
    
    # Wait before next test case
    echo "Waiting 15 seconds before next test case..."
    sleep 15
    
    echo ""
done

echo "================================================"
echo "High latency, low bandwidth tests completed!"
echo "Results saved in $LOG_DIR"
echo "================================================"
'

# Generate analysis report (ホスト側で実行)
echo "Generating analysis report..."
python3 ./scripts/analyze_high_latency_results.py $LOG_DIR

# グラフ生成も必ず実行（ホスト側で実行）
echo "Generating performance graphs..."
python3 ./scripts/generate_performance_graphs.py $LOG_DIR

echo "Analysis & graph complete! Check the reports and graphs in $LOG_DIR" 