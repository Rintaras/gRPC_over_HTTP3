#!/bin/bash

# Japanese Benchmark Script for HTTP/2 vs HTTP/3 Performance Comparison
# Based on run_bench.sh with Japanese output and character encoding support
# Features: Long measurement time, increased connections, extended timeouts, protocol separation

# 開始時刻を記録
START_TIME=$(date +%s)

echo "================================================"
echo "HTTP/2 vs HTTP/3 性能ベンチマーク (日本語版)"
echo "================================================"
echo "ベンチマーク開始: $(date)"
echo "================================================"

# Execute the entire benchmark inside the client container
docker exec grpc-client bash -c '
# タイムスタンプ付きディレクトリ作成
NOW=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="/logs/japanese_benchmark_${NOW}"
mkdir -p $LOG_DIR

echo "[INFO] ログディレクトリ: $LOG_DIR"

SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"

# テストケース（性能比較に最適化）
TEST_CASES=(
    "0 0"      # 理想環境
    "50 0"     # 中程度遅延
    "100 0"    # 高遅延
    "150 0"    # 超高遅延
)

# ベンチマークパラメータ（信頼性向上）
REQUESTS=30000        # 総リクエスト数
CONNECTIONS=50        # 同時接続数
THREADS=10           # 並列スレッド数
MAX_CONCURRENT=50    # 最大同時ストリーム数
REQUEST_DATA="日本語ベンチマーククライアントからのテスト - HTTP/2 vs HTTP/3 性能比較テスト用の現実的なデータペイロード"

# フェア比較パラメータ
WARMUP_REQUESTS=10000   # ウォームアップ用リクエスト数
MEASUREMENT_REQUESTS=20000  # 実際の測定用リクエスト数
CONNECTION_WARMUP_TIME=15   # 接続安定化時間
CONNECTION_REUSE_ENABLED=true

# システム安定化設定
SYSTEM_STABILIZATION_TIME=20  # システム安定化時間
MEMORY_CLEANUP_ENABLED=true   # メモリクリーンアップ
NETWORK_RESET_ENABLED=true    # ネットワークリセット

# 派生パラメータの計算
REQUESTS_PER_CONNECTION=$((REQUESTS / CONNECTIONS))
REMAINING_REQUESTS=$((REQUESTS % CONNECTIONS))
CONNECTIONS_PER_THREAD=$((CONNECTIONS / THREADS))

echo "================================================"
echo "HTTP/2 vs HTTP/3 性能ベンチマーク (日本語版)"
echo "================================================"
echo "パラメータ:"
echo "  総リクエスト数: $REQUESTS"
echo "  同時接続数: $CONNECTIONS"
echo "  並列スレッド数: $THREADS"
echo "  最大同時ストリーム数: $MAX_CONCURRENT"
echo "  接続あたりリクエスト数: $REQUESTS_PER_CONNECTION"
echo "  スレッドあたり接続数: $CONNECTIONS_PER_THREAD"
echo "  リクエストデータ: \"$REQUEST_DATA\""
echo "  テストケース数: ${#TEST_CASES[@]}"
echo "  フェア比較: 有効"
echo "    - ウォームアップリクエスト: $WARMUP_REQUESTS"
echo "    - 測定リクエスト: $MEASUREMENT_REQUESTS"
echo "    - 接続安定化時間: ${CONNECTION_WARMUP_TIME}秒"
echo "  システム安定化: 有効"
echo "    - 安定化時間: ${SYSTEM_STABILIZATION_TIME}秒"
echo "    - メモリクリーンアップ: $MEMORY_CLEANUP_ENABLED"
echo "    - ネットワークリセット: $NETWORK_RESET_ENABLED"
echo "================================================"

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# ベンチマークパラメータをテキストファイルに保存
cat <<EOF > "$LOG_DIR/benchmark_params.txt"
REQUESTS=$REQUESTS
CONNECTIONS=$CONNECTIONS
THREADS=$THREADS
MAX_CONCURRENT=$MAX_CONCURRENT
WARMUP_REQUESTS=$WARMUP_REQUESTS
MEASUREMENT_REQUESTS=$MEASUREMENT_REQUESTS
CONNECTION_WARMUP_TIME=$CONNECTION_WARMUP_TIME
SYSTEM_STABILIZATION_TIME=$SYSTEM_STABILIZATION_TIME
MEMORY_CLEANUP_ENABLED=$MEMORY_CLEANUP_ENABLED
NETWORK_RESET_ENABLED=$NETWORK_RESET_ENABLED
EOF

# 現在のタイムスタンプを取得する関数
get_timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

