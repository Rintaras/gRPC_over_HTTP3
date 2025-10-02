#!/bin/bash

cd "$(dirname "$0")"

LATEST_LOG="logs/$(ls -t logs/ 2>/dev/null | head -1)"

if [ -z "$LATEST_LOG" ] || [ ! -d "$LATEST_LOG" ]; then
    echo "ベンチマーク実行中のログが見つかりません"
    exit 1
fi

echo "========================================="
echo "ベンチマーク進行状況モニター"
echo "========================================="
echo ""
echo "ログディレクトリ: $LATEST_LOG"
echo ""

while true; do
    clear
    echo "========================================="
    echo "ベンチマーク進行状況"
    echo "========================================="
    echo ""
    echo "時刻: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "ログ: $LATEST_LOG"
    echo ""
    
    if [ -f "$LATEST_LOG/benchmark_results.csv" ]; then
        LINES=$(($(wc -l < "$LATEST_LOG/benchmark_results.csv") - 1))
        PROGRESS=$(echo "scale=1; $LINES * 100 / 400" | bc)
        
        echo "データ行数: $LINES/400"
        echo "進捗: $PROGRESS%"
        echo ""
        
        BARS=$((LINES / 10))
        echo -n "["
        for i in $(seq 1 40); do
            if [ $i -le $BARS ]; then
                echo -n "="
            else
                echo -n " "
            fi
        done
        echo "] $PROGRESS%"
        
        echo ""
        echo "=== 最新10行 ==="
        tail -10 "$LATEST_LOG/benchmark_results.csv"
        
        if [ $LINES -ge 400 ]; then
            echo ""
            echo "✓ ベンチマーク完了！"
            
            if [ -f "$LATEST_LOG/response_time_comparison.png" ]; then
                echo "✓ グラフ生成完了"
                echo ""
                echo "結果を確認: ./view_results.sh"
            fi
            break
        fi
    else
        echo "CSV作成待ち..."
    fi
    
    sleep 5
done

