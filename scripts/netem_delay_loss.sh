#!/bin/bash

# Network emulation script for delay and loss
# Usage: ./netem_delay_loss.sh <delay_ms> <loss_percent>

if [ $# -ne 2 ]; then
    echo "Usage: $0 <delay_ms> <loss_percent>"
    echo "Example: $0 50 1"
    exit 1
fi

DELAY=$1
LOSS=$2

echo "Setting network conditions: ${DELAY}ms delay, ${LOSS}% loss"

# Remove existing qdisc
tc qdisc del dev eth0 root 2>/dev/null || true

# Add new qdisc with delay and loss
if [ $DELAY -gt 0 ] || [ $LOSS -gt 0 ]; then
    tc qdisc add dev eth0 root netem delay ${DELAY}ms loss ${LOSS}%
    echo "Network conditions applied successfully"
else
    echo "No network impairment applied (delay=0, loss=0)"
fi

# Show current qdisc
echo "Current qdisc configuration:"
tc qdisc show dev eth0 