#!/bin/bash

# Raspberry Pi 5 クイックベンチマークスクリプト
# 構築されたサーバーの簡単な性能テスト

echo "================================================"
echo "Raspberry Pi 5 クイックベンチマーク"
echo "================================================"
echo "ベンチマーク開始: $(date)"
echo "================================================"

# 設定
RASPBERRY_PI_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"
CLIENT_CONTAINER="grpc-client"
ROUTER_CONTAINER="grpc-router"

# ログディレクトリ作成
NOW=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs/quick_benchmark_${NOW}"
mkdir -p $LOG_DIR

echo "[INFO] ログディレクトリ: $LOG_DIR"

# ベンチマークパラメータ（軽量版）
REQUESTS=5000        # 軽量版リクエスト数
CONNECTIONS=20       # 接続数
THREADS=4           # スレッド数
MAX_CONCURRENT=20   # 最大同時ストリーム数

# テストケース（軽量版）
TEST_CASES=(
    "0 0"      # 0ms delay, 0% loss
    "50 1"     # 50ms delay, 1% loss
    "100 2"    # 100ms delay, 2% loss
)

echo "================================================"
echo "ベンチマークパラメータ:"
echo "  Raspberry Pi IP: $RASPBERRY_PI_IP"
echo "  リクエスト数: $REQUESTS"
echo "  接続数: $CONNECTIONS"
echo "  スレッド数: $THREADS"
echo "  テストケース: ${#TEST_CASES[@]}"
echo "================================================"

# 関数: ネットワーク条件設定
apply_network_conditions() {
    local delay=$1
    local loss=$2
    
    echo "ネットワーク条件設定: ${delay}ms delay, ${loss}% loss"
    docker exec $ROUTER_CONTAINER /scripts/netem_delay_loss_bandwidth.sh $delay $loss
    
    # ネットワーク安定化待機
    echo "ネットワーク安定化待機中..."
    sleep 5
}

# 関数: HTTP/2ベンチマーク実行
run_http2_benchmark() {
    local delay=$1
    local loss=$2
    local log_file="$LOG_DIR/h2_${delay}ms_${loss}pct.log"
    
    echo "HTTP/2ベンチマーク実行 (${delay}ms delay, ${loss}% loss)..."
    
    # ベンチマーク実行
    docker exec $CLIENT_CONTAINER h2load -n $REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $RASPBERRY_PI_IP:443 \
        --insecure \
        https://$RASPBERRY_PI_IP/health > $log_file 2>&1
    
    # 結果確認
    if grep -q "succeeded, 0 failed" $log_file; then
        echo "✅ HTTP/2ベンチマーク: SUCCESS"
        
        # パフォーマンス情報抽出
        local req_per_sec=$(grep "finished in" $log_file | grep -o '[0-9.]* req/s' | head -1)
        local total_time=$(grep "finished in" $log_file | grep -o '[0-9.]*s' | head -1)
        echo "   リクエスト/秒: $req_per_sec"
        echo "   総時間: $total_time"
    else
        echo "❌ HTTP/2ベンチマーク: FAILED"
    fi
    
    echo ""
}

# 関数: HTTP/3ベンチマーク実行
run_http3_benchmark() {
    local delay=$1
    local loss=$2
    local log_file="$LOG_DIR/h3_${delay}ms_${loss}pct.log"
    
    echo "HTTP/3ベンチマーク実行 (${delay}ms delay, ${loss}% loss)..."
    
    # ベンチマーク実行
    docker exec $CLIENT_CONTAINER h2load -n $REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $RASPBERRY_PI_IP:443 \
        --alpn-list=h3,h2 \
        --insecure \
        https://$RASPBERRY_PI_IP/health > $log_file 2>&1
    
    # 結果確認
    if grep -q "succeeded, 0 failed" $log_file; then
        echo "✅ HTTP/3ベンチマーク: SUCCESS"
        
        # パフォーマンス情報抽出
        local req_per_sec=$(grep "finished in" $log_file | grep -o '[0-9.]* req/s' | head -1)
        local total_time=$(grep "finished in" $log_file | grep -o '[0-9.]*s' | head -1)
        echo "   リクエスト/秒: $req_per_sec"
        echo "   総時間: $total_time"
    else
        echo "⚠️  HTTP/3ベンチマーク: NOT SUPPORTED"
    fi
    
    echo ""
}

