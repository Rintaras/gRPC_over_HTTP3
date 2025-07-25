#!/bin/bash

# Ultra Final Boundary Analysis Script
# 超最終的な境界値分析スクリプト

set -e

# 基本設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="logs/ultra_final_boundary_analysis_$(date +%Y%m%d_%H%M%S)"
SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"

# 開始時刻を記録
START_TIME=$(date +%s)

echo "================================================"
echo "超最終境界値分析"
echo "================================================"
echo "開始時刻: $(date)"
echo "ログディレクトリ: $LOG_DIR"
echo "================================================"

# ログディレクトリ作成
mkdir -p $LOG_DIR

# 超最終テストケース（大幅に緩和された条件）
declare -a ULTRA_TEST_CONDITIONS=(
    # 低遅延環境（細かい刻み）
    "0:0:0"      # 理想環境
    "5:0:0"      # 低遅延
    "10:0:0"     # 中低遅延
    "15:0:0"     # 中遅延
    "20:0:0"     # 中高遅延
    "25:0:0"     # 中高遅延
    "30:0:0"     # 中高遅延
    
    # 中遅延環境（損失付き）
    "40:0:0"     # 中遅延
    "50:1:0"     # 中遅延 + 低損失
    "70:1:0"     # 中高遅延 + 低損失
    "100:2:0"    # 高遅延 + 中損失
    
    # 高遅延環境（極端な条件）
    "150:3:0"    # 高遅延 + 高損失
    "200:5:0"    # 超高遅延 + 高損失
)

echo "超最終テスト条件:"
for condition in "${ULTRA_TEST_CONDITIONS[@]}"; do
    echo "  • $condition"
done
echo ""

# システム準備
echo "システム準備中..."
docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh 0 0 > /dev/null 2>&1
sleep 5

# 超最終境界値分析実行
echo "超最終境界値分析を開始..."
python3 scripts/ultra_final_analysis.py \
    --log_dir "$LOG_DIR" \
    --test_conditions "${ULTRA_TEST_CONDITIONS[@]}"

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
echo "超最終境界値分析完了: $(date)"
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
echo "次のステップ: 超最終レポートを確認してください"
echo "cat $LOG_DIR/ultra_final_boundary_report.txt" 