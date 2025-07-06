#!/bin/bash

# 高負荷ベンチマークスクリプト（HTTP/2 vs HTTP/3）
echo "================================================"
echo "高負荷ベンチマーク開始: $(date)"
echo "================================================"

# コンテナ内でベンチマーク実行
docker exec grpc-client bash -c '
NOW=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="/logs/benchmark_highload_${NOW}"
mkdir -p $LOG_DIR

SERVER_IP="172.30.0.2"
ROUTER_IP="172.30.0.254"

# 高負荷テストケース（遅延ms 損失% 帯域Mbps）
declare -a test_cases=(
    "0 0 0"      # 理想
    "50 0 0"    # 中遅延
    "100 1 0"   # 高遅延低損失
    "150 3 0"   # 高遅延高損失
    "100 0 10"  # 帯域制限
    "150 1 5"   # 高遅延+損失+帯域
)

REQUESTS=100000
CONNECTIONS=500
THREADS=100
MAX_CONCURRENT=500
# 10KBのランダムデータ
REQUEST_DATA=$(head -c 10240 </dev/urandom | base64 | tr -d '\n' | head -c 10240)
WARMUP_REQUESTS=10000
MEASUREMENT_REQUESTS=90000
CONNECTION_WARMUP_TIME=3

cat <<EOF > "$LOG_DIR/benchmark_params.txt"
REQUESTS=$REQUESTS
CONNECTIONS=$CONNECTIONS
THREADS=$THREADS
MAX_CONCURRENT=$MAX_CONCURRENT
WARMUP_REQUESTS=$WARMUP_REQUESTS
MEASUREMENT_REQUESTS=$MEASUREMENT_REQUESTS
CONNECTION_WARMUP_TIME=$CONNECTION_WARMUP_TIME
EOF

get_timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

log_network_conditions() {
    local delay=$1
    local loss=$2
    local bw=$3
    local log_file=$4
    echo "=== NETWORK CONDITIONS ===" >> $log_file
    echo "Timestamp: $(get_timestamp)" >> $log_file
    echo "Delay: ${delay}ms" >> $log_file
    echo "Loss: ${loss}%" >> $log_file
    echo "Bandwidth: ${bw}Mbps" >> $log_file
    echo "Router IP: $ROUTER_IP" >> $log_file
    echo "Server IP: $SERVER_IP" >> $log_file
    echo "Current qdisc configuration:" >> $log_file
    docker exec grpc-router tc qdisc show dev eth0 >> $log_file 2>&1
    echo "" >> $log_file
}

run_http2_bench() {
    local delay=$1; local loss=$2; local bw=$3
    local log_file="$LOG_DIR/h2_${delay}ms_${loss}pct_${bw}mbps.log"
    local csv_file="$LOG_DIR/h2_${delay}ms_${loss}pct_${bw}mbps.csv"
    echo "=== HTTP/2 BENCHMARK RESULTS ===" > $log_file
    log_network_conditions $delay $loss $bw $log_file
    local temp_data_file=$(mktemp)
    echo "$REQUEST_DATA" > "$temp_data_file"
    h2load -n $WARMUP_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 --header "User-Agent: h2load-benchmark-warmup" \
        --data "$temp_data_file" https://$SERVER_IP/echo >> $log_file 2>&1
    sleep $CONNECTION_WARMUP_TIME
    h2load -n $MEASUREMENT_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 --header "User-Agent: h2load-benchmark-measurement" \
        --data "$temp_data_file" --log-file "$csv_file" https://$SERVER_IP/echo >> $log_file 2>&1
    rm "$temp_data_file"
    echo "=== BENCHMARK SUMMARY ===" >> $log_file
    echo "Protocol: HTTP/2" >> $log_file
    echo "End Time: $(get_timestamp)" >> $log_file
    echo "CSV Log: $csv_file" >> $log_file
}

run_http3_bench() {
    local delay=$1; local loss=$2; local bw=$3
    local log_file="$LOG_DIR/h3_${delay}ms_${loss}pct_${bw}mbps.log"
    local csv_file="$LOG_DIR/h3_${delay}ms_${loss}pct_${bw}mbps.csv"
    echo "=== HTTP/3 BENCHMARK RESULTS ===" > $log_file
    log_network_conditions $delay $loss $bw $log_file
    local temp_data_file=$(mktemp)
    echo "$REQUEST_DATA" > "$temp_data_file"
    h2load -n $WARMUP_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 --header "User-Agent: h2load-benchmark-warmup" \
        --data "$temp_data_file" --alpn-list=h3,h2 https://$SERVER_IP/echo >> $log_file 2>&1
    sleep $CONNECTION_WARMUP_TIME
    h2load -n $MEASUREMENT_REQUESTS -c $CONNECTIONS -t $THREADS -m $MAX_CONCURRENT \
        --connect-to $SERVER_IP:443 --header "User-Agent: h2load-benchmark-measurement" \
        --data "$temp_data_file" --alpn-list=h3,h2 --log-file "$csv_file" https://$SERVER_IP/echo >> $log_file 2>&1
    rm "$temp_data_file"
    echo "=== BENCHMARK SUMMARY ===" >> $log_file
    echo "Protocol: HTTP/3" >> $log_file
    echo "End Time: $(get_timestamp)" >> $log_file
    echo "CSV Log: $csv_file" >> $log_file
}

for test_case in "${test_cases[@]}"; do
    read -r delay loss bw <<< "$test_case"
    echo ""
    echo "================================================"
    echo "Test case: ${delay}ms delay, ${loss}% loss, ${bw}Mbps bandwidth"
    echo "================================================"
    # ネットワーク条件適用
    docker exec grpc-router /scripts/netem_delay_loss_bandwidth.sh $delay $loss $bw
    sleep 8
    run_http2_bench $delay $loss $bw
    run_http3_bench $delay $loss $bw
    echo "Completed test case: ${delay}ms delay, ${loss}% loss, ${bw}Mbps bandwidth"
    echo ""
done

echo "================================================"
echo "All highload benchmarks completed!"
echo "Results saved in $LOG_DIR/"
echo "================================================"
ls -la $LOG_DIR/h*_*.log 
'

# ホスト側でグラフ生成
echo "[ホスト] グラフ自動生成: python3 scripts/generate_performance_graphs.py"
LATEST_LOG_DIR=$(ls -1td logs/benchmark_highload_* | head -n1)
python3 scripts/generate_performance_graphs.py "$LATEST_LOG_DIR"
echo "================================================"
echo "高負荷ベンチマーク + グラフ生成 完了: $(date)"
echo "結果: $LATEST_LOG_DIR"
echo "================================================" 