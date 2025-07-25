#!/bin/bash

# Performance Comparison Analysis Script
# performance_comparison_overview.pngのようなグラフを生成するスクリプト

set -e

# 基本設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="logs/performance_comparison_$(date +%Y%m%d_%H%M%S)"
SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"

# 開始時刻を記録
START_TIME=$(date +%s)

echo "================================================"
echo "HTTP/2 vs HTTP/3 性能比較分析"
echo "================================================"
echo "開始時刻: $(date)"
echo "ログディレクトリ: $LOG_DIR"
echo "================================================"

# ログディレクトリ作成
mkdir -p $LOG_DIR

# 性能比較テストケース（performance_comparison_overview.pngと同じ条件）
declare -a PERFORMANCE_TEST_CONDITIONS=(
    # 遅延条件（損失なし）
    "0:0:0"      # 理想環境
    "50:0:0"     # 中遅延
    "100:0:0"    # 高遅延
    "150:0:0"    # 超高遅延
)

echo "性能比較テスト条件:"
for condition in "${PERFORMANCE_TEST_CONDITIONS[@]}"; do
    echo "  • $condition"
done
echo ""

# システム準備
echo "システム準備中..."
docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh 0 0 > /dev/null 2>&1
sleep 5

# 性能比較分析実行
echo "性能比較分析を開始..."
python3 scripts/performance_comparison_analyzer.py \
    --log_dir "$LOG_DIR" \
    --test_conditions "${PERFORMANCE_TEST_CONDITIONS[@]}"

# ネットワーク条件リセット
echo ""
echo "ネットワーク条件をリセット中..."
docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh 0 0 > /dev/null 2>&1

# 終了時刻を記録して実行時間を計算
END_TIME=$(date +%s)
EXECUTION_TIME=$((END_TIME - START_TIME))

# 実行時間を分と秒に変換
MINUTES=$((EXECUTION_TIME / 60))
SECONDS=$((EXECUTION_TIME % 60))

echo ""
echo "================================================"
echo "性能比較分析完了: $(date)"
echo "結果保存先: $LOG_DIR"
echo "================================================"

# 実行時間を表示
echo ""
echo "⏱️  実行時間: ${MINUTES}分${SECONDS}秒 (合計${EXECUTION_TIME}秒)"
echo ""

# 結果ファイルの確認
echo "生成されたファイル:"
ls -la "$LOG_DIR"/*.png 2>/dev/null || echo "グラフファイルが見つかりません"
ls -la "$LOG_DIR"/*.txt 2>/dev/null || echo "レポートファイルが見つかりません"

echo ""
echo "次のステップ: 性能比較レポートを確認してください"
echo "cat $LOG_DIR/performance_comparison_report.txt"
echo ""
echo "グラフファイル: $LOG_DIR/performance_comparison_overview.png" 