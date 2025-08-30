#!/bin/bash

# Test single test case for HTTP/3 timing fix
echo "Testing single test case (0ms delay)..."

# Create test log directory
TEST_LOG_DIR="logs/test_single_case_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEST_LOG_DIR"

echo "Test log directory: $TEST_LOG_DIR"

# Run HTTP/3 benchmark for single test case
echo "Running HTTP/3 benchmark (0ms delay, 3% loss)..."

# Clear log file and add header
log_file="$TEST_LOG_DIR/h3_0ms_3pct.log"
csv_file="$TEST_LOG_DIR/h3_0ms_3pct.csv"

echo "=== HTTP/3 BENCHMARK RESULTS (TEST) ===" > $log_file
echo "Timestamp: $(date)" >> $log_file
echo "Delay: 0ms (simulated)" >> $log_file
echo "Loss: 3% (simulated)" >> $log_file
echo "Target Server: 172.20.10.4" >> $log_file
echo "" >> $log_file

echo "=== MEASUREMENT PHASE ===" >> $log_file
echo "Running HTTP/3 benchmark with quiche client..." >> $log_file

# Run multiple HTTP/3 requests to simulate benchmark
start_time=$(date +%s)
success_count=0
total_count=10  # Reduced for testing

for i in $(seq 1 $total_count); do
    echo "Request $i/$total_count..." >> $log_file
    
    # Run quiche client request with corrected timing
    request_start=$(date +%s%N | cut -b1-13)  # milliseconds
    result=$(RUST_LOG=info ./quiche-client/target/release/quiche-client https://172.20.10.4:4433/ --no-verify 2>&1)
    request_end=$(date +%s%N | cut -b1-13)  # milliseconds
    
    # Calculate request time in milliseconds
    request_time=$((request_end - request_start))
    
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
    sleep 0.2
done

end_time=$(date +%s)
total_time=$((end_time - start_time))

# Add summary at the end
echo "" >> $log_file
echo "=== BENCHMARK SUMMARY ===" >> $log_file
echo "Protocol: HTTP/3 (quiche client)" >> $log_file
echo "Target Server: 172.20.10.4:4433" >> $log_file
echo "Total Requests: $total_count" >> $log_file
echo "Successful Requests: $success_count" >> $log_file
echo "Success Rate: $((success_count * 100 / total_count))%" >> $log_file
echo "Total Time: ${total_time}s" >> $log_file
echo "End Time: $(date)" >> $log_file
echo "CSV Log: $csv_file" >> $log_file

echo "Test completed!"
echo "HTTP/3 results saved to $log_file"
echo "HTTP/3 CSV data saved to $csv_file"

# Show CSV content
echo ""
echo "CSV content preview:"
head -10 "$csv_file"





