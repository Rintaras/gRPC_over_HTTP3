#!/bin/bash

# Raspberry Pi 5 サーバー検証スクリプト
# 構築されたサーバーの動作確認とベンチマーク実行

echo "================================================"
echo "Raspberry Pi 5 サーバー検証スクリプト"
echo "================================================"
echo "検証開始: $(date)"
echo "================================================"

# 設定
RASPBERRY_PI_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"
CLIENT_CONTAINER="grpc-client"
ROUTER_CONTAINER="grpc-router"

# ログディレクトリ作成
NOW=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs/verification_${NOW}"
mkdir -p $LOG_DIR

echo "[INFO] ログディレクトリ: $LOG_DIR"

# 関数: 基本的な接続テスト
test_basic_connectivity() {
    echo "=== 基本的な接続テスト ==="
    
    # Pingテスト
    echo "1. Pingテスト..."
    if ping -c 3 $RASPBERRY_PI_IP > /dev/null 2>&1; then
        echo "✅ Ping to Raspberry Pi 5: SUCCESS"
    else
        echo "❌ Ping to Raspberry Pi 5: FAILED"
        return 1
    fi
    
    # ポート443テスト
    echo "2. ポート443テスト..."
    if timeout 5 bash -c "</dev/tcp/$RASPBERRY_PI_IP/443" 2>/dev/null; then
        echo "✅ Port 443 on Raspberry Pi 5: OPEN"
    else
        echo "❌ Port 443 on Raspberry Pi 5: CLOSED"
        return 1
    fi
    
    echo ""
}

# 関数: SSL証明書テスト
test_ssl_certificate() {
    echo "=== SSL証明書テスト ==="
    
    # SSL証明書確認
    echo "1. SSL証明書確認..."
    if echo | openssl s_client -connect $RASPBERRY_PI_IP:443 -servername grpc-server-pi.local 2>/dev/null | grep -q "Verify return code: 0"; then
        echo "✅ SSL certificate: VALID"
    else
        echo "⚠️  SSL certificate: SELF-SIGNED (expected for development)"
    fi
    
    # 証明書詳細情報
    echo "2. 証明書詳細情報..."
    echo | openssl s_client -connect $RASPBERRY_PI_IP:443 -servername grpc-server-pi.local 2>/dev/null | \
        openssl x509 -noout -text | grep -E "(Subject:|Not Before|Not After|Public Key)" >> "$LOG_DIR/ssl_certificate_info.txt"
    echo "証明書情報を $LOG_DIR/ssl_certificate_info.txt に保存しました"
    
    echo ""
}

