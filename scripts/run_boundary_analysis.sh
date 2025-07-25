#!/bin/bash

# HTTP/2 vs HTTP/3 Performance Boundary Analysis Script
# 性能境界値分析用ベンチマークスクリプト

set -e

# 基本設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="logs/boundary_analysis_$(date +%Y%m%d_%H%M%S)"
SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"

# ベンチマークパラメータ
REQUESTS=10000
CONNECTIONS=50
THREADS=10
WARMUP_REQUESTS=2000
MEASUREMENT_REQUESTS=8000
WARMUP_TIME=5

echo "================================================"
echo "HTTP/2 vs HTTP/3 Performance Boundary Analysis"
echo "================================================"
echo "開始時刻: $(date)"
echo "ログディレクトリ: $LOG_DIR"
echo "================================================"

# ログディレクトリ作成
mkdir -p $LOG_DIR

# 境界値分析用テストケース
declare -a BOUNDARY_TESTS=(
    # 低遅延環境での境界値検出 (0-20ms, 1ms刻み)
    "0:20:1:0.0:0"
    "0:20:1:0.5:0" 
    "0:20:1:1.0:0"
    
    # 中遅延環境での境界値検出 (20-100ms, 2ms刻み)
    "20:100:2:0.0:0"
    "20:100:2:1.0:0"
    "20:100:2:2.0:0"
    
    # 高遅延環境での境界値検出 (100-300ms, 5ms刻み)
    "100:300:5:0.0:0"
    "100:300:5:2.0:0"
    "100:300:5:5.0:0"
)

# 境界値分析関数
run_boundary_test() {
    local test_spec="$1"
    IFS=':' read -r delay_start delay_end delay_step loss bandwidth <<< "$test_spec"
    
    echo ""
    echo "=== 境界値分析: ${delay_start}-${delay_end}ms (${delay_step}ms刻み), Loss: ${loss}%, BW: ${bandwidth}Mbps ==="
    
    local test_name="boundary_${delay_start}_${delay_end}_${delay_step}_${loss//./_}pct_${bandwidth}mbps"
    local test_log="$LOG_DIR/${test_name}.log"
    local csv_file="$LOG_DIR/${test_name}.csv"
    
    # CSVヘッダー作成
    echo "delay_ms,loss_pct,bandwidth_mbps,protocol,throughput_req_s,latency_mean_ms,latency_p50_ms,latency_p90_ms,latency_p99_ms,connect_time_mean_ms,ttfb_mean_ms,error_rate_pct,timeout_rate_pct" > "$csv_file"
    
    # 遅延範囲でのテスト実行
    for delay in $(seq $delay_start $delay_step $delay_end); do
        echo "Testing: ${delay}ms delay, ${loss}% loss, ${bandwidth}Mbps bandwidth"
        
        # ネットワーク条件設定
        if [ "$bandwidth" = "0" ]; then
            docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh $delay $loss > /dev/null 2>&1
        else
            docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh $delay $loss $bandwidth > /dev/null 2>&1
        fi
        
        # システム安定化
        echo "  システム安定化中..."
        sleep $WARMUP_TIME
        
        # HTTP/2テスト
        echo "  HTTP/2テスト実行中..."
        local h2_result=$(docker exec grpc-client h2load --alpn-list=h2,http/1.1 \
            -n $REQUESTS -c $CONNECTIONS -t $THREADS \
            https://$SERVER_IP/echo 2>/dev/null)
        
        # HTTP/2結果解析
        local h2_throughput=$(echo "$h2_result" | grep "finished in" | awk '{print $4}')
        local h2_latency_mean=$(echo "$h2_result" | grep "time for request:" | awk '{print $2}' | sed 's/us$//' | awk '{print $1/1000}')
        local h2_connect_mean=$(echo "$h2_result" | grep "time for connect:" | awk '{print $2}' | sed 's/ms$//')
        local h2_ttfb_mean=$(echo "$h2_result" | grep "time to 1st byte:" | awk '{print $2}' | sed 's/ms$//')
        
        # HTTP/3テスト
        echo "  HTTP/3テスト実行中..."
        local h3_result=$(docker exec grpc-client h2load --alpn-list=h3,h2,http/1.1 \
            -n $REQUESTS -c $CONNECTIONS -t $THREADS \
            https://$SERVER_IP/echo 2>/dev/null)
        
        # HTTP/3結果解析
        local h3_throughput=$(echo "$h3_result" | grep "finished in" | awk '{print $4}')
        local h3_latency_mean=$(echo "$h3_result" | grep "time for request:" | awk '{print $2}' | sed 's/us$//' | awk '{print $1/1000}')
        local h3_connect_mean=$(echo "$h3_result" | grep "time for connect:" | awk '{print $2}' | sed 's/ms$//')
        local h3_ttfb_mean=$(echo "$h3_result" | grep "time to 1st byte:" | awk '{print $2}' | sed 's/ms$//')
        
        # CSV出力
        echo "$delay,$loss,$bandwidth,http2,$h2_throughput,$h2_latency_mean,0,0,0,$h2_connect_mean,$h2_ttfb_mean,0,0" >> "$csv_file"
        echo "$delay,$loss,$bandwidth,http3,$h3_throughput,$h3_latency_mean,0,0,0,$h3_connect_mean,$h3_ttfb_mean,0,0" >> "$csv_file"
        
        # 境界値判定
        local throughput_diff=$(echo "scale=4; ($h3_throughput - $h2_throughput) / $h2_throughput * 100" | bc -l 2>/dev/null || echo "0")
        echo "  結果: HTTP/2=${h2_throughput} req/s, HTTP/3=${h3_throughput} req/s, 差異=${throughput_diff}%"
        
        # 境界値検出ログ
        if (( $(echo "$throughput_diff > 5" | bc -l 2>/dev/null || echo "0") )); then
            echo "*** 境界値候補検出: ${delay}ms遅延でHTTP/3が${throughput_diff}%優位 ***" | tee -a "$LOG_DIR/boundary_candidates.log"
        elif (( $(echo "$throughput_diff < -5" | bc -l 2>/dev/null || echo "0") )); then
            echo "*** 境界値候補検出: ${delay}ms遅延でHTTP/2が$(echo "scale=1; -1 * $throughput_diff" | bc -l)%優位 ***" | tee -a "$LOG_DIR/boundary_candidates.log"
        fi
    done
    
    echo "境界値分析完了: $test_name"
}

# メイン実行ループ
echo "境界値分析テスト開始..."

for test_spec in "${BOUNDARY_TESTS[@]}"; do
    run_boundary_test "$test_spec"
done

# ネットワーク条件リセット
echo ""
echo "ネットワーク条件をリセット中..."
docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh 0 0 > /dev/null 2>&1

echo ""
echo "================================================"
echo "境界値分析完了: $(date)"
echo "結果保存先: $LOG_DIR"
echo "================================================"

# 境界値分析レポート生成
if [ -f "$LOG_DIR/boundary_candidates.log" ]; then
    echo ""
    echo "=== 検出された境界値候補 ==="
    cat "$LOG_DIR/boundary_candidates.log"
    echo ""
fi

echo "境界値分析用データファイル:"
ls -la "$LOG_DIR"/*.csv

echo ""
echo "次のステップ: 境界値分析スクリプトでデータを解析してください"
echo "python3 scripts/analyze_boundary_results.py $LOG_DIR" 