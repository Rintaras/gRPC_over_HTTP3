#!/bin/bash
# システムリソース監視スクリプト

echo "📊 システムリソース監視を開始..."

while true; do
    echo "=== $(date) ==="
    
    # CPU使用率
    cpu_usage=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
    echo "CPU使用率: ${cpu_usage}%"
    
    # メモリ使用率
    memory_usage=$(top -l 1 | grep "PhysMem" | awk '{print $2}' | sed 's/G//')
    echo "メモリ使用率: ${memory_usage}%"
    
    # ディスク使用率
    disk_usage=$(df -h / | tail -1 | awk '{print $5}')
    echo "ディスク使用率: ${disk_usage}"
    
    # Dockerコンテナ状況
    echo "Dockerコンテナ:"
    docker ps --format "table {{.Names}}	{{.Status}}	{{.Ports}}"
    
    echo "---"
    sleep 5
done
