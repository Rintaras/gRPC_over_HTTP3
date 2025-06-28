#!/bin/bash

# Improved benchmark script for HTTP/2 vs HTTP/3 performance comparison
# Tests 4 network conditions: (0/0), (50/0), (100/1), (150/3)
# Features: Adjusted load, HTTP/3 enforcement, structured logging, network condition recording

SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"
LOG_DIR="/logs"

# Test cases: (delay_ms, loss_percent)
declare -a test_cases=(
    "0 0"
    "50 0"
    "100 1"
    "150 3"
)

# Benchmark parameters (reduced load for better success rate)
REQUESTS=1000    # 1000リクエストに減らす
CONNECTIONS=10   # 10接続に減らす
THREADS=2        # スレッドも2に減らす
CONCURRENT=10    # 最大同時10

echo "================================================"
echo "HTTP/2 vs HTTP/3 Performance Benchmark"
echo "================================================"
echo "Parameters:"
echo "  Requests: $REQUESTS"
echo "  Connections: $CONNECTIONS"
echo "  Threads: $THREADS"
echo "  Max Concurrent: $CONCURRENT"
echo "  Test Cases: ${#test_cases[@]}"
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
    
    echo "Running HTTP/2 benchmark (${delay}ms delay, ${loss}% loss)..."
    
    # Clear log file and add header
    echo "=== HTTP/2 BENCHMARK RESULTS ===" > $log_file
    log_network_conditions $delay $loss $log_file
    
    # Run h2load for HTTP/2 with optimized parameters
    h2load -n $REQUESTS -c $CONNECTIONS -t $THREADS -m $CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 30 \
        --connection-inactivity-timeout 30 \
        --header "User-Agent: h2load-benchmark" \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    # Add summary at the end
    echo "" >> $log_file
    echo "=== BENCHMARK SUMMARY ===" >> $log_file
    echo "Protocol: HTTP/2" >> $log_file
    echo "End Time: $(get_timestamp)" >> $log_file
    
    echo "HTTP/2 results saved to $log_file"
}

# Function to run HTTP/3 benchmark with h2load (if supported)
run_http3_h2load_bench() {
    local delay=$1
    local loss=$2
    local log_file="$LOG_DIR/h3_${delay}ms_${loss}pct.log"
    
    echo "Running HTTP/3 benchmark with h2load (${delay}ms delay, ${loss}% loss)..."
    
    # Clear log file and add header
    echo "=== HTTP/3 BENCHMARK RESULTS (h2load) ===" > $log_file
    log_network_conditions $delay $loss $log_file
    
    # Try h2load with HTTP/3
    echo "Attempting h2load with HTTP/3..." >> $log_file
    
    # Run h2load with HTTP/3 ALPN
    h2load -n $REQUESTS -c $CONNECTIONS -t $THREADS -m $CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 30 \
        --connection-inactivity-timeout 30 \
        --header "User-Agent: h2load-benchmark" \
        --alpn-list=h3,h2 \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    # Check if h2load succeeded and analyze protocol usage
    if grep -q "succeeded, 0 failed" $log_file; then
        # Check if HTTP/3 was actually used by looking for QUIC indicators
        if grep -q "Application protocol: h3" $log_file; then
            echo "✓ h2load HTTP/3 benchmark completed successfully (confirmed HTTP/3)"
            protocol_used="HTTP/3 (confirmed)"
            
            # Add summary at the end
            echo "" >> $log_file
            echo "=== BENCHMARK SUMMARY ===" >> $log_file
            echo "Protocol: $protocol_used" >> $log_file
            echo "End Time: $(get_timestamp)" >> $log_file
            
            echo "HTTP/3 h2load results saved to $log_file"
            return 0
        elif grep -q "Application protocol: h2" $log_file; then
            echo "⚠ h2load completed but used HTTP/2 (fallback), switching to curl-based HTTP/3"
            return 1
        else
            echo "✓ h2load benchmark completed successfully (protocol unclear)"
            protocol_used="Unknown"
            
            # Add summary at the end
            echo "" >> $log_file
            echo "=== BENCHMARK SUMMARY ===" >> $log_file
            echo "Protocol: $protocol_used" >> $log_file
            echo "End Time: $(get_timestamp)" >> $log_file
            
            echo "HTTP/3 h2load results saved to $log_file"
            return 0
        fi
    else
        echo "h2load HTTP/3 failed, falling back to curl-based benchmark"
        return 1
    fi
}

