#!/bin/bash
# ベンチマーク実行前のシステム最適化スクリプト

echo "🚀 システム最適化を開始..."

# Dockerリソースのクリーンアップ
echo "🐳 Dockerリソースをクリーンアップ中..."
docker container prune -f
docker image prune -f
docker volume prune -f
docker builder prune -f
docker system prune -f

# メモリクリーンアップ（macOS）
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🧠 メモリをクリーンアップ中..."
    sudo purge
fi

# システム情報の表示
echo "📊 システム情報:"
echo "CPU使用率: $(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')"
echo "メモリ使用率: $(top -l 1 | grep "PhysMem" | awk '{print $2}' | sed 's/G//')"
echo "ディスク使用率: $(df -h / | tail -1 | awk '{print $5}')"

echo "✅ システム最適化完了！"
