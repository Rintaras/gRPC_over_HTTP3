#!/bin/bash

echo "========================================="
echo "HTTP/3 vs HTTP/2 遅延影響ベンチマーク"
echo "========================================="
echo ""
echo "条件:"
echo "- 帯域: 5Mbps (固定)"
echo "- 遅延: 0ms, 25ms, 50ms, 75ms, 100ms, 125ms, 150ms, 175ms, 200ms"
echo "- パケット損失: 0% (固定)"
echo "- データサイズ: 1MB (固定)"
echo "- リクエスト数: 25回/条件"
echo ""

BANDWIDTH="5mbit"
LOSS="0%"
ITERATIONS=25

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="$PROJECT_ROOT/logs/${TIMESTAMP}"
mkdir -p "$LOG_DIR"

OUTPUT_FILE="${LOG_DIR}/benchmark_results.csv"

echo "timestamp,protocol,latency,iteration,time_total,speed_kbps,success" > $OUTPUT_FILE

echo "結果保存先: $LOG_DIR"
echo ""

run_benchmark() {
    local latency=$1
    local label=$2
    
    echo ""
    echo "========================================="
    echo "$label"
    echo "帯域: $BANDWIDTH, 遅延: $latency, 損失: $LOSS"
    echo "========================================="
    
    docker-compose -f "$PROJECT_ROOT/docker-compose.router_tc.yml" down 2>/dev/null
    sleep 2
    
    echo "コンテナ起動中..."
    BANDWIDTH=$BANDWIDTH LATENCY=$latency LOSS=$LOSS docker-compose -f "$PROJECT_ROOT/docker-compose.router_tc.yml" up -d 2>&1 | grep -E "(Created|Started)" > /dev/null
    
    sleep 5
    
    echo ""
    echo "tc設定確認:"
    docker exec network-router tc qdisc show dev eth0
    
    echo ""
    echo "=== HTTP/3テスト (50回) ==="
    docker build -f "$PROJECT_ROOT/Dockerfile.http3_test" -t http3-test "$PROJECT_ROOT" 2>&1 | grep -E "(writing|naming)" | tail -2 > /dev/null
    
    local http3_times=()
    local http3_speeds=()
    local http3_success=0
    local http3_total_time=0
    local http3_total_speed=0
    
    for i in $(seq 1 $ITERATIONS); do
        timestamp=$(date +%s)
        output=$(docker run --rm \
          --network protocol_comparison_protocol_net \
          --add-host=network-router:$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' network-router) \
          -e TARGET_URL=https://network-router:8443/1mb \
          http3-test "./http3_test" "1" 2>&1)
        
        if echo "$output" | grep -q "成功: 1/1"; then
            time=$(echo "$output" | grep "平均時間:" | awk '{print $2}' | sed 's/秒//')
            speed=$(echo "$output" | grep "平均速度:" | awk '{print $2}')
            
            if [ ! -z "$time" ] && [ ! -z "$speed" ]; then
                http3_times+=($time)
                http3_speeds+=($speed)
                http3_total_time=$(echo "$http3_total_time + $time" | bc)
                http3_total_speed=$(echo "$http3_total_speed + $speed" | bc)
                http3_success=$((http3_success + 1))
                
                echo "$timestamp,HTTP/3,$latency,$i,$time,$speed,1" >> $OUTPUT_FILE
                
                if [ $((i % 10)) -eq 0 ]; then
                    echo "  進捗: $i/$ITERATIONS (${time}秒, ${speed} KB/s)"
                fi
            else
                echo "$timestamp,HTTP/3,$latency,$i,,,0" >> $OUTPUT_FILE
            fi
        else
            echo "$timestamp,HTTP/3,$latency,$i,,,0" >> $OUTPUT_FILE
            if [ $((i % 10)) -eq 0 ]; then
                echo "  進捗: $i/$ITERATIONS (失敗)"
            fi
        fi
    done
    
    if [ $http3_success -gt 0 ]; then
        local http3_avg_time=$(echo "scale=3; $http3_total_time / $http3_success" | bc)
        local http3_avg_speed=$(echo "scale=2; $http3_total_speed / $http3_success" | bc)
        
        IFS=$'\n' sorted=($(printf '%s\n' "${http3_times[@]}" | sort -n))
        unset IFS
        local http3_min=${sorted[0]}
        local http3_max=${sorted[${#sorted[@]}-1]}
        local median_idx=$((http3_success / 2))
        local http3_median=${sorted[$median_idx]}
        
        echo ""
        echo "HTTP/3 結果:"
        echo "  成功: $http3_success/$ITERATIONS"
        echo "  平均時間: ${http3_avg_time}秒"
        echo "  平均速度: ${http3_avg_speed} KB/s"
        echo "  中央値: ${http3_median}秒"
        echo "  最小: ${http3_min}秒, 最大: ${http3_max}秒"
    else
        echo ""
        echo "HTTP/3: 全試行が失敗"
    fi
    
    echo ""
    echo "=== HTTP/2テスト (50回) ==="
    
    local http2_times=()
    local http2_speeds=()
    local http2_success=0
    local http2_total_time=0
    local http2_total_speed=0
    
    for i in $(seq 1 $ITERATIONS); do
        timestamp=$(date +%s)
        output=$(curl -k --http2 https://localhost:8444/1mb -o /dev/null -w "%{time_total} %{speed_download}" 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            read time speed <<< "$output"
            
            if [ ! -z "$time" ] && [ ! -z "$speed" ]; then
                speed_kb=$(echo "scale=2; $speed/1024" | bc)
                http2_times+=($time)
                http2_speeds+=($speed_kb)
                http2_total_time=$(echo "$http2_total_time + $time" | bc)
                http2_total_speed=$(echo "$http2_total_speed + $speed_kb" | bc)
                http2_success=$((http2_success + 1))
                
                echo "$timestamp,HTTP/2,$latency,$i,$time,$speed_kb,1" >> $OUTPUT_FILE
                
                if [ $((i % 10)) -eq 0 ]; then
                    echo "  進捗: $i/$ITERATIONS (${time}秒, ${speed_kb} KB/s)"
                fi
            else
                echo "$timestamp,HTTP/2,$latency,$i,,,0" >> $OUTPUT_FILE
            fi
        else
            echo "$timestamp,HTTP/2,$latency,$i,,,0" >> $OUTPUT_FILE
            if [ $((i % 10)) -eq 0 ]; then
                echo "  進捗: $i/$ITERATIONS (失敗)"
            fi
        fi
    done
    
    if [ $http2_success -gt 0 ]; then
        local http2_avg_time=$(echo "scale=3; $http2_total_time / $http2_success" | bc)
        local http2_avg_speed=$(echo "scale=2; $http2_total_speed / $http2_success" | bc)
        
        IFS=$'\n' sorted=($(printf '%s\n' "${http2_times[@]}" | sort -n))
        unset IFS
        local http2_min=${sorted[0]}
        local http2_max=${sorted[${#sorted[@]}-1]}
        local median_idx=$((http2_success / 2))
        local http2_median=${sorted[$median_idx]}
        
        echo ""
        echo "HTTP/2 結果:"
        echo "  成功: $http2_success/$ITERATIONS"
        echo "  平均時間: ${http2_avg_time}秒"
        echo "  平均速度: ${http2_avg_speed} KB/s"
        echo "  中央値: ${http2_median}秒"
        echo "  最小: ${http2_min}秒, 最大: ${http2_max}秒"
    else
        echo ""
        echo "HTTP/2: 全試行が失敗"
    fi
    
    echo ""
    echo "========================================="
    
    docker-compose -f "$PROJECT_ROOT/docker-compose.router_tc.yml" down 2>/dev/null
    sleep 2
}

run_benchmark "0ms" "1. 遅延 0ms (ベースライン)"
run_benchmark "25ms" "2. 遅延 25ms"
run_benchmark "50ms" "3. 遅延 50ms"
run_benchmark "75ms" "4. 遅延 75ms"
run_benchmark "100ms" "5. 遅延 100ms"
run_benchmark "125ms" "6. 遅延 125ms"
run_benchmark "150ms" "7. 遅延 150ms"
run_benchmark "175ms" "8. 遅延 175ms"
run_benchmark "200ms" "9. 遅延 200ms"

echo ""
echo "========================================="
echo "全ベンチマーク完了"
echo "========================================="
echo ""
echo "結果ファイル: $OUTPUT_FILE"
echo ""
echo "統計分析を実行中..."

if command -v python3 &> /dev/null; then
    python3 << EOF
import csv
import statistics

data = {'HTTP/2': {}, 'HTTP/3': {}}

with open('$OUTPUT_FILE', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['success'] == '1' and row['time_total']:
            protocol = row['protocol']
            latency = row['latency']
            time = float(row['time_total'])
            
            if latency not in data[protocol]:
                data[protocol][latency] = []
            data[protocol][latency].append(time)

print("\n=== 統計サマリー ===\n")
print(f"{'条件':<10} {'プロトコル':<8} {'成功数':<8} {'平均(秒)':<10} {'中央値(秒)':<12} {'標準偏差':<10}")
print("-" * 70)

for latency in ['0ms', '25ms', '50ms', '75ms', '100ms', '125ms', '150ms', '175ms', '200ms']:
    for protocol in ['HTTP/2', 'HTTP/3']:
        if latency in data[protocol] and len(data[protocol][latency]) > 0:
            times = data[protocol][latency]
            avg = statistics.mean(times)
            median = statistics.median(times)
            stdev = statistics.stdev(times) if len(times) > 1 else 0
            print(f"{latency:<10} {protocol:<8} {len(times):<8} {avg:<10.3f} {median:<12.3f} {stdev:<10.3f}")
        else:
            print(f"{latency:<10} {protocol:<8} {'0':<8} {'-':<10} {'-':<12} {'-':<10}")
    print()
EOF
else
    echo "Python3が見つかりません。CSVファイルを手動で分析してください。"
fi

echo ""
echo "詳細データ: $OUTPUT_FILE"

echo ""
echo "========================================="
echo "グラフを自動生成中..."
echo "========================================="

if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
    
    export BENCHMARK_CSV="$OUTPUT_FILE"
    export BENCHMARK_OUTPUT_DIR="$LOG_DIR"
    
    echo ""
    echo "1. 応答速度比較グラフを生成中..."
    python3 "$SCRIPT_DIR/visualize_response_time.py" 2>/dev/null
    
    echo ""
    echo "2. 安定性比較グラフを生成中..."
    python3 "$SCRIPT_DIR/visualize_stability.py" 2>/dev/null
    
    echo ""
    echo "3. 総合分析グラフを生成中..."
    python3 "$SCRIPT_DIR/visualize_results.py" 2>/dev/null
    
    echo ""
    echo "========================================="
    echo "グラフ生成完了！"
    echo "========================================="
    echo ""
    echo "保存場所: $LOG_DIR/"
    echo ""
    echo "生成されたファイル:"
    ls -lh "$LOG_DIR"/*.png "$LOG_DIR"/*.csv 2>/dev/null | awk '{print "  - " $9 " (" $5 ")"}'
    
    echo ""
    echo "グラフを開く場合:"
    echo "  open $LOG_DIR/response_time_comparison.png"
    echo "  open $LOG_DIR/stability_comparison.png"
    echo "  open $LOG_DIR/benchmark_visualization.png"
    echo "  open $LOG_DIR/benchmark_analysis.png"
else
    echo ""
    echo "※ グラフ生成をスキップしました（Python環境が見つかりません）"
    echo "  グラフを生成するには以下を実行してください:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install pandas matplotlib seaborn"
    echo "  python visualize_response_time.py"
fi

echo ""
