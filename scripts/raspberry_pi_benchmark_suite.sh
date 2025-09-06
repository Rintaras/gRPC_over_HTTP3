#!/bin/bash

# Raspberry Pi 5 ベンチマークスイート
# 包括的な性能テストと検証

echo "================================================"
echo "Raspberry Pi 5 ベンチマークスイート"
echo "================================================"
echo "スイート開始: $(date)"
echo "================================================"

# 設定
RASPBERRY_PI_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"
CLIENT_CONTAINER="grpc-client"
ROUTER_CONTAINER="grpc-router"

# ログディレクトリ作成
NOW=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs/benchmark_suite_${NOW}"
mkdir -p $LOG_DIR

echo "[INFO] ログディレクトリ: $LOG_DIR"

# メニュー表示
show_menu() {
    echo "================================================"
    echo "ベンチマークスイート メニュー"
    echo "================================================"
    echo "1. サーバー検証テスト"
    echo "2. クイックベンチマーク"
    echo "3. 本格ベンチマーク"
    echo "4. カスタムベンチマーク"
    echo "5. ネットワーク診断"
    echo "6. パフォーマンス分析"
    echo "7. 全テスト実行"
    echo "8. 終了"
    echo "================================================"
    echo -n "選択してください (1-8): "
}

# 関数: サーバー検証テスト
run_verification_test() {
    echo "=== サーバー検証テスト実行 ==="
    ./scripts/verify_raspberry_pi_server.sh
    echo "サーバー検証テスト完了"
    echo ""
}

# 関数: クイックベンチマーク
run_quick_benchmark() {
    echo "=== クイックベンチマーク実行 ==="
    ./scripts/quick_benchmark_raspberry_pi.sh
    echo "クイックベンチマーク完了"
    echo ""
}

# 関数: 本格ベンチマーク
run_full_benchmark() {
    echo "=== 本格ベンチマーク実行 ==="
    ./scripts/run_bench_raspberry_pi.sh
    echo "本格ベンチマーク完了"
    echo ""
}

# 関数: カスタムベンチマーク
run_custom_benchmark() {
    echo "=== カスタムベンチマーク設定 ==="
    
    # パラメータ入力
    echo -n "リクエスト数 (デフォルト: 10000): "
    read requests
    requests=${requests:-10000}
    
    echo -n "接続数 (デフォルト: 50): "
    read connections
    connections=${connections:-50}
    
    echo -n "スレッド数 (デフォルト: 10): "
    read threads
    threads=${threads:-10}
    
    echo -n "遅延 (ms) (デフォルト: 100): "
    read delay
    delay=${delay:-100}
    
    echo -n "パケットロス (%) (デフォルト: 2): "
    read loss
    loss=${loss:-2}
    
    echo ""
    echo "カスタムベンチマークパラメータ:"
    echo "  リクエスト数: $requests"
    echo "  接続数: $connections"
    echo "  スレッド数: $threads"
    echo "  遅延: ${delay}ms"
    echo "  パケットロス: ${loss}%"
    echo ""
    
    # ネットワーク条件設定
    echo "ネットワーク条件設定中..."
    docker exec $ROUTER_CONTAINER /scripts/netem_delay_loss_bandwidth.sh $delay $loss
    sleep 5
    
    # HTTP/2ベンチマーク
    echo "HTTP/2ベンチマーク実行中..."
    local h2_log="$LOG_DIR/custom_h2_${delay}ms_${loss}pct.log"
    docker exec $CLIENT_CONTAINER h2load -n $requests -c $connections -t $threads \
        --connect-to $RASPBERRY_PI_IP:443 \
        --insecure \
        https://$RASPBERRY_PI_IP/health > $h2_log 2>&1
    
    if grep -q "succeeded, 0 failed" $h2_log; then
        echo "✅ HTTP/2ベンチマーク: SUCCESS"
        local h2_req_per_sec=$(grep "finished in" $h2_log | grep -o '[0-9.]* req/s' | head -1)
        echo "   リクエスト/秒: $h2_req_per_sec"
    else
        echo "❌ HTTP/2ベンチマーク: FAILED"
    fi
    
    # HTTP/3ベンチマーク
    echo "HTTP/3ベンチマーク実行中..."
    local h3_log="$LOG_DIR/custom_h3_${delay}ms_${loss}pct.log"
    docker exec $CLIENT_CONTAINER h2load -n $requests -c $connections -t $threads \
        --connect-to $RASPBERRY_PI_IP:443 \
        --alpn-list=h3,h2 \
        --insecure \
        https://$RASPBERRY_PI_IP/health > $h3_log 2>&1
    
    if grep -q "succeeded, 0 failed" $h3_log; then
        echo "✅ HTTP/3ベンチマーク: SUCCESS"
        local h3_req_per_sec=$(grep "finished in" $h3_log | grep -o '[0-9.]* req/s' | head -1)
        echo "   リクエスト/秒: $h3_req_per_sec"
    else
        echo "⚠️  HTTP/3ベンチマーク: NOT SUPPORTED"
    fi
    
    echo "カスタムベンチマーク完了"
    echo ""
}

