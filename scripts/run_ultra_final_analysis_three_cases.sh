#!/bin/bash

# Ultra Final Analysis for Three Network Cases
# 低遅延、中遅延、高遅延環境での超最終分析

set -e

# 基本設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_LOG_DIR="logs/ultra_final_three_cases_$(date +%Y%m%d_%H%M%S)"
SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"

# 開始時刻を記録
START_TIME=$(date +%s)

echo "================================================"
echo "超最終分析 - 3つのネットワーク環境"
echo "================================================"
echo "開始時刻: $(date)"
echo "ログディレクトリ: $BASE_LOG_DIR"
echo "================================================"

# ログディレクトリ作成
mkdir -p $BASE_LOG_DIR

# 3つのネットワーク環境の定義
NETWORK_CASES=(
    "low_latency:10:0:0"      # 低遅延環境: 10ms遅延, 0%損失
    "medium_latency:100:2:0"   # 中遅延環境: 100ms遅延, 2%損失
    "high_latency:200:5:0"     # 高遅延環境: 200ms遅延, 5%損失
)

# 実験回数
EXPERIMENT_COUNT=3

# 各ケースで3回実験を実行
for case_info in "${NETWORK_CASES[@]}"; do
    IFS=':' read -r case_name delay loss bandwidth <<< "$case_info"
    
    echo ""
    echo "================================================"
    echo "ケース: $case_name"
    echo "条件: ${delay}ms遅延, ${loss}%損失, ${bandwidth}Mbps帯域"
    echo "================================================"
    
    # ケース専用ディレクトリ作成
    CASE_LOG_DIR="$BASE_LOG_DIR/${case_name}"
    mkdir -p $CASE_LOG_DIR
    
    # 3回の実験を実行
    for experiment in $(seq 1 $EXPERIMENT_COUNT); do
        echo ""
        echo "実験 $experiment/$EXPERIMENT_COUNT 開始..."
        
        # 実験用ディレクトリ作成
        EXP_LOG_DIR="$CASE_LOG_DIR/experiment_${experiment}"
        mkdir -p $EXP_LOG_DIR
        
        echo "ネットワーク条件: ${delay}ms遅延, ${loss}%損失, ${bandwidth}Mbps帯域"
        
        # システム準備
        echo "システム準備中..."
        docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh $delay $loss $bandwidth > /dev/null 2>&1
        sleep 5
        
        # 超最終境界値分析実行
        echo "超最終境界値分析を開始..."
        echo "測定回数分のディレクトリが自動生成されます..."
        python3 scripts/ultra_final_analysis.py \
            --log_dir "$EXP_LOG_DIR" \
            --test_conditions "${delay}:${loss}:${bandwidth}"
        
        echo "実験 $experiment/$EXPERIMENT_COUNT 完了"
        echo "結果保存先: $EXP_LOG_DIR"
        echo "測定ディレクトリ: $EXP_LOG_DIR/measurement_1, measurement_2"
        
        # 実験間隔
        if [ $experiment -lt $EXPERIMENT_COUNT ]; then
            echo "次の実験まで10秒待機..."
            sleep 10  # 30秒から10秒に短縮
        fi
    done
    
    echo ""
    echo "ケース $case_name の全実験完了"
    echo "結果ディレクトリ: $CASE_LOG_DIR"
done

# ネットワーク条件リセット
echo ""
echo "ネットワーク条件をリセット中..."
docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh 0 0 > /dev/null 2>&1

# 平均化処理
echo ""
echo "================================================"
echo "平均化処理開始"
echo "================================================"

# 各ケースの結果を平均化
for case_info in "${NETWORK_CASES[@]}"; do
    IFS=':' read -r case_name delay loss bandwidth <<< "$case_info"
    
    echo ""
    echo "ケース $case_name の平均化処理..."
    
    CASE_LOG_DIR="$BASE_LOG_DIR/${case_name}"
    
    # 実験ディレクトリのリストを作成
    experiment_dirs=()
    for i in $(seq 1 $EXPERIMENT_COUNT); do
        experiment_dirs+=("$CASE_LOG_DIR/experiment_$i")
    done
    
    # 平均化スクリプトを実行
    python3 scripts/average_benchmark_results.py \
        "${experiment_dirs[@]}" \
        --output_dir "$CASE_LOG_DIR/averaged"
    
    echo "ケース $case_name の平均化完了"
done

# 全ケースの統合グラフ生成
echo ""
echo "================================================"
echo "統合グラフ生成"
echo "================================================"

# 統合データディレクトリ作成
INTEGRATED_DIR="$BASE_LOG_DIR/integrated"
mkdir -p $INTEGRATED_DIR

# 各ケースの平均化結果を統合
echo "統合データを作成中..."
python3 scripts/generate_performance_graphs.py \
    --log_dir "$INTEGRATED_DIR" \
    --integrate_cases \
    --case_dirs "$BASE_LOG_DIR/low_latency/averaged" "$BASE_LOG_DIR/medium_latency/averaged" "$BASE_LOG_DIR/high_latency/averaged"

# 終了時刻を記録して実行時間を計算
END_TIME=$(date +%s)
EXECUTION_TIME=$((END_TIME - START_TIME))

# 実行時間を分と秒に変換
MINUTES=$((EXECUTION_TIME / 60))
SECONDS=$((EXECUTION_TIME % 60))

echo ""
echo "================================================"
echo "超最終分析 - 3つのネットワーク環境 完了: $(date)"
echo "結果保存先: $BASE_LOG_DIR"
echo "================================================"

# 実行時間を表示
echo ""
echo "⏱️  実行時間: ${MINUTES}分${SECONDS}秒 (合計${EXECUTION_TIME}秒)"
echo ""

# 結果ファイルの確認
echo "生成されたファイル:"
echo ""
echo "📊 統合グラフ:"
ls -la "$INTEGRATED_DIR"/*.png 2>/dev/null || echo "統合グラフファイルが見つかりません"

echo ""
echo "📁 各ケースの結果:"
for case_info in "${NETWORK_CASES[@]}"; do
    IFS=':' read -r case_name delay loss bandwidth <<< "$case_info"
    CASE_LOG_DIR="$BASE_LOG_DIR/${case_name}"
    echo "  • $case_name: $CASE_LOG_DIR"
    ls -la "$CASE_LOG_DIR/averaged"/*.png 2>/dev/null || echo "    グラフファイルが見つかりません"
done

echo ""
echo "🎯 次のステップ:"
echo "1. 統合グラフを確認: $INTEGRATED_DIR/performance_comparison_overview.png"
echo "2. 各ケースの詳細結果を確認:"
for case_info in "${NETWORK_CASES[@]}"; do
    IFS=':' read -r case_name delay loss bandwidth <<< "$case_info"
    CASE_LOG_DIR="$BASE_LOG_DIR/${case_name}"
    echo "   • $case_name: $CASE_LOG_DIR/averaged/"
done

echo ""
echo "📈 グラフ確認コマンド:"
echo "open $INTEGRATED_DIR/performance_comparison_overview.png" 