#!/bin/bash

INTERFACE=${1:-eth0}

echo "トラフィックコントロール設定を削除中..."
echo "インターフェース: $INTERFACE"

tc qdisc del dev $INTERFACE root 2>/dev/null

echo "設定削除完了"
tc qdisc show dev $INTERFACE