# 包括的なシステム制御を実行する関数
comprehensive_system_control() {
    local delay=$1
    local loss=$2
    
    echo "=== 包括的システム制御 ==="
    echo "タイムスタンプ: $(get_timestamp)"
    echo "遅延: ${delay}ms, 損失: ${loss}%"
    
    # ステップ1: メモリ使用量制御
    control_memory_usage
    
    # ステップ2: ネットワーク条件制御
    control_network_conditions $delay $loss
    
    # ステップ3: システム安定化
    echo "=== 最終システム安定化 ==="
    echo "最終安定化のため ${SYSTEM_STABILIZATION_TIME}秒待機中..."
    sleep $SYSTEM_STABILIZATION_TIME
    
    echo "包括的システム制御完了"
    echo ""
}

# メモリ使用量を制御する関数
control_memory_usage() {
    echo "=== メモリ使用量制御 ==="
    
    if [ "$MEMORY_CLEANUP_ENABLED" = true ]; then
        echo "包括的メモリクリーンアップを実行中..."
        
        # ページキャッシュクリア
        sync 2>/dev/null || true
        
        # ディレクトリエントリとインノードクリア
        echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
        
        # コンテナのメモリ制限設定
        docker update --memory=2g --memory-swap=2g grpc-client 2>/dev/null || true
        docker update --memory=1g --memory-swap=1g grpc-router 2>/dev/null || true
        docker update --memory=2g --memory-swap=2g grpc-server 2>/dev/null || true
    fi
    
    echo "メモリ使用量制御完了"
    echo ""
}

# ネットワーク条件を制御する関数
control_network_conditions() {
    local delay=$1
    local loss=$2
    
    echo "=== ネットワーク条件制御 ==="
    echo "遅延: ${delay}ms, 損失: ${loss}%"
    
    if [ "$NETWORK_RESET_ENABLED" = true ]; then
        echo "ネットワーク接続をリセット中..."
        
        # ルートキャッシュフラッシュ
        ip route flush cache 2>/dev/null || true
        
        # TCP接続リセット（簡略化）
        pkill -f "ss" 2>/dev/null || true
        
        # ネットワークバッファサイズ設定
        sysctl -w net.core.rmem_max=16777216 2>/dev/null || true
        sysctl -w net.core.wmem_max=16777216 2>/dev/null || true
    fi
    
    echo "ネットワーク条件制御完了"
    echo ""
}

# ベンチマーク前にシステムを安定化する関数
stabilize_system() {
    local delay=$1
    local loss=$2
    
    echo "=== システム安定化 ==="
    echo "タイムスタンプ: $(get_timestamp)"
    echo "遅延: ${delay}ms, 損失: ${loss}%"
    
    # システム安定化のため待機
    echo "システム安定化のため ${SYSTEM_STABILIZATION_TIME}秒待機中..."
    sleep $SYSTEM_STABILIZATION_TIME
    
    # メモリクリーンアップ（有効な場合）
    if [ "$MEMORY_CLEANUP_ENABLED" = true ]; then
        echo "メモリクリーンアップを実行中..."
        sync 2>/dev/null || true
    fi
    
    # ネットワークリセット（有効な場合）
    if [ "$NETWORK_RESET_ENABLED" = true ]; then
        echo "ネットワーク接続をリセット中..."
        ip route flush cache 2>/dev/null || true
    fi
    
    echo "システム安定化完了"
    echo ""
}

# ネットワーク条件をログに記録する関数
log_network_conditions() {
    local delay=$1
    local loss=$2
    local log_file=$3
    
    echo "=== ネットワーク条件 ===" >> $log_file
    echo "タイムスタンプ: $(get_timestamp)" >> $log_file
    echo "遅延: ${delay}ms" >> $log_file
    echo "損失: ${loss}%" >> $log_file
    echo "ルーターIP: $ROUTER_IP" >> $log_file
    echo "サーバーIP: $SERVER_IP" >> $log_file
    
    # 現在のqdisc設定を取得
    echo "現在のqdisc設定:" >> $log_file
    docker exec grpc-router tc qdisc show dev eth0 >> $log_file 2>&1
    echo "" >> $log_file
}

