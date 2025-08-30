#!/bin/bash

# Test HTTP/3 timing measurement
echo "Testing HTTP/3 timing measurement..."

# Test single request with timing
request_start=$(date +%s%N | cut -b1-13)  # milliseconds
echo "Start time: ${request_start}ms"

# Simulate HTTP/3 request
sleep 0.1

request_end=$(date +%s%N | cut -b1-13)  # milliseconds
echo "End time: ${request_end}ms"

# Calculate request time
request_time=$((request_end - request_start))
echo "Request time: ${request_time}ms"
echo "Request time (microseconds): $((request_time * 1000))"

# Test CSV format
echo "$(date +%s),200,$((request_time * 1000))"






