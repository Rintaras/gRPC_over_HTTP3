#!/bin/bash

echo "================================================"
echo "5回連続ベンチマーク実行スクリプト"
echo "================================================"

# 実行回数
TOTAL_RUNS=5

# ログディレクトリの作成
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SUMMARY_DIR="/Users/root1/Documents/Research/gRPC_over_HTTP3/go-impl/logs/benchmark_summary_${TIMESTAMP}"
mkdir -p "$SUMMARY_DIR"

echo "実行開始時刻: $(date)"
echo "総実行回数: $TOTAL_RUNS"
echo "サマリーディレクトリ: $SUMMARY_DIR"
echo ""

# 各実行の結果を保存する配列
declare -a RUN_RESULTS=()

# 5回実行
for i in $(seq 1 $TOTAL_RUNS); do
    echo "================================================"
    echo "実行回数: $i/$TOTAL_RUNS"
    echo "実行時刻: $(date)"
    echo "================================================"
    
    # ベンチマーク実行
    echo "ベンチマーク実行中..."
    cd /Users/root1/Documents/Research/gRPC_over_HTTP3/go-impl
    docker exec go-grpc-client ./latency_benchmark > "$SUMMARY_DIR/run_${i}_output.log" 2>&1
    
    # 実行結果の確認
    if [ $? -eq 0 ]; then
        echo "実行 $i: 成功"
        
        # 最新のログディレクトリを取得
        LATEST_LOG_DIR=$(ls -t /Users/root1/Documents/Research/gRPC_over_HTTP3/go-impl/logs/ | grep "latency_benchmark_" | head -1)
        LATEST_LOG_PATH="/Users/root1/Documents/Research/gRPC_over_HTTP3/go-impl/logs/$LATEST_LOG_DIR"
        
        # 結果ファイルをコピー
        if [ -d "$LATEST_LOG_PATH" ]; then
            cp "$LATEST_LOG_PATH/latency_results.json" "$SUMMARY_DIR/run_${i}_results.json"
            cp "$LATENCY_LOG_PATH/latency_results.csv" "$SUMMARY_DIR/run_${i}_results.csv"
            cp "$LATEST_LOG_PATH/latency_report.txt" "$SUMMARY_DIR/run_${i}_report.txt"
            cp "$LATEST_LOG_PATH/latency_comparison.png" "$SUMMARY_DIR/run_${i}_comparison.png"
            
            echo "結果ファイルをコピーしました: $SUMMARY_DIR/run_${i}_*"
        fi
        
        RUN_RESULTS+=("成功")
    else
        echo "実行 $i: 失敗"
        RUN_RESULTS+=("失敗")
    fi
    
    echo ""
    
    # 最後の実行でなければ待機
    if [ $i -lt $TOTAL_RUNS ]; then
        echo "次の実行まで30秒待機..."
        sleep 30
        echo ""
    fi
done

echo "================================================"
echo "全実行完了"
echo "完了時刻: $(date)"
echo "================================================"

# 実行結果サマリー
echo ""
echo "実行結果サマリー:"
echo "成功: $(echo "${RUN_RESULTS[@]}" | tr ' ' '\n' | grep -c "成功")"
echo "失敗: $(echo "${RUN_RESULTS[@]}" | tr ' ' '\n' | grep -c "失敗")"
echo ""

# 結果分析スクリプトを実行
echo "結果分析を実行中..."
cd /Users/root1/Documents/Research/gRPC_over_HTTP3/go-impl
go run -tags tools ./scripts/analyze_multiple_results.go "$SUMMARY_DIR" > "$SUMMARY_DIR/analysis_summary.txt" 2>&1

echo "分析結果: $SUMMARY_DIR/analysis_summary.txt"
echo "================================================"
echo "5回連続ベンチマーク実行完了"
echo "================================================"
