#!/bin/bash

# Network emulation script for delay, loss, and bandwidth limitation
# Usage: ./netem_delay_loss_bandwidth.sh <delay_ms> <loss_percent> <bandwidth_mbps>
# Example: ./netem_delay_loss_bandwidth.sh 200 1 10

if [ $# -ne 3 ]; then
    echo "Usage: $0 <delay_ms> <loss_percent> <bandwidth_mbps>"
    echo "Example: $0 200 1 10"
    echo "This will set: ${1}ms delay, ${2}% loss, ${3}Mbps bandwidth limit"
    exit 1
fi

DELAY=$1
LOSS=$2
BANDWIDTH=$3

echo "Setting network conditions: ${DELAY}ms delay, ${LOSS}% loss, ${BANDWIDTH}Mbps bandwidth"

# Remove existing qdisc
tc qdisc del dev eth0 root 2>/dev/null || true

# Add new qdisc with delay, loss, and bandwidth limitation
if [ $DELAY -gt 0 ] || [ $LOSS -gt 0 ] || [ $BANDWIDTH -gt 0 ]; then
    # Use tbf (token bucket filter) for bandwidth limitation
    # and netem for delay and loss
    tc qdisc add dev eth0 root handle 1: tbf rate ${BANDWIDTH}mbit burst 32kbit latency 400ms
    tc qdisc add dev eth0 parent 1:1 handle 10: netem delay ${DELAY}ms loss ${LOSS}%
    echo "Network conditions applied successfully"
else
    echo "No network impairment applied"
fi

# Show current qdisc
echo "Current qdisc configuration:"
tc qdisc show dev eth0

# Show interface statistics
echo ""
echo "Interface statistics:"
tc -s qdisc show dev eth0 