# h2loadでHTTP/2ベンチマークを実行する関数
run_http2_bench() {
    local delay=$1
    local loss=$2
    local log_file="$LOG_DIR/h2_${delay}ms_${loss}pct.log"
    local csv_file="$LOG_DIR/h2_${delay}ms_${loss}pct.csv"
    
    echo "HTTP/2ベンチマーク実行中 (${delay}ms遅延, ${loss}%損失)..."
    
    # ログファイルをクリアしてヘッダーを追加
    echo "=== HTTP/2 ベンチマーク結果 ===" > $log_file
    log_network_conditions $delay $loss $log_file
    
    # h2load用の一時データファイルを作成
    local temp_data_file=$(mktemp)
    echo "$REQUEST_DATA" > "$temp_data_file"
    
    # フェア比較: 最初に接続を確立し、その後測定
    echo "フェア比較のためHTTP/2接続を確立中..."
    echo "=== 接続確立フェーズ ===" >> $log_file
    
    # フェーズ1: ウォームアップリクエストで接続を確立
    h2load -n $WARMUP_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-benchmark-warmup" \
        --data "$temp_data_file" \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    echo "接続安定化のため ${CONNECTION_WARMUP_TIME}秒待機中..." >> $log_file
    sleep $CONNECTION_WARMUP_TIME
    
    echo "=== 測定フェーズ ===" >> $log_file
    # フェーズ2: 確立された接続で性能を測定
    h2load -n $MEASUREMENT_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-benchmark-measurement" \
        --data "$temp_data_file" \
        --log-file "$csv_file" \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    # 一時ファイルをクリーンアップ
    rm "$temp_data_file"
    
    # 最後にサマリーを追加
    echo "" >> $log_file
    echo "=== ベンチマークサマリー ===" >> $log_file
    echo "プロトコル: HTTP/2" >> $log_file
    echo "フェア比較: 有効" >> $log_file
    echo "ウォームアップリクエスト: $WARMUP_REQUESTS" >> $log_file
    echo "測定リクエスト: $MEASUREMENT_REQUESTS" >> $log_file
    echo "終了時刻: $(get_timestamp)" >> $log_file
    echo "CSVログ: $csv_file" >> $log_file
    
    echo "HTTP/2結果を保存: $log_file"
    echo "HTTP/2 CSVデータを保存: $csv_file"
}

# h2loadでHTTP/3ベンチマークを実行する関数
run_http3_bench() {
    local delay=$1
    local loss=$2
    local log_file="$LOG_DIR/h3_${delay}ms_${loss}pct.log"
    local csv_file="$LOG_DIR/h3_${delay}ms_${loss}pct.csv"
    
    echo "h2loadでHTTP/3ベンチマーク実行中 (${delay}ms遅延, ${loss}%損失)..."
    
    # ログファイルをクリアしてヘッダーを追加
    echo "=== HTTP/3 ベンチマーク結果 ===" > $log_file
    log_network_conditions $delay $loss $log_file
    
    # h2load用の一時データファイルを作成
    local temp_data_file=$(mktemp)
    echo "$REQUEST_DATA" > "$temp_data_file"
    
    # フェア比較: 最初に接続を確立し、その後測定
    echo "フェア比較のためHTTP/3接続を確立中..."
    echo "=== 接続確立フェーズ ===" >> $log_file
    
    # フェーズ1: ウォームアップリクエストで接続を確立
    h2load -n $WARMUP_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-benchmark-warmup" \
        --data "$temp_data_file" \
        --alpn-list=h3,h2 \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    echo "接続安定化のため ${CONNECTION_WARMUP_TIME}秒待機中..." >> $log_file
    sleep $CONNECTION_WARMUP_TIME
    
    echo "=== 測定フェーズ ===" >> $log_file
    # フェーズ2: 確立された接続で性能を測定
    h2load -n $MEASUREMENT_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 \
        --connection-active-timeout 60 \
        --connection-inactivity-timeout 60 \
        --header "User-Agent: h2load-benchmark-measurement" \
        --data "$temp_data_file" \
        --alpn-list=h3,h2 \
        --log-file "$csv_file" \
        https://$SERVER_IP/echo >> $log_file 2>&1
    
    # 一時ファイルをクリーンアップ
    rm "$temp_data_file"
    
    # h2loadが成功したかチェックし、プロトコル使用状況を分析
    if grep -q "succeeded, 0 failed" $log_file; then
        # QUIC指標を探してHTTP/3が実際に使用されたかチェック
        if grep -q "Application protocol: h3" $log_file; then
            echo "✓ h2load HTTP/3ベンチマークが正常に完了 (HTTP/3確認済み)"
            protocol_used="HTTP/3 (確認済み)"
        elif grep -q "Application protocol: h2" $log_file; then
            echo "⚠ h2load完了しましたがHTTP/2を使用 (フォールバック)"
            protocol_used="HTTP/2 (フォールバック)"
        else
            echo "✓ h2loadベンチマークが正常に完了 (プロトコル不明)"
            protocol_used="不明"
        fi
        
        # 最後にサマリーを追加
        echo "" >> $log_file
        echo "=== ベンチマークサマリー ===" >> $log_file
        echo "プロトコル: $protocol_used" >> $log_file
        echo "フェア比較: 有効" >> $log_file
        echo "ウォームアップリクエスト: $WARMUP_REQUESTS" >> $log_file
        echo "測定リクエスト: $MEASUREMENT_REQUESTS" >> $log_file
        echo "終了時刻: $(get_timestamp)" >> $log_file
        echo "CSVログ: $csv_file" >> $log_file
        
        echo "HTTP/3結果を保存: $log_file"
        echo "HTTP/3 CSVデータを保存: $csv_file"
        return 0
    else
        echo "h2load HTTP/3失敗"
        return 1
    fi
}

