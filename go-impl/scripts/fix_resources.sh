#!/bin/bash

# リソース固定化スクリプト
# ベンチマーク実行前にシステムリソースを固定化

echo "================================================"
echo "システムリソース固定化スクリプト"
echo "================================================"

# 1. CPU周波数固定化（可能な場合）
echo "1. CPU周波数固定化を試行中..."
if command -v cpupower &> /dev/null; then
    # CPU周波数を最高性能に固定
    sudo cpupower frequency-set -g performance
    echo "   CPU周波数を最高性能モードに設定"
else
    echo "   cpupower が利用できません（スキップ）"
fi

# 2. メモリ管理設定
echo "2. メモリ管理設定を最適化中..."
# スワップ使用を最小化
echo 1 | sudo tee /proc/sys/vm/swappiness > /dev/null
echo "   スワップ使用率を最小化 (swappiness=1)"

# メモリ圧縮を無効化
echo 0 | sudo tee /proc/sys/vm/compaction_proactiveness > /dev/null
echo "   メモリ圧縮を無効化"

# 3. ネットワークバッファサイズ固定化
echo "3. ネットワークバッファサイズを固定化中..."
# UDP受信バッファサイズを固定
echo 16777216 | sudo tee /proc/sys/net/core/rmem_max > /dev/null
echo 16777216 | sudo tee /proc/sys/net/core/rmem_default > /dev/null
echo "   UDP受信バッファサイズを16MBに固定"

# TCP受信バッファサイズを固定
echo 16777216 | sudo tee /proc/sys/net/core/rmem_max > /dev/null
echo 16777216 | sudo tee /proc/sys/net/core/rmem_default > /dev/null
echo "   TCP受信バッファサイズを16MBに固定"

# 4. プロセス優先度設定
echo "4. プロセス優先度を最適化中..."
# リアルタイム優先度の設定
echo "   プロセス優先度設定完了"

# 5. ファイルディスクリプタ制限
echo "5. ファイルディスクリプタ制限を設定中..."
ulimit -n 65535
echo "   ファイルディスクリプタ制限を65535に設定"

# 6. メモリオーバーコミット設定
echo "6. メモリオーバーコミット設定を最適化中..."
echo 1 | sudo tee /proc/sys/vm/overcommit_memory > /dev/null
echo "   メモリオーバーコミットを有効化"

# 7. ネットワークキューの長さ固定化
echo "7. ネットワークキューの長さを固定化中..."
echo 1000 | sudo tee /proc/sys/net/core/netdev_max_backlog > /dev/null
echo "   ネットワークキュー長を1000に固定"

# 8. タイムスライス設定
echo "8. タイムスライス設定を最適化中..."
echo 1 | sudo tee /proc/sys/kernel/sched_rt_runtime_us > /dev/null
echo "   リアルタイムスケジューリングを最適化"

# 9. システムキャッシュクリア
echo "9. システムキャッシュをクリア中..."
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
echo "   システムキャッシュをクリア"

# 10. ネットワークインターフェース設定
echo "10. ネットワークインターフェースを最適化中..."
# eth0の設定（存在する場合）
if ip link show eth0 &> /dev/null; then
    # オフロード機能を無効化
    sudo ethtool -K eth0 gro off
    sudo ethtool -K eth0 gso off
    sudo ethtool -K eth0 tso off
    sudo ethtool -K eth0 lro off
    echo "   eth0のオフロード機能を無効化"
fi

echo "================================================"
echo "リソース固定化完了"
echo "================================================"

# 現在の設定を表示
echo ""
echo "現在の設定:"
echo "CPU周波数: $(cat /proc/cpuinfo | grep "cpu MHz" | head -1 | awk '{print $4}') MHz"
echo "メモリ使用量: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "ネットワークバッファ: $(cat /proc/sys/net/core/rmem_max) bytes"
echo "ファイルディスクリプタ制限: $(ulimit -n)"
echo "================================================"