# 関数: 結果サマリー生成
generate_summary() {
    echo "=== 結果サマリー生成 ==="
    
    local summary_file="$LOG_DIR/quick_benchmark_summary.txt"
    
    echo "Raspberry Pi 5 クイックベンチマーク結果" > $summary_file
    echo "=======================================" >> $summary_file
    echo "ベンチマーク日時: $(date '+%Y-%m-%d %H:%M:%S')" >> $summary_file
    echo "対象サーバー: $RASPBERRY_PI_IP" >> $summary_file
    echo "リクエスト数: $REQUESTS" >> $summary_file
    echo "接続数: $CONNECTIONS" >> $summary_file
    echo "スレッド数: $THREADS" >> $summary_file
    echo "" >> $summary_file
    
    # 各テストケースの結果
    for test_case in "${TEST_CASES[@]}"; do
        read -r delay loss <<< "$test_case"
        
        echo "テストケース: ${delay}ms delay, ${loss}% loss" >> $summary_file
        echo "----------------------------------------" >> $summary_file
        
        # HTTP/2結果
        local h2_log="$LOG_DIR/h2_${delay}ms_${loss}pct.log"
        if [ -f "$h2_log" ] && grep -q "succeeded, 0 failed" "$h2_log"; then
            local h2_req_per_sec=$(grep "finished in" "$h2_log" | grep -o '[0-9.]* req/s' | head -1)
            local h2_total_time=$(grep "finished in" "$h2_log" | grep -o '[0-9.]*s' | head -1)
            echo "  HTTP/2: ✅ SUCCESS" >> $summary_file
            echo "    リクエスト/秒: $h2_req_per_sec" >> $summary_file
            echo "    総時間: $h2_total_time" >> $summary_file
        else
            echo "  HTTP/2: ❌ FAILED" >> $summary_file
        fi
        
        # HTTP/3結果
        local h3_log="$LOG_DIR/h3_${delay}ms_${loss}pct.log"
        if [ -f "$h3_log" ] && grep -q "succeeded, 0 failed" "$h3_log"; then
            local h3_req_per_sec=$(grep "finished in" "$h3_log" | grep -o '[0-9.]* req/s' | head -1)
            local h3_total_time=$(grep "finished in" "$h3_log" | grep -o '[0-9.]*s' | head -1)
            echo "  HTTP/3: ✅ SUCCESS" >> $summary_file
            echo "    リクエスト/秒: $h3_req_per_sec" >> $summary_file
            echo "    総時間: $h3_total_time" >> $summary_file
        else
            echo "  HTTP/3: ⚠️  NOT SUPPORTED" >> $summary_file
        fi
        
        echo "" >> $summary_file
    done
    
    echo "結果サマリーを $summary_file に保存しました"
    echo ""
}

# メイン実行
main() {
    echo "Raspberry Pi 5サーバーのクイックベンチマークを開始します..."
    echo ""
    
    # Dockerコンテナの確認
    if ! docker ps | grep -q $CLIENT_CONTAINER; then
        echo "❌ クライアントコンテナ ($CLIENT_CONTAINER) が起動していません"
        echo "Docker環境を起動してください: docker-compose up -d"
        exit 1
    fi
    
    if ! docker ps | grep -q $ROUTER_CONTAINER; then
        echo "❌ ルーターコンテナ ($ROUTER_CONTAINER) が起動していません"
        echo "Docker環境を起動してください: docker-compose up -d"
        exit 1
    fi
    
    # 接続確認
    echo "接続確認中..."
    if ! ping -c 1 $RASPBERRY_PI_IP > /dev/null 2>&1; then
        echo "❌ Raspberry Pi 5 ($RASPBERRY_PI_IP) に接続できません"
        echo "サーバーの起動とネットワーク設定を確認してください"
        exit 1
    fi
    echo "✅ Raspberry Pi 5 に接続確認"
    echo ""
    
    # ベンチマーク実行
    for test_case in "${TEST_CASES[@]}"; do
        read -r delay loss <<< "$test_case"
        
        echo "================================================"
        echo "テストケース: ${delay}ms delay, ${loss}% loss"
        echo "================================================"
        
        # ネットワーク条件設定
        apply_network_conditions $delay $loss
        
        # HTTP/2ベンチマーク
        run_http2_benchmark $delay $loss
        
        # 待機
        echo "プロトコル間待機中..."
        sleep 10
        
        # HTTP/3ベンチマーク
        run_http3_benchmark $delay $loss
        
        echo "テストケース完了: ${delay}ms delay, ${loss}% loss"
        echo ""
    done
    
    # 結果サマリー生成
    generate_summary
    
    echo "================================================"
    echo "クイックベンチマーク完了: $(date)"
    echo "================================================"
    echo "結果ディレクトリ: $LOG_DIR"
    echo ""
    echo "生成されたファイル:"
    ls -la $LOG_DIR/
    echo ""
    echo "結果サマリー:"
    cat $LOG_DIR/quick_benchmark_summary.txt
    echo ""
    echo "次のステップ:"
    echo "1. 結果を確認してください"
    echo "2. 問題がない場合は本格的なベンチマークを実行してください:"
    echo "   ./scripts/run_bench_raspberry_pi.sh"
    echo "================================================"
}

# メイン実行
main "$@"
