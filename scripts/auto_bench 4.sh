#!/bin/bash

# Auto benchmark script - runs run_bench3.sh 5 times and averages the results
echo "================================================"
echo "Auto Benchmark Suite - 5x Execution with Averaging"
echo "================================================"
echo "開始時刻: $(date)"
echo "================================================"

# 実行回数
EXECUTION_COUNT=5
LOG_DIRS=()

# 5回ベンチマークを実行
for i in $(seq 1 $EXECUTION_COUNT); do
    echo ""
    echo "================================================"
    echo "実行 $i/$EXECUTION_COUNT"
    echo "================================================"
    
    # ベンチマーク実行
    ./scripts/run_bench3.sh
    
    # 最新のログディレクトリを取得
    LATEST_DIR=$(ls -1td logs/benchmark_* | head -n1)
    LOG_DIRS+=("$LATEST_DIR")
    
    echo "実行 $i 完了: $LATEST_DIR"
    echo "================================================"
done

echo ""
echo "================================================"
echo "全実行完了: $(date)"
echo "================================================"

# データ平均化とグラフ生成
echo "データ平均化とグラフ生成を開始..."

# Pythonスクリプトで平均化処理を実行
python3 scripts/average_benchmark_results.py "${LOG_DIRS[@]}"

echo "================================================"
echo "平均化処理完了: $(date)"
echo "================================================"

# 結果ディレクトリを表示
AVERAGE_DIR=$(ls -1td logs/average_benchmark_* | head -n1 2>/dev/null)
if [ -n "$AVERAGE_DIR" ]; then
    echo "平均化結果: $AVERAGE_DIR"
    echo "生成されたファイル:"
    ls -la "$AVERAGE_DIR"/*.png 2>/dev/null || echo "グラフファイルが見つかりません"
else
    echo "平均化結果ディレクトリが見つかりません"
fi

echo "================================================"
echo "Auto Benchmark Suite 完了: $(date)"
echo "================================================"