#!/bin/bash
# HTTP/3 Connection Time Optimization Script
# Focuses on improving HTTP/3 connection establishment time

echo "================================================"
echo "HTTP/3 Connection Time Optimization"
echo "================================================"

# Configuration
SERVER_IP="172.30.0.2"
LOG_DIR="/logs/http3_optimization_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "Log directory: $LOG_DIR"

# Function to test connection time with different parameters
test_connection_time() {
    local protocol=$1
    local connections=$2
    local threads=$3
    local warmup_time=$4
    local test_name=$5
    local log_file="$LOG_DIR/${protocol}_${test_name}.log"
    
    echo "Testing $protocol with $connections connections, $threads threads, ${warmup_time}s warmup..."
    
    # Create temporary data file
    local temp_data_file=$(mktemp)
    echo "Hello from HTTP/3 optimization test" > "$temp_data_file"
    
    if [ "$protocol" = "http3" ]; then
        docker exec grpc-client h2load -n 1000 -c $connections -t $threads -m 50 \
            --connect-to $SERVER_IP:443 \
            --connection-active-timeout 60 \
            --connection-inactivity-timeout 60 \
            --header "User-Agent: HTTP3-Optimization-Test" \
            --data "$temp_data_file" \
            --alpn-list=h3,h2 \
            https://$SERVER_IP/echo > "$log_file" 2>&1
    else
        docker exec grpc-client h2load -n 1000 -c $connections -t $threads -m 50 \
            --connect-to $SERVER_IP:443 \
            --connection-active-timeout 60 \
            --connection-inactivity-timeout 60 \
            --header "User-Agent: HTTP2-Optimization-Test" \
            --data "$temp_data_file" \
            https://$SERVER_IP/echo > "$log_file" 2>&1
    fi
    
    # Extract connection time with improved parsing
    local connect_time=$(grep "time for connect" "$log_file" | tail -1 | awk '{print $4}' | sed 's/ms//')
    local ttfb=$(grep "time to 1st byte" "$log_file" | tail -1 | awk '{print $4}' | sed 's/ms//')
    local throughput=$(grep "finished in" "$log_file" | tail -1 | awk '{print $4}' | sed 's/,//')
    
    echo "$protocol,$test_name,$connections,$threads,$warmup_time,$connect_time,$ttfb,$throughput" >> "$LOG_DIR/optimization_results.csv"
    
    rm "$temp_data_file"
    echo "Results: Connect=${connect_time}ms, TTFB=${ttfb}ms, Throughput=$throughput"
}

# Test extreme network conditions where HTTP/3 might have advantage
test_extreme_conditions() {
    echo "Testing extreme network conditions..."
    
    # Test multiple extreme conditions
    local extreme_conditions=(
        "1000 30"   # 1s delay, 30% loss
        "2000 50"   # 2s delay, 50% loss
        "5000 70"   # 5s delay, 70% loss
        "10000 80"  # 10s delay, 80% loss
    )
    
    for condition in "${extreme_conditions[@]}"; do
        read -r delay loss <<< "$condition"
        echo "Testing with ${delay}ms delay, ${loss}% loss..."
        
        # Apply network conditions
        docker exec grpc-router tc qdisc del dev eth0 root 2>/dev/null || true
        docker exec grpc-router tc qdisc add dev eth0 root netem delay ${delay}ms loss ${loss}%
        
        sleep 5
        
        # Test with minimal connections to focus on connection time
        test_connection_time "http2" 1 1 5 "extreme_${delay}ms_${loss}pct"
        test_connection_time "http3" 1 1 5 "extreme_${delay}ms_${loss}pct"
        
        # Reset network conditions
        docker exec grpc-router tc qdisc del dev eth0 root 2>/dev/null || true
        sleep 2
    done
}

# Test connection reuse scenarios
test_connection_reuse() {
    echo "Testing connection reuse scenarios..."
    
    # Test with connection reuse
    test_connection_time "http2" 10 2 10 "connection_reuse"
    test_connection_time "http3" 10 2 10 "connection_reuse"
    
    # Test with 0-RTT focus
    test_connection_time "http2" 5 1 15 "0rtt_focus"
    test_connection_time "http3" 5 1 15 "0rtt_focus"
}

# Test different connection patterns
test_connection_patterns() {
    echo "Testing different connection patterns..."
    
    # Single connection test
    test_connection_time "http2" 1 1 5 "single_connection"
    test_connection_time "http3" 1 1 5 "single_connection"
    
    # Multiple connections test
    test_connection_time "http2" 20 4 10 "multiple_connections"
    test_connection_time "http3" 20 4 10 "multiple_connections"
}

# Initialize results file
echo "protocol,test_name,connections,threads,warmup_time,connect_time,ttfb,throughput" > "$LOG_DIR/optimization_results.csv"

# Run tests
test_extreme_conditions
test_connection_reuse
test_connection_patterns

echo "================================================"
echo "Optimization tests completed!"
echo "Results saved to: $LOG_DIR/optimization_results.csv"
echo "================================================"

# Generate summary
echo "=== CONNECTION TIME OPTIMIZATION SUMMARY ===" > "$LOG_DIR/summary.txt"
echo "Generated: $(date)" >> "$LOG_DIR/summary.txt"
echo "" >> "$LOG_DIR/summary.txt"

# Analyze results
if [ -f "$LOG_DIR/optimization_results.csv" ]; then
    echo "Connection Time Analysis:" >> "$LOG_DIR/summary.txt"
    tail -n +2 "$LOG_DIR/optimization_results.csv" | while IFS=',' read -r protocol test_name connections threads warmup_time connect_time ttfb throughput; do
        echo "  $protocol ($test_name): ${connect_time}ms connect, ${ttfb}ms TTFB" >> "$LOG_DIR/summary.txt"
    done
fi

echo "Summary saved to: $LOG_DIR/summary.txt"
cat "$LOG_DIR/summary.txt" 