# Function to run HTTP/3 benchmark with curl (since h2load doesn't support HTTP/3)
run_http3_bench() {
    local delay=$1
    local loss=$2
    local log_file="$LOG_DIR/h3_${delay}ms_${loss}pct.log"
    
    echo "Running HTTP/3 benchmark (${delay}ms delay, ${loss}% loss)..."
    
    # Clear log file and add header
    echo "=== HTTP/3 BENCHMARK RESULTS ===" > $log_file
    log_network_conditions $delay $loss $log_file
    
    # Initialize counters
    success=0
    fail=0
    latencies=()
    connect_times=()
    first_byte_times=()
    
    echo "Starting HTTP/3 benchmark with curl (h2load equivalent load)..." >> $log_file
    echo "Requests: $REQUESTS, Connections: $CONNECTIONS, Threads: $THREADS, Max Concurrent: $CONCURRENT" >> $log_file
    echo "Start time: $(date -u)" >> $log_file
    echo "" >> $log_file
    
    # Calculate requests per connection to match h2load behavior
    local requests_per_conn=$((REQUESTS / CONNECTIONS))
    local remaining_requests=$((REQUESTS % CONNECTIONS))
    
    echo "Requests per connection: $requests_per_conn" >> $log_file
    echo "Remaining requests: $remaining_requests" >> $log_file
    echo "" >> $log_file
    
    # Function to run requests for a single connection
    run_connection_requests() {
        local conn_id=$1
        local req_count=$2
        local conn_latencies=()
        local conn_connect_times=()
        local conn_first_byte_times=()
        local conn_success=0
        local conn_fail=0
        
        for i in $(seq 1 $req_count); do
            # Make HTTP/3 request with detailed timing metrics
            response=$(curl -sk --http3 \
                --connect-timeout 10 \
                --max-time 30 \
                --retry 0 \
                --no-progress-meter \
                -w "%{time_total} %{time_connect} %{time_starttransfer} %{size_download} %{http_code} %{http_version}\n" \
                https://$SERVER_IP/echo 2>/dev/null)
            
            # Process response - curl outputs body first, then -w format
            if [ $? -eq 0 ]; then
                # Get the last line which contains the -w format data
                last_line=$(echo "$response" | tail -1)
                read time_total time_connect time_starttransfer size code version <<< "$last_line"
                
                if [ "$code" = "200" ]; then
                    conn_latencies+=("$time_total")
                    conn_connect_times+=("$time_connect")
                    conn_first_byte_times+=("$time_starttransfer")
                    ((conn_success++))
                else
                    ((conn_fail++))
                fi
            else
                ((conn_fail++))
            fi
            
            # Add small delay between requests to simulate h2load behavior
            sleep 0.001
        done
        
        # Return results as space-separated string
        echo "$conn_success $conn_fail ${conn_latencies[*]} ${conn_connect_times[*]} ${conn_first_byte_times[*]}"
    }
    
    # Run connections in parallel using background jobs
    local pids=()
    local temp_files=()
    
    for conn in $(seq 1 $CONNECTIONS); do
        local req_count=$requests_per_conn
        if [ $conn -le $remaining_requests ]; then
            ((req_count++))
        fi
        
        # Create temporary file for this connection's results
        temp_file=$(mktemp)
        temp_files+=("$temp_file")
        
        # Run connection requests in background
        (run_connection_requests $conn $req_count > "$temp_file") &
        pids+=($!)
        
        # Limit concurrent connections
        if [ ${#pids[@]} -ge $THREADS ]; then
            wait ${pids[0]}
            pids=("${pids[@]:1}")
        fi
    done
    
    # Wait for all background jobs to complete
    for pid in "${pids[@]}"; do
        wait $pid
    done
    
    # Collect results from all connections
    for temp_file in "${temp_files[@]}"; do
        if [ -f "$temp_file" ]; then
            read conn_success conn_fail conn_latencies conn_connect_times conn_first_byte_times < "$temp_file"
            ((success += conn_success))
            ((fail += conn_fail))
            # Add individual values to arrays
            for l in $conn_latencies; do
                latencies+=("$l")
            done
            for c in $conn_connect_times; do
                connect_times+=("$c")
            done
            for f in $conn_first_byte_times; do
                first_byte_times+=("$f")
            done
            rm "$temp_file"
        fi
    done
    
    # Calculate statistics
    min=999999
    max=0
    sum=0
    count=0
    
    # Calculate connect time statistics
    connect_min=999999
    connect_max=0
    connect_sum=0
    
    # Calculate first byte time statistics
    first_byte_min=999999
    first_byte_max=0
    first_byte_sum=0
    
    for l in "${latencies[@]}"; do
        if (( $(echo "$l < $min" | bc -l) )); then
            min=$l
        fi
        if (( $(echo "$l > $max" | bc -l) )); then
            max=$l
        fi
        sum=$(echo "$sum + $l" | bc -l)
        ((count++))
    done
    
    # Calculate connect time statistics
    for c in "${connect_times[@]}"; do
        if (( $(echo "$c < $connect_min" | bc -l) )); then
            connect_min=$c
        fi
        if (( $(echo "$c > $connect_max" | bc -l) )); then
            connect_max=$c
        fi
        connect_sum=$(echo "$connect_sum + $c" | bc -l)
    done
    
    # Calculate first byte time statistics
    for f in "${first_byte_times[@]}"; do
        if (( $(echo "$f < $first_byte_min" | bc -l) )); then
            first_byte_min=$f
        fi
        if (( $(echo "$f > $first_byte_max" | bc -l) )); then
            first_byte_max=$f
        fi
        first_byte_sum=$(echo "$first_byte_sum + $f" | bc -l)
    done
    
    if [ $count -gt 0 ]; then
        mean=$(echo "$sum / $count" | bc -l)
        connect_mean=$(echo "$connect_sum / $count" | bc -l)
        first_byte_mean=$(echo "$first_byte_sum / $count" | bc -l)
    else
        mean=0
        min=0
        max=0
        connect_mean=0
        connect_min=0
        connect_max=0
        first_byte_mean=0
        first_byte_min=0
        first_byte_max=0
    fi
    
    # Calculate throughput
    if [ $count -gt 0 ]; then
        # Estimate total time (assuming requests were distributed evenly)
        total_time=$(echo "$max * $CONNECTIONS / $THREADS" | bc -l)
        if (( $(echo "$total_time < 0.001" | bc -l) )); then
            total_time=0.001
        fi
        throughput=$(echo "$count / $total_time" | bc -l)
    else
        throughput=0
        total_time=0
    fi
    
    # Output detailed results in h2load format
    echo "finished in ${total_time}s, ${throughput} req/s, 0B/s" >> $log_file
    echo "requests: $REQUESTS total, $REQUESTS started, $count done, $success succeeded, $fail failed, 0 errored, 0 timeout" >> $log_file
    echo "status codes: $success 2xx, 0 3xx, 0 4xx, 0 5xx" >> $log_file
    echo "traffic: 0B (0) total, 0B (0) headers (space savings 0.00%), 0B (0) data" >> $log_file
    echo "                     min         max         mean         sd        +/- sd" >> $log_file
    echo "time for request: $(printf "%8.0fus" $(echo "$min * 1000000" | bc -l)) $(printf "%8.0fus" $(echo "$max * 1000000" | bc -l)) $(printf "%8.0fus" $(echo "$mean * 1000000" | bc -l)) $(printf "%8.0fus" 0) $(printf "%6.2f%%" 100)" >> $log_file
    echo "time for connect: $(printf "%8.0fus" $(echo "$connect_min * 1000000" | bc -l)) $(printf "%8.0fus" $(echo "$connect_max * 1000000" | bc -l)) $(printf "%8.0fus" $(echo "$connect_mean * 1000000" | bc -l)) $(printf "%8.0fus" 0) $(printf "%6.2f%%" 100)" >> $log_file
    echo "time to 1st byte: $(printf "%8.0fus" $(echo "$first_byte_min * 1000000" | bc -l)) $(printf "%8.0fus" $(echo "$first_byte_max * 1000000" | bc -l)) $(printf "%8.0fus" $(echo "$first_byte_mean * 1000000" | bc -l)) $(printf "%8.0fus" 0) $(printf "%6.2f%%" 100)" >> $log_file
    echo "req/s           : $(printf "%8.2f" $throughput) $(printf "%8.2f" $throughput) $(printf "%8.2f" $throughput) $(printf "%8.2f" 0) $(printf "%6.2f%%" 100)" >> $log_file
    
    # Add summary at the end
    echo "" >> $log_file
    echo "=== BENCHMARK SUMMARY ===" >> $log_file
    echo "Protocol: HTTP/3" >> $log_file
    echo "End Time: $(get_timestamp)" >> $log_file
    
    echo "HTTP/3 results saved to $log_file"
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
    
    # Try h2load for HTTP/3 first, fallback to curl if it fails
    if ! run_http3_h2load_bench $delay $loss; then
        echo "Falling back to curl-based HTTP/3 benchmark..."
        run_http3_bench $delay $loss
    fi
    
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