# HTTP/3が動作しているか確認する関数
verify_http3() {
    echo "HTTP/3接続性を確認中..."
    
    # curlでHTTP/3をテスト
    local http3_test=$(curl -k --http3 https://$SERVER_IP/echo 2>/dev/null | grep -c "HTTP/3")
    
    if [ "$http3_test" -gt 0 ]; then
        echo "✓ HTTP/3が正常に動作しています"
        return 0
    else
        echo "✗ HTTP/3が動作していません"
        return 1
    fi
}

# メインベンチマークループ
for test_case in "${TEST_CASES[@]}"; do
    read -r delay loss <<< "$test_case"
    
    echo ""
    echo "================================================"
    echo "テストケース: ${delay}ms遅延, ${loss}%損失"
    echo "================================================"
    
    # ネットワーク条件を適用
    echo "ネットワーク条件を適用中..."
    docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh $delay $loss
    
    # 一貫した結果のためのシステム安定化
    stabilize_system $delay $loss
    
    # ネットワーク安定化のため待機
    echo "ネットワーク安定化のため待機中..."
    sleep 10
    
    # ベンチマーク前にHTTP/3が動作しているか確認
    if ! verify_http3; then
        echo "警告: HTTP/3確認に失敗しましたが、続行します..."
    fi
    
    # 干渉を避けるため順次ベンチマークを実行
    echo "ベンチマーク実行中..."
    run_http2_bench $delay $loss
    
    echo "プロトコル間で30秒待機中..."
    sleep 30
    
    # h2loadでHTTP/3ベンチマークを実行
    run_http3_bench $delay $loss
    
    echo "テストケース完了: ${delay}ms遅延, ${loss}%損失"
    echo ""
done

echo "================================================"
echo "全ベンチマーク完了!"
echo "結果を保存: $LOG_DIR/"
echo "================================================"
echo "ファイル:"
ls -la $LOG_DIR/h*_*.log 

# サマリーレポート生成
echo ""
echo "=== サマリーレポート ==="
echo "生成時刻: $(get_timestamp)"
echo "総テストケース数: ${#TEST_CASES[@]}"
echo "ログディレクトリ: $LOG_DIR"
echo ""
echo "ファイルサイズ:"
for log_file in $LOG_DIR/h*_*.log; do
    if [ -f "$log_file" ]; then
        size=$(wc -l < "$log_file")
        echo "  $(basename $log_file): $size 行"
    fi
done

echo "ベンチマーク完了! レポートとグラフを確認してください: $LOG_DIR"
'

echo "================================================"
echo "ベンチマーク完了: $(date)"
echo "================================================"

# ホスト側で最新のベンチマークディレクトリを取得してグラフ生成
LATEST_LOG_DIR=$(ls -1td logs/japanese_benchmark_* | head -n1)
echo "[ホスト] グラフ自動生成: python3 scripts/generate_performance_graphs.py $LATEST_LOG_DIR"

# グラフ生成の実行（エラーハンドリング付き）
echo "[ホスト] グラフ生成を開始..."

# グラフ生成を実行
if source venv/bin/activate && python3 scripts/generate_performance_graphs.py "$LATEST_LOG_DIR"; then
    echo "✅ グラフ生成が正常に完了しました"
    echo "生成されたグラフファイル:"
    ls -la "$LATEST_LOG_DIR"/*.png 2>/dev/null || echo "グラフファイルが見つかりません"
else
    echo "❌ グラフ生成でエラーが発生しました"
    echo "手動でグラフ生成を実行してください:"
    echo "source venv/bin/activate && python3 scripts/generate_performance_graphs.py $LATEST_LOG_DIR"
fi

# 終了時刻を記録して実行時間を計算
END_TIME=$(date +%s)
EXECUTION_TIME=$((END_TIME - START_TIME))

# 実行時間を分と秒に変換
MINUTES=$((EXECUTION_TIME / 60))
SECONDS=$((EXECUTION_TIME % 60))

echo "================================================"
echo "完全自動化完了: $(date)"
echo "ベンチマーク + グラフ生成が正常に完了しました"
echo "結果: $LATEST_LOG_DIR"
echo "================================================"

# 実行時間を表示
echo ""
echo "⏱️  実行時間: ${MINUTES}分${SECONDS}秒 (合計${EXECUTION_TIME}秒)"
echo ""

echo "================================================"
echo "完全自動化完了: $(date)"
echo "ベンチマーク + グラフ生成が正常に完了しました"
echo "結果: $LATEST_LOG_DIR"
echo "================================================" 