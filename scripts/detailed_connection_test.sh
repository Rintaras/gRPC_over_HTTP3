#!/bin/bash

# Detailed connection time measurement for HTTP/2 vs HTTP/3
# Focuses on actual connection establishment time, not total request time

echo "================================================"
echo "Detailed Connection Time Measurement"
echo "================================================"

SERVER_IP="172.30.0.2"
LOG_DIR="/logs/detailed_conn_test_$(date +%Y%m%d_%H%M%S)"
mkdir -p $LOG_DIR

echo "Test directory: $LOG_DIR"

# Function to measure detailed connection times
measure_connection_time() {
    local protocol=$1
    local test_name=$2
    local log_file="$LOG_DIR/${protocol}_${test_name}_detailed.log"
    
    echo "Measuring $protocol $test_name connection time..."
    
    # Clear any existing connections
    docker exec grpc-client sh -c 'rm -rf /tmp/.h2load* 2>/dev/null || true'
    
    # Measure with curl's detailed timing
    if [ "$protocol" = "http3" ]; then
        docker exec grpc-client curl -sk --http3 \
            -w "Protocol: HTTP/3\nConnect: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\nDNS: %{time_namelookup}s\nTLS: %{time_appconnect}s\nRedirect: %{time_redirect}s\n" \
            --connect-timeout 10 \
            https://$SERVER_IP/echo > /dev/null 2>"$log_file"
    else
        docker exec grpc-client curl -sk \
            -w "Protocol: HTTP/2\nConnect: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\nDNS: %{time_namelookup}s\nTLS: %{time_appconnect}s\nRedirect: %{time_redirect}s\n" \
            --connect-timeout 10 \
            https://$SERVER_IP/echo > /dev/null 2>"$log_file"
    fi
    
    echo "Results saved to: $log_file"
}

# Function to test with different connection scenarios
test_connection_scenarios() {
    echo "Testing different connection scenarios..."
    
    # 1. Fresh connection (no session reuse)
    echo "1. Fresh connection test..."
    measure_connection_time "http2" "fresh"
    measure_connection_time "http3" "fresh"
    
    # 2. Session reuse test
    echo "2. Session reuse test..."
    # First connection to establish session
    docker exec grpc-client curl -sk --http3 https://$SERVER_IP/echo > /dev/null 2>/dev/null
    docker exec grpc-client curl -sk https://$SERVER_IP/echo > /dev/null 2>/dev/null
    
    # Second connection (should reuse session)
    measure_connection_time "http2" "reuse"
    measure_connection_time "http3" "reuse"
    
    # 3. Multiple rapid connections
    echo "3. Multiple rapid connections test..."
    for i in {1..5}; do
        echo "  Connection $i:"
        measure_connection_time "http2" "rapid_$i"
        measure_connection_time "http3" "rapid_$i"
        sleep 1
    done
}

# Function to analyze results
analyze_results() {
    echo "================================================"
    echo "Connection Time Analysis"
    echo "================================================"
    
    echo "HTTP/2 Results:"
    for file in $LOG_DIR/http2_*.log; do
        if [ -f "$file" ]; then
            echo "  $(basename $file):"
            cat "$file"
            echo ""
        fi
    done
    
    echo "HTTP/3 Results:"
    for file in $LOG_DIR/http3_*.log; do
        if [ -f "$file" ]; then
            echo "  $(basename $file):"
            cat "$file"
            echo ""
        fi
    done
    
    # Calculate averages
    echo "Average Connection Times:"
    echo "HTTP/2 Connect Time: $(grep 'Connect:' $LOG_DIR/http2_*.log | awk '{sum+=$2} END {print sum/NR}')s"
    echo "HTTP/3 Connect Time: $(grep 'Connect:' $LOG_DIR/http3_*.log | awk '{sum+=$2} END {print sum/NR}')s"
    echo "HTTP/2 TLS Time: $(grep 'TLS:' $LOG_DIR/http2_*.log | awk '{sum+=$2} END {print sum/NR}')s"
    echo "HTTP/3 TLS Time: $(grep 'TLS:' $LOG_DIR/http3_*.log | awk '{sum+=$2} END {print sum/NR}')s"
}

# Run tests
test_connection_scenarios

# Analyze results
analyze_results

echo "================================================"
echo "Test completed. Results in: $LOG_DIR"
echo "================================================" 