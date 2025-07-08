#!/bin/bash
# Usage: netem_delay_loss_bandwidth.sh <delay_ms> <loss_pct> <bandwidth_mbps>
# 例: ./netem_delay_loss_bandwidth.sh 100 1 10

DEV=eth0
DELAY_MS=${1:-0}
LOSS_PCT=${2:-0}
BANDWIDTH_MBPS=${3:-0}

# 既存qdisc削除
tc qdisc del dev $DEV root 2>/dev/null

# netem + tbfで遅延・損失・帯域制限
if [ "$BANDWIDTH_MBPS" -gt 0 ]; then
  tc qdisc add dev $DEV root handle 1: netem delay ${DELAY_MS}ms loss ${LOSS_PCT}%
  # tbf: 帯域制限 (rate)、バースト、遅延バッファ
  tc qdisc add dev $DEV parent 1:1 handle 10: tbf rate ${BANDWIDTH_MBPS}mbit burst 32kbit latency 400ms
else
  tc qdisc add dev $DEV root netem delay ${DELAY_MS}ms loss ${LOSS_PCT}%
fi

tc qdisc show dev $DEV 