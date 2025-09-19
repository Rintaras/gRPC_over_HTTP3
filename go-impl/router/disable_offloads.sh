#!/bin/bash

# ネットワークオフロード機能を無効化するスクリプト
# LSO (Large Send Offload) と LRO (Large Receive Offload) を無効化
# これにより tc netem のパケットロス機能が正しく動作するようになる

INTERFACE=${1:-eth0}

echo "Disabling network offload features on interface: $INTERFACE"

# 現在のオフロード設定を表示
echo "Current offload settings:"
ethtool -k $INTERFACE | grep -E "(generic-segmentation-offload|large-receive-offload|generic-receive-offload|tcp-segmentation-offload)"

# オフロード機能を無効化
echo "Disabling offload features..."

# Generic Segmentation Offload (GSO) を無効化
ethtool -K $INTERFACE gso off

# Large Receive Offload (LRO) を無効化  
ethtool -K $INTERFACE lro off

# Generic Receive Offload (GRO) を無効化
ethtool -K $INTERFACE gro off

# TCP Segmentation Offload (TSO) を無効化
ethtool -K $INTERFACE tso off

# UDP Fragmentation Offload (UFO) を無効化
ethtool -K $INTERFACE ufo off

# 変更後の設定を確認
echo "Updated offload settings:"
ethtool -k $INTERFACE | grep -E "(generic-segmentation-offload|large-receive-offload|generic-receive-offload|tcp-segmentation-offload)"

echo "Network offload features disabled successfully"
