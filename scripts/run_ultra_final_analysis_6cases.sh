#!/bin/bash

# Ultra Final Boundary Analysis Script - 6 Cases Version
# 超最終的な境界値分析スクリプト - 6ケース版

set -e

# 基本設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="logs/ultra_final_boundary_analysis_6cases_$(date +%Y%m%d_%H%M%S)"
SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"

# 開始時刻を記録
START_TIME=$(date +%s)

echo "================================================"
echo "超最終境界値分析 (6ケース版)"
echo "================================================"
echo "開始時刻: $(date)"
echo "ログディレクトリ: $LOG_DIR"
echo "================================================"

# ログディレクトリ作成
mkdir -p $LOG_DIR

# 6ケースのテスト条件
echo "テスト条件 (6ケース):"
echo "  低遅延環境 (2ケース):"
echo "    • 0ms遅延, 0%損失, 0Mbps帯域 (理想環境)"
echo "    • 10ms遅延, 0%損失, 0Mbps帯域 (低遅延)"
echo ""
echo "  中遅延環境 (2ケース):"
echo "    • 30ms遅延, 1%損失, 0Mbps帯域 (中遅延 + 低損失)"
echo "    • 50ms遅延, 2%損失, 0Mbps帯域 (中高遅延 + 中損失)"
echo ""
echo "  高遅延環境 (2ケース):"
echo "    • 100ms遅延, 3%損失, 0Mbps帯域 (高遅延 + 高損失)"
echo "    • 200ms遅延, 5%損失, 0Mbps帯域 (超高遅延 + 超高損失)"
echo ""

# システム準備
echo "システム準備中..."
docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh 0 0 > /dev/null 2>&1
sleep 5

# 超最終境界値分析実行 (6ケース版)
echo "超最終境界値分析 (6ケース版) を開始..."
python3 scripts/ultra_final_analysis_6cases.py \
    --log_dir "$LOG_DIR"

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
echo "超最終境界値分析 (6ケース版) 完了: $(date)"
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
echo "cat $LOG_DIR/ultra_final_boundary_report_6cases.txt"
echo ""
echo "グラフファイル:"
echo "open $LOG_DIR/ultra_final_boundary_analysis_6cases.png" 