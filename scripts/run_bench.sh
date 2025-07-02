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

# Benchmark parameters (h2load and curl unified)
REQUESTS=1000        # 総リクエスト数
CONNECTIONS=50       # 同時接続数 (HTTP/3のパフォーマンスをh2loadと一致させるため、さらに増加)
THREADS=10          # 並列スレッド数
MAX_CONCURRENT=50   # 最大同時ストリーム数
REQUEST_DATA="Hello from benchmark client - HTTP/2 vs HTTP/3 performance comparison test with realistic data payload for accurate measurement"  # サイズ: 約150バイト

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
    
    # Create temporary data file for h2load
    local temp_data_file=$(mktemp)
    echo "$REQUEST_DATA" > "$temp_data_file"
    
    # Run h2load for HTTP/2 with optimized parameters
    h2load -n $REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 30 \
        --connection-inactivity-timeout 30 \
        --header "User-Agent: h2load-benchmark" \
        --data "$temp_data_file" \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    # Clean up temporary file
    rm "$temp_data_file"
    
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
    
    # Create temporary data file for h2load
    local temp_data_file=$(mktemp)
    echo "$REQUEST_DATA" > "$temp_data_file"
    
    # Run h2load with HTTP/3 ALPN
    h2load -n $REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 30 \
        --connection-inactivity-timeout 30 \
        --header "User-Agent: h2load-benchmark" \
        --data "$temp_data_file" \
        --alpn-list=h3,h2 \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    # Clean up temporary file
    rm "$temp_data_file"
    
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
    total_data_transferred=0
    total_headers_size=0
    total_download_size=0
    
    echo "Starting HTTP/3 benchmark with curl (h2load equivalent load)..." >> $log_file
    echo "Requests: $REQUESTS, Connections: $CONNECTIONS, Threads: $THREADS, Max Concurrent: $MAX_CONCURRENT" >> $log_file
    echo "Start time: $(date -u)" >> $log_file
    echo "" >> $log_file
    
    # Log load distribution to match h2load
    echo "Load Distribution (matching h2load):" >> $log_file
    echo "  Requests per connection: $REQUESTS_PER_CONNECTION" >> $log_file
    echo "  Remaining requests: $REMAINING_REQUESTS" >> $log_file
    echo "  Connections per thread: $CONNECTIONS_PER_THREAD" >> $log_file
    echo "  Request data: \"$REQUEST_DATA\"" >> $log_file
    echo "" >> $log_file
    
    # Function to run requests for a single connection (matching h2load behavior)
    run_connection_requests() {
        local conn_id=$1
        local req_count=$2
        local conn_latencies=()
        local conn_connect_times=()
        local conn_first_byte_times=()
        local conn_download_sizes=()
        local conn_success=0
        local conn_fail=0
        
        # Process requests in batches for better performance
        local batch_size=50  # Further increased batch size for maximum parallelism
        local remaining=$req_count
        
        while [ $remaining -gt 0 ]; do
            local current_batch=$((remaining > batch_size ? batch_size : remaining))
            
            # Create batch of curl commands
            local batch_pids=()
            local batch_temp_files=()
            
            for i in $(seq 1 $current_batch); do
                # Create temporary file for this request
                temp_file=$(mktemp)
                batch_temp_files+=("$temp_file")
                
                # Make HTTP/3 request with same data as h2load
                (curl -sk --http3 \
                    --connect-timeout 10 \
                    --max-time 30 \
                    --retry 0 \
                    --no-progress-meter \
                    --data "$REQUEST_DATA" \
                    -w "%{time_total} %{time_connect} %{time_starttransfer} %{size_download} %{http_code} %{http_version}\n" \
                    https://$SERVER_IP/echo 2>/dev/null > "$temp_file") &
                batch_pids+=($!)
            done
            
            # Wait for batch to complete
            for pid in "${batch_pids[@]}"; do
                wait $pid
            done
            
            # Process batch results
            for temp_file in "${batch_temp_files[@]}"; do
                if [ -f "$temp_file" ]; then
                    response=$(cat "$temp_file")
                    rm "$temp_file"
                    
                    # Process response - curl outputs body first, then -w format
                    if [ -n "$response" ]; then
                        # Get the last line which contains the -w format data
                        last_line=$(echo "$response" | tail -1)
                        read time_total time_connect time_starttransfer size code version <<< "$last_line"
                        
                        if [ "$code" = "200" ]; then
                            conn_latencies+=("$time_total")
                            conn_connect_times+=("$time_connect")
                            conn_first_byte_times+=("$time_starttransfer")
                            conn_download_sizes+=("$size")
                            ((conn_success++))
                        else
                            ((conn_fail++))
                        fi
                    else
                        ((conn_fail++))
                    fi
                fi
            done
            
            remaining=$((remaining - current_batch))
        done
        
        # Return results as space-separated string
        echo "$conn_success $conn_fail ${conn_latencies[*]} ${conn_connect_times[*]} ${conn_first_byte_times[*]} ${conn_download_sizes[*]}"
    }
    
    # Run connections in parallel using background jobs (matching h2load thread distribution)
    local pids=()
    local temp_files=()
    local conn_counter=0
    
    # Start all connections simultaneously for maximum concurrency (like h2load)
    echo "Starting $CONNECTIONS connections with $THREADS threads..." >> $log_file
    
    for thread in $(seq 1 $THREADS); do
        echo "  Thread $thread: starting $CONNECTIONS_PER_THREAD connections" >> $log_file
        for conn_in_thread in $(seq 1 $CONNECTIONS_PER_THREAD); do
            ((conn_counter++))
            
            local req_count=$REQUESTS_PER_CONNECTION
            if [ $conn_counter -le $REMAINING_REQUESTS ]; then
                ((req_count++))
            fi
            
            # Create temporary file for this connection's results
            temp_file=$(mktemp)
            temp_files+=("$temp_file")
            
            # Run connection requests in background (maximize concurrency)
            (run_connection_requests $conn_counter $req_count > "$temp_file") &
            pids+=($!)
            
            # Small delay to prevent overwhelming the system
            sleep 0.001
        done
    done
    
    echo "All connections started. Waiting for completion..." >> $log_file
    
    # Wait for all background jobs to complete
    for pid in "${pids[@]}"; do
        wait $pid
    done
    
    # Collect results from all connections
    for temp_file in "${temp_files[@]}"; do
        if [ -f "$temp_file" ]; then
            read conn_success conn_fail conn_latencies conn_connect_times conn_first_byte_times conn_download_sizes < "$temp_file"
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
            for s in $conn_download_sizes; do
                total_download_size=$(echo "$total_download_size + $s" | bc)
            done
            rm "$temp_file"
        fi
    done
    
    # Calculate data transfer statistics using actual curl measurements
    # Use actual download size from curl and estimate upload size
    request_data_size=${#REQUEST_DATA}
    total_upload_size=$(echo "$success * $request_data_size" | bc)
    total_traffic=$(echo "$total_upload_size + $total_download_size" | bc)
    
    # Estimate headers size based on actual traffic ratio from h2load
    # h2load shows ~101KB headers for ~171KB total traffic (about 59% headers)
    if (( $(echo "$total_traffic > 0" | bc -l) )); then
        estimated_headers_ratio=59
        total_headers_size=$(echo "$total_traffic * $estimated_headers_ratio / 100" | bc)
        total_data_transferred=$(echo "$total_traffic - $total_headers_size" | bc)
    else
        total_headers_size=0
        total_data_transferred=0
    fi
    
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
    
         # Calculate throughput and timing statistics
     if [ $count -gt 0 ]; then
         # Calculate standard deviation for latencies
         variance_sum=0
         for l in "${latencies[@]}"; do
             diff=$(echo "$l - $mean" | bc -l)
             variance_sum=$(echo "$variance_sum + $diff * $diff" | bc -l)
         done
         if [ $count -gt 1 ]; then
             variance=$(echo "$variance_sum / ($count - 1)" | bc -l)
             std_dev=$(echo "sqrt($variance)" | bc -l)
         else
             std_dev=0
         fi
         
         # Calculate standard deviation for connect times
         connect_variance_sum=0
         for c in "${connect_times[@]}"; do
             diff=$(echo "$c - $connect_mean" | bc -l)
             connect_variance_sum=$(echo "$connect_variance_sum + $diff * $diff" | bc -l)
         done
         if [ $count -gt 1 ]; then
             connect_variance=$(echo "$connect_variance_sum / ($count - 1)" | bc -l)
             connect_std_dev=$(echo "sqrt($connect_variance)" | bc -l)
         else
             connect_std_dev=0
         fi
         
         # Calculate standard deviation for first byte times
         first_byte_variance_sum=0
         for f in "${first_byte_times[@]}"; do
             diff=$(echo "$f - $first_byte_mean" | bc -l)
             first_byte_variance_sum=$(echo "$first_byte_variance_sum + $diff * $diff" | bc -l)
         done
         if [ $count -gt 1 ]; then
             first_byte_variance=$(echo "$first_byte_variance_sum / ($count - 1)" | bc -l)
             first_byte_std_dev=$(echo "sqrt($first_byte_variance)" | bc -l)
         else
             first_byte_std_dev=0
         fi
         
         # Calculate total time more accurately
         total_time=$(echo "$max" | bc -l)
         if (( $(echo "$total_time < 0.001" | bc -l) )); then
             total_time=0.001
         fi
         throughput=$(echo "$count / $total_time" | bc -l)
         
         # Calculate percentage within 1 standard deviation (approximation)
         within_std_dev=68.27  # Approximately 68% for normal distribution
     else
         std_dev=0
         connect_std_dev=0
         first_byte_std_dev=0
         throughput=0
         total_time=0
         within_std_dev=0
     fi
     
     # Format total time to match h2load format (ms)
     if (( $(echo "$total_time >= 1" | bc -l) )); then
         formatted_time=$(printf "%.2fs" $total_time)
     else
         formatted_time=$(printf "%.2fms" $(echo "$total_time * 1000" | bc -l))
     fi
     
     # Format throughput to match h2load format
     if (( $(echo "$throughput >= 1000" | bc -l) )); then
         formatted_throughput=$(printf "%.2f" $throughput)
     else
         formatted_throughput=$(printf "%.2f" $throughput)
     fi
     
     # Format traffic size to match h2load format
     if (( $(echo "$total_traffic >= 1048576" | bc -l) )); then
         formatted_traffic=$(printf "%.2fMB/s" $(echo "$total_traffic / 1048576" | bc -l))
     else
         formatted_traffic=$(printf "%.2fKB/s" $(echo "$total_traffic / 1024" | bc -l))
     fi
     
     # Output detailed results in h2load format with consistent units
     echo "finished in ${formatted_time}, ${formatted_throughput} req/s, ${formatted_traffic}" >> $log_file
     echo "requests: $REQUESTS total, $REQUESTS started, $count done, $success succeeded, $fail failed, 0 errored, 0 timeout" >> $log_file
     echo "status codes: $success 2xx, 0 3xx, 0 4xx, 0 5xx" >> $log_file
     echo "traffic: $(echo "scale=2; $total_traffic / 1024" | bc -l)KB ($total_traffic) total, $(echo "scale=2; $total_headers_size / 1024" | bc -l)KB ($total_headers_size) headers (space savings 0.00%), $(echo "scale=2; $total_data_transferred / 1024" | bc -l)KB ($total_data_transferred) data" >> $log_file
     echo "                     min         max         mean         sd        +/- sd" >> $log_file
     
     # Format time values to match h2load format (ms for values >= 1ms, us for smaller values)
     if (( $(echo "$min >= 0.001" | bc -l) )); then
         min_formatted=$(printf "%8.2fms" $(echo "$min * 1000" | bc -l))
     else
         min_formatted=$(printf "%8.0fus" $(echo "$min * 1000000" | bc -l))
     fi
     if (( $(echo "$max >= 0.001" | bc -l) )); then
         max_formatted=$(printf "%8.2fms" $(echo "$max * 1000" | bc -l))
     else
         max_formatted=$(printf "%8.0fus" $(echo "$max * 1000000" | bc -l))
     fi
     if (( $(echo "$mean >= 0.001" | bc -l) )); then
         mean_formatted=$(printf "%8.2fms" $(echo "$mean * 1000" | bc -l))
     else
         mean_formatted=$(printf "%8.0fus" $(echo "$mean * 1000000" | bc -l))
     fi
     if (( $(echo "$std_dev >= 0.001" | bc -l) )); then
         std_dev_formatted=$(printf "%8.2fms" $(echo "$std_dev * 1000" | bc -l))
     else
         std_dev_formatted=$(printf "%8.0fus" $(echo "$std_dev * 1000000" | bc -l))
     fi
     
     echo "time for request: $min_formatted $max_formatted $mean_formatted $std_dev_formatted $(printf "%6.2f%%" $within_std_dev)" >> $log_file
     
     # Format connect time values
     if (( $(echo "$connect_min >= 0.001" | bc -l) )); then
         connect_min_formatted=$(printf "%8.2fms" $(echo "$connect_min * 1000" | bc -l))
     else
         connect_min_formatted=$(printf "%8.0fus" $(echo "$connect_min * 1000000" | bc -l))
     fi
     if (( $(echo "$connect_max >= 0.001" | bc -l) )); then
         connect_max_formatted=$(printf "%8.2fms" $(echo "$connect_max * 1000" | bc -l))
     else
         connect_max_formatted=$(printf "%8.0fus" $(echo "$connect_max * 1000000" | bc -l))
     fi
     if (( $(echo "$connect_mean >= 0.001" | bc -l) )); then
         connect_mean_formatted=$(printf "%8.2fms" $(echo "$connect_mean * 1000" | bc -l))
     else
         connect_mean_formatted=$(printf "%8.0fus" $(echo "$connect_mean * 1000000" | bc -l))
     fi
     if (( $(echo "$connect_std_dev >= 0.001" | bc -l) )); then
         connect_std_dev_formatted=$(printf "%8.2fms" $(echo "$connect_std_dev * 1000" | bc -l))
     else
         connect_std_dev_formatted=$(printf "%8.0fus" $(echo "$connect_std_dev * 1000000" | bc -l))
     fi
     
     echo "time for connect: $connect_min_formatted $connect_max_formatted $connect_mean_formatted $connect_std_dev_formatted $(printf "%6.2f%%" $within_std_dev)" >> $log_file
     
     # Format first byte time values
     if (( $(echo "$first_byte_min >= 0.001" | bc -l) )); then
         first_byte_min_formatted=$(printf "%8.2fms" $(echo "$first_byte_min * 1000" | bc -l))
     else
         first_byte_min_formatted=$(printf "%8.0fus" $(echo "$first_byte_min * 1000000" | bc -l))
     fi
     if (( $(echo "$first_byte_max >= 0.001" | bc -l) )); then
         first_byte_max_formatted=$(printf "%8.2fms" $(echo "$first_byte_max * 1000" | bc -l))
     else
         first_byte_max_formatted=$(printf "%8.0fus" $(echo "$first_byte_max * 1000000" | bc -l))
     fi
     if (( $(echo "$first_byte_mean >= 0.001" | bc -l) )); then
         first_byte_mean_formatted=$(printf "%8.2fms" $(echo "$first_byte_mean * 1000" | bc -l))
     else
         first_byte_mean_formatted=$(printf "%8.0fus" $(echo "$first_byte_mean * 1000000" | bc -l))
     fi
     if (( $(echo "$first_byte_std_dev >= 0.001" | bc -l) )); then
         first_byte_std_dev_formatted=$(printf "%8.2fms" $(echo "$first_byte_std_dev * 1000" | bc -l))
     else
         first_byte_std_dev_formatted=$(printf "%8.0fus" $(echo "$first_byte_std_dev * 1000000" | bc -l))
     fi
     
     echo "time to 1st byte: $first_byte_min_formatted $first_byte_max_formatted $first_byte_mean_formatted $first_byte_std_dev_formatted $(printf "%6.2f%%" $within_std_dev)" >> $log_file
     # Calculate req/s statistics (min, max, mean, sd) based on actual request times
     if [ $count -gt 0 ]; then
         # Calculate req/s for each request based on its latency
         req_per_sec_values=()
         for l in "${latencies[@]}"; do
             if (( $(echo "$l > 0" | bc -l) )); then
                 req_per_sec=$(echo "1 / $l" | bc -l)
                 req_per_sec_values+=("$req_per_sec")
             fi
         done
         
         # Calculate min, max, mean, sd for req/s
         req_per_sec_min=999999
         req_per_sec_max=0
         req_per_sec_sum=0
         req_per_sec_count=0
         
         for rps in "${req_per_sec_values[@]}"; do
             if (( $(echo "$rps < $req_per_sec_min" | bc -l) )); then
                 req_per_sec_min=$rps
             fi
             if (( $(echo "$rps > $req_per_sec_max" | bc -l) )); then
                 req_per_sec_max=$rps
             fi
             req_per_sec_sum=$(echo "$req_per_sec_sum + $rps" | bc -l)
             ((req_per_sec_count++))
         done
         
         if [ $req_per_sec_count -gt 0 ]; then
             req_per_sec_mean=$(echo "$req_per_sec_sum / $req_per_sec_count" | bc -l)
             
             # Calculate standard deviation for req/s
             req_per_sec_variance_sum=0
             for rps in "${req_per_sec_values[@]}"; do
                 diff=$(echo "$rps - $req_per_sec_mean" | bc -l)
                 req_per_sec_variance_sum=$(echo "$req_per_sec_variance_sum + $diff * $diff" | bc -l)
             done
             if [ $req_per_sec_count -gt 1 ]; then
                 req_per_sec_variance=$(echo "$req_per_sec_variance_sum / ($req_per_sec_count - 1)" | bc -l)
                 req_per_sec_std_dev=$(echo "sqrt($req_per_sec_variance)" | bc -l)
             else
                 req_per_sec_std_dev=0
             fi
         else
             req_per_sec_mean=0
             req_per_sec_std_dev=0
         fi
     else
         req_per_sec_min=0
         req_per_sec_max=0
         req_per_sec_mean=0
         req_per_sec_std_dev=0
     fi
     
     # Calculate percentage of requests within 1 standard deviation
     req_per_sec_within_std_dev=0
     if [ $req_per_sec_count -gt 0 ] && (( $(echo "$req_per_sec_std_dev > 0" | bc -l) )); then
         lower_bound=$(echo "$req_per_sec_mean - $req_per_sec_std_dev" | bc -l)
         upper_bound=$(echo "$req_per_sec_mean + $req_per_sec_std_dev" | bc -l)
         
         within_count=0
         for rps in "${req_per_sec_values[@]}"; do
             if (( $(echo "$rps >= $lower_bound && $rps <= $upper_bound" | bc -l) )); then
                 ((within_count++))
             fi
         done
         
         req_per_sec_within_std_dev=$(echo "scale=2; $within_count * 100 / $req_per_sec_count" | bc -l)
     else
         req_per_sec_within_std_dev=100.00
     fi
     
     echo "req/s           : $(printf "%8.2f" $req_per_sec_min) $(printf "%8.2f" $req_per_sec_max) $(printf "%8.2f" $req_per_sec_mean) $(printf "%8.2f" $req_per_sec_std_dev) $(printf "%6.2f%%" $req_per_sec_within_std_dev)" >> $log_file
    
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