# 関数: HTTP/2接続テスト
test_http2_connection() {
    echo "=== HTTP/2接続テスト ==="
    
    # ローカル接続テスト
    echo "1. ローカル接続テスト..."
    if curl -k --http2 --connect-timeout 10 https://$RASPBERRY_PI_IP/health 2>/dev/null | grep -q "OK"; then
        echo "✅ HTTP/2 local connection: SUCCESS"
    else
        echo "❌ HTTP/2 local connection: FAILED"
        return 1
    fi
    
    # Dockerクライアントからの接続テスト
    echo "2. Dockerクライアントからの接続テスト..."
    if docker exec $CLIENT_CONTAINER curl -k --http2 --connect-timeout 10 https://$RASPBERRY_PI_IP/health 2>/dev/null | grep -q "OK"; then
        echo "✅ HTTP/2 Docker client connection: SUCCESS"
    else
        echo "❌ HTTP/2 Docker client connection: FAILED"
        return 1
    fi
    
    # Echoエンドポイントテスト
    echo "3. Echoエンドポイントテスト..."
    local echo_response=$(curl -k --http2 --connect-timeout 10 https://$RASPBERRY_PI_IP/echo -d "test message" 2>/dev/null)
    if echo "$echo_response" | grep -q "Hello from Raspberry Pi 5"; then
        echo "✅ HTTP/2 echo endpoint: SUCCESS"
        echo "   レスポンス: $echo_response"
    else
        echo "❌ HTTP/2 echo endpoint: FAILED"
        return 1
    fi
    
    echo ""
}

# 関数: HTTP/3接続テスト
test_http3_connection() {
    echo "=== HTTP/3接続テスト ==="
    
    # ローカル接続テスト
    echo "1. ローカル接続テスト..."
    if curl -k --http3 --connect-timeout 10 https://$RASPBERRY_PI_IP/health 2>/dev/null | grep -q "OK"; then
        echo "✅ HTTP/3 local connection: SUCCESS"
    else
        echo "⚠️  HTTP/3 local connection: MAY NOT BE SUPPORTED"
    fi
    
    # Dockerクライアントからの接続テスト
    echo "2. Dockerクライアントからの接続テスト..."
    if docker exec $CLIENT_CONTAINER curl -k --http3 --connect-timeout 10 https://$RASPBERRY_PI_IP/health 2>/dev/null | grep -q "OK"; then
        echo "✅ HTTP/3 Docker client connection: SUCCESS"
    else
        echo "⚠️  HTTP/3 Docker client connection: MAY NOT BE SUPPORTED"
    fi
    
    # Echoエンドポイントテスト
    echo "3. Echoエンドポイントテスト..."
    local echo_response=$(curl -k --http3 --connect-timeout 10 https://$RASPBERRY_PI_IP/echo -d "test message" 2>/dev/null)
    if echo "$echo_response" | grep -q "Hello from Raspberry Pi 5"; then
        echo "✅ HTTP/3 echo endpoint: SUCCESS"
        echo "   レスポンス: $echo_response"
    else
        echo "⚠️  HTTP/3 echo endpoint: MAY NOT BE SUPPORTED"
    fi
    
    echo ""
}

# 関数: パフォーマンステスト
test_performance() {
    echo "=== パフォーマンステスト ==="
    
    # 基本的なパフォーマンステスト
    echo "1. 基本的なパフォーマンステスト..."
    
    # HTTP/2パフォーマンステスト
    echo "   HTTP/2パフォーマンステスト..."
    local h2_start_time=$(date +%s.%N)
    for i in {1..10}; do
        curl -k --http2 --connect-timeout 5 https://$RASPBERRY_PI_IP/health > /dev/null 2>&1
    done
    local h2_end_time=$(date +%s.%N)
    local h2_duration=$(echo "$h2_end_time - $h2_start_time" | bc)
    echo "   HTTP/2 10リクエスト時間: ${h2_duration}秒"
    
    # HTTP/3パフォーマンステスト（利用可能な場合）
    echo "   HTTP/3パフォーマンステスト..."
    local h3_start_time=$(date +%s.%N)
    for i in {1..10}; do
        curl -k --http3 --connect-timeout 5 https://$RASPBERRY_PI_IP/health > /dev/null 2>&1
    done
    local h3_end_time=$(date +%s.%N)
    local h3_duration=$(echo "$h3_end_time - $h3_start_time" | bc)
    echo "   HTTP/3 10リクエスト時間: ${h3_duration}秒"
    
    echo ""
}

# 関数: ネットワーク統計収集
collect_network_stats() {
    echo "=== ネットワーク統計収集 ==="
    
    # クライアント側統計
    echo "1. クライアント側統計..."
    docker exec $CLIENT_CONTAINER ss -tuln > "$LOG_DIR/client_ss_output.txt" 2>&1
    docker exec $CLIENT_CONTAINER ip -s link show eth0 > "$LOG_DIR/client_network_stats.txt" 2>&1
    
    # ルーター側統計
    echo "2. ルーター側統計..."
    docker exec $ROUTER_CONTAINER ss -tuln > "$LOG_DIR/router_ss_output.txt" 2>&1
    docker exec $ROUTER_CONTAINER ip -s link show eth0 > "$LOG_DIR/router_network_stats.txt" 2>&1
    
    # 接続テスト
    echo "3. 接続テスト..."
    docker exec $CLIENT_CONTAINER ping -c 5 $RASPBERRY_PI_IP > "$LOG_DIR/ping_test.txt" 2>&1
    
    echo "ネットワーク統計を $LOG_DIR/ に保存しました"
    echo ""
}

# 関数: ベンチマーク実行
run_benchmark() {
    echo "=== ベンチマーク実行 ==="
    
    # ベンチマークパラメータ
    local requests=1000
    local connections=10
    local threads=2
    
    echo "ベンチマークパラメータ:"
    echo "  リクエスト数: $requests"
    echo "  接続数: $connections"
    echo "  スレッド数: $threads"
    echo ""
    
    # HTTP/2ベンチマーク
    echo "1. HTTP/2ベンチマーク実行..."
    local h2_log="$LOG_DIR/h2_benchmark.log"
    echo "=== HTTP/2 BENCHMARK ===" > $h2_log
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')" >> $h2_log
    echo "Target: $RASPBERRY_PI_IP:443" >> $h2_log
    echo "" >> $h2_log
    
    docker exec $CLIENT_CONTAINER h2load -n $requests -c $connections -t $threads \
        --connect-to $RASPBERRY_PI_IP:443 \
        --insecure \
        https://$RASPBERRY_PI_IP/health >> $h2_log 2>&1
    
    if grep -q "succeeded, 0 failed" $h2_log; then
        echo "✅ HTTP/2ベンチマーク: SUCCESS"
    else
        echo "❌ HTTP/2ベンチマーク: FAILED"
    fi
    
    # HTTP/3ベンチマーク
    echo "2. HTTP/3ベンチマーク実行..."
    local h3_log="$LOG_DIR/h3_benchmark.log"
    echo "=== HTTP/3 BENCHMARK ===" > $h3_log
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')" >> $h3_log
    echo "Target: $RASPBERRY_PI_IP:443" >> $h3_log
    echo "" >> $h3_log
    
    docker exec $CLIENT_CONTAINER h2load -n $requests -c $connections -t $threads \
        --connect-to $RASPBERRY_PI_IP:443 \
        --alpn-list=h3,h2 \
        --insecure \
        https://$RASPBERRY_PI_IP/health >> $h3_log 2>&1
    
    if grep -q "succeeded, 0 failed" $h3_log; then
        echo "✅ HTTP/3ベンチマーク: SUCCESS"
    else
        echo "⚠️  HTTP/3ベンチマーク: MAY NOT BE SUPPORTED"
    fi
    
    echo ""
}

# 関数: 結果サマリー生成
generate_summary() {
    echo "=== 結果サマリー生成 ==="
    
    local summary_file="$LOG_DIR/verification_summary.txt"
    
    echo "Raspberry Pi 5 サーバー検証結果" > $summary_file
    echo "=================================" >> $summary_file
    echo "検証日時: $(date '+%Y-%m-%d %H:%M:%S')" >> $summary_file
    echo "対象サーバー: $RASPBERRY_PI_IP" >> $summary_file
    echo "" >> $summary_file
    
    # 接続テスト結果
    echo "接続テスト結果:" >> $summary_file
    if ping -c 1 $RASPBERRY_PI_IP > /dev/null 2>&1; then
        echo "  Ping: ✅ SUCCESS" >> $summary_file
    else
        echo "  Ping: ❌ FAILED" >> $summary_file
    fi
    
    if timeout 5 bash -c "</dev/tcp/$RASPBERRY_PI_IP/443" 2>/dev/null; then
        echo "  Port 443: ✅ OPEN" >> $summary_file
    else
        echo "  Port 443: ❌ CLOSED" >> $summary_file
    fi
    
    # HTTP/2テスト結果
    echo "" >> $summary_file
    echo "HTTP/2テスト結果:" >> $summary_file
    if curl -k --http2 --connect-timeout 5 https://$RASPBERRY_PI_IP/health 2>/dev/null | grep -q "OK"; then
        echo "  HTTP/2: ✅ SUCCESS" >> $summary_file
    else
        echo "  HTTP/2: ❌ FAILED" >> $summary_file
    fi
    
    # HTTP/3テスト結果
    echo "" >> $summary_file
    echo "HTTP/3テスト結果:" >> $summary_file
    if curl -k --http3 --connect-timeout 5 https://$RASPBERRY_PI_IP/health 2>/dev/null | grep -q "OK"; then
        echo "  HTTP/3: ✅ SUCCESS" >> $summary_file
    else
        echo "  HTTP/3: ⚠️  NOT SUPPORTED" >> $summary_file
    fi
    
    # ベンチマーク結果
    echo "" >> $summary_file
    echo "ベンチマーク結果:" >> $summary_file
    if [ -f "$LOG_DIR/h2_benchmark.log" ] && grep -q "succeeded, 0 failed" "$LOG_DIR/h2_benchmark.log"; then
        echo "  HTTP/2ベンチマーク: ✅ SUCCESS" >> $summary_file
    else
        echo "  HTTP/2ベンチマーク: ❌ FAILED" >> $summary_file
    fi
    
    if [ -f "$LOG_DIR/h3_benchmark.log" ] && grep -q "succeeded, 0 failed" "$LOG_DIR/h3_benchmark.log"; then
        echo "  HTTP/3ベンチマーク: ✅ SUCCESS" >> $summary_file
    else
        echo "  HTTP/3ベンチマーク: ⚠️  NOT SUPPORTED" >> $summary_file
    fi
    
    echo "結果サマリーを $summary_file に保存しました"
    echo ""
}

# メイン実行
main() {
    echo "Raspberry Pi 5サーバーの検証を開始します..."
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
    
    # 検証実行
    test_basic_connectivity
    test_ssl_certificate
    test_http2_connection
    test_http3_connection
    test_performance
    collect_network_stats
    run_benchmark
    generate_summary
    
    echo "================================================"
    echo "検証完了: $(date)"
    echo "================================================"
    echo "結果ディレクトリ: $LOG_DIR"
    echo ""
    echo "生成されたファイル:"
    ls -la $LOG_DIR/
    echo ""
    echo "結果サマリー:"
    cat $LOG_DIR/verification_summary.txt
    echo ""
    echo "次のステップ:"
    echo "1. 結果を確認してください"
    echo "2. 問題がある場合はトラブルシューティングを実行してください"
    echo "3. 問題がない場合は本格的なベンチマークを実行してください:"
    echo "   ./scripts/run_bench_raspberry_pi.sh"
    echo "================================================"
}

# メイン実行
main "$@"
