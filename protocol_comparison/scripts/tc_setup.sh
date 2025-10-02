#!/bin/bash

INTERFACE=${1:-eth0}
BANDWIDTH=${2:-1mbit}
LATENCY=${3:-0ms}
LOSS=${4:-0%}

echo "トラフィックコントロール設定を適用中..."
echo "インターフェース: $INTERFACE"
echo "帯域制限: $BANDWIDTH"
echo "遅延: $LATENCY"
echo "パケット損失: $LOSS"

tc qdisc del dev $INTERFACE root 2>/dev/null

tc qdisc add dev $INTERFACE root handle 1: htb default 10
tc class add dev $INTERFACE parent 1: classid 1:10 htb rate $BANDWIDTH

if [ "$LATENCY" != "0ms" ] || [ "$LOSS" != "0%" ]; then
    tc qdisc add dev $INTERFACE parent 1:10 handle 10: netem delay $LATENCY loss $LOSS
fi

echo "設定完了"
tc qdisc show dev $INTERFACE