# 関数: ネットワーク診断
run_network_diagnosis() {
    echo "=== ネットワーク診断実行 ==="
    
    local diag_log="$LOG_DIR/network_diagnosis.log"
    
    echo "ネットワーク診断結果" > $diag_log
    echo "===================" >> $diag_log
    echo "診断日時: $(date '+%Y-%m-%d %H:%M:%S')" >> $diag_log
    echo "" >> $diag_log
    
    # 基本接続テスト
    echo "1. 基本接続テスト..."
    echo "Ping to Raspberry Pi 5:" >> $diag_log
    ping -c 5 $RASPBERRY_PI_IP >> $diag_log 2>&1
    echo ""
    
    # ポート確認
    echo "2. ポート確認..."
    echo "Port 443 check:" >> $diag_log
    timeout 5 bash -c "</dev/tcp/$RASPBERRY_PI_IP/443" >> $diag_log 2>&1
    echo ""
    
    # SSL証明書確認
    echo "3. SSL証明書確認..."
    echo "SSL Certificate check:" >> $diag_log
    echo | openssl s_client -connect $RASPBERRY_PI_IP:443 -servername grpc-server-pi.local 2>&1 | \
        grep -E "(Subject:|Not Before|Not After|Verify return code)" >> $diag_log
    echo ""
    
    # ネットワーク統計
    echo "4. ネットワーク統計..."
    echo "Client network stats:" >> $diag_log
    docker exec $CLIENT_CONTAINER ip -s link show eth0 >> $diag_log 2>&1
    echo "" >> $diag_log
    
    echo "Router network stats:" >> $diag_log
    docker exec $ROUTER_CONTAINER ip -s link show eth0 >> $diag_log 2>&1
    echo "" >> $diag_log
    
    # 接続テスト
    echo "5. 接続テスト..."
    echo "HTTP/2 connection test:" >> $diag_log
    curl -k --http2 --connect-timeout 10 https://$RASPBERRY_PI_IP/health >> $diag_log 2>&1
    echo "" >> $diag_log
    
    echo "HTTP/3 connection test:" >> $diag_log
    curl -k --http3 --connect-timeout 10 https://$RASPBERRY_PI_IP/health >> $diag_log 2>&1
    echo "" >> $diag_log
    
    echo "ネットワーク診断完了: $diag_log"
    echo ""
}

# 関数: パフォーマンス分析
run_performance_analysis() {
    echo "=== パフォーマンス分析実行 ==="
    
    local analysis_log="$LOG_DIR/performance_analysis.log"
    
    echo "パフォーマンス分析結果" > $analysis_log
    echo "====================" >> $analysis_log
    echo "分析日時: $(date '+%Y-%m-%d %H:%M:%S')" >> $analysis_log
    echo "" >> $analysis_log
    
    # レスポンス時間測定
    echo "1. レスポンス時間測定..."
    echo "HTTP/2 Response Time Analysis:" >> $analysis_log
    for i in {1..10}; do
        local start_time=$(date +%s.%N)
        curl -k --http2 --connect-timeout 5 https://$RASPBERRY_PI_IP/health > /dev/null 2>&1
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)
        echo "Request $i: ${duration}s" >> $analysis_log
    done
    echo ""
    
    # スループット測定
    echo "2. スループット測定..."
    echo "Throughput Analysis:" >> $analysis_log
    local throughput_log="$LOG_DIR/throughput_test.log"
    docker exec $CLIENT_CONTAINER h2load -n 1000 -c 10 -t 2 \
        --connect-to $RASPBERRY_PI_IP:443 \
        --insecure \
        https://$RASPBERRY_PI_IP/health > $throughput_log 2>&1
    
    if grep -q "succeeded, 0 failed" $throughput_log; then
        local req_per_sec=$(grep "finished in" $throughput_log | grep -o '[0-9.]* req/s' | head -1)
        local total_time=$(grep "finished in" $throughput_log | grep -o '[0-9.]*s' | head -1)
        echo "Requests per second: $req_per_sec" >> $analysis_log
        echo "Total time: $total_time" >> $analysis_log
    else
        echo "Throughput test failed" >> $analysis_log
    fi
    echo ""
    
    # リソース使用量確認
    echo "3. リソース使用量確認..."
    echo "Resource Usage:" >> $analysis_log
    echo "Client container stats:" >> $analysis_log
    docker stats $CLIENT_CONTAINER --no-stream >> $analysis_log 2>&1
    echo "" >> $analysis_log
    
    echo "Router container stats:" >> $analysis_log
    docker stats $ROUTER_CONTAINER --no-stream >> $analysis_log 2>&1
    echo "" >> $analysis_log
    
    echo "パフォーマンス分析完了: $analysis_log"
    echo ""
}

# 関数: 全テスト実行
run_all_tests() {
    echo "=== 全テスト実行 ==="
    
    echo "1. サーバー検証テスト..."
    run_verification_test
    
    echo "2. クイックベンチマーク..."
    run_quick_benchmark
    
    echo "3. ネットワーク診断..."
    run_network_diagnosis
    
    echo "4. パフォーマンス分析..."
    run_performance_analysis
    
    echo "全テスト完了"
    echo ""
}

# メインループ
main() {
    echo "Raspberry Pi 5ベンチマークスイートを開始します..."
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
    
    # メニューループ
    while true; do
        show_menu
        read choice
        
        case $choice in
            1)
                run_verification_test
                ;;
            2)
                run_quick_benchmark
                ;;
            3)
                run_full_benchmark
                ;;
            4)
                run_custom_benchmark
                ;;
            5)
                run_network_diagnosis
                ;;
            6)
                run_performance_analysis
                ;;
            7)
                run_all_tests
                ;;
            8)
                echo "ベンチマークスイートを終了します"
                break
                ;;
            *)
                echo "無効な選択です。1-8の数字を入力してください。"
                ;;
        esac
        
        echo "Enterキーを押して続行..."
        read
    done
    
    echo "================================================"
    echo "ベンチマークスイート終了: $(date)"
    echo "================================================"
    echo "結果ディレクトリ: $LOG_DIR"
    echo "生成されたファイル:"
    ls -la $LOG_DIR/
    echo "================================================"
}

# メイン実行
main "$@"
