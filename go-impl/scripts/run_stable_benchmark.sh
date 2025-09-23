#!/bin/bash

# 安定したベンチマーク実行スクリプト
# リソース固定化後にベンチマークを実行

echo "================================================"
echo "安定したベンチマーク実行スクリプト"
echo "================================================"

# 1. システムリソース固定化
echo "1. システムリソースを固定化中..."
./scripts/fix_resources.sh

# 2. Docker環境のリフレッシュ
echo ""
echo "2. Docker環境をリフレッシュ中..."
cd /Users/root1/Documents/Research/gRPC_over_HTTP3/go-impl

# 既存のコンテナを停止・削除
docker-compose down --remove-orphans

# システムリソースを再固定化
./scripts/fix_resources.sh

# 3. 固定化されたリソースでコンテナを起動
echo ""
echo "3. 固定化されたリソースでコンテナを起動中..."
docker-compose up -d

# 4. コンテナの起動を待機
echo ""
echo "4. コンテナの起動を待機中..."
sleep 30

# 5. ヘルスチェック
echo ""
echo "5. ヘルスチェックを実行中..."
echo "サーバー:"
curl -f http://localhost:8080/health || echo "サーバーヘルスチェック失敗"

echo "ルーター:"
curl -f http://localhost:8081/health || echo "ルーターヘルスチェック失敗"

# 6. システムリソース状態を確認
echo ""
echo "6. システムリソース状態を確認中..."
echo "CPU使用率:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1

echo "メモリ使用率:"
free | grep Mem | awk '{printf "%.1f%%\n", $3/$2 * 100.0}'

echo "ネットワークバッファサイズ:"
cat /proc/sys/net/core/rmem_max

# 7. ベンチマーク実行
echo ""
echo "7. ベンチマークを実行中..."
echo "================================================"

# ベンチマーク実行
docker exec go-grpc-client ./latency_benchmark

echo "================================================"
echo "ベンチマーク実行完了"
echo "================================================"

# 8. 実行後のリソース状態を確認
echo ""
echo "8. 実行後のリソース状態を確認中..."
echo "CPU使用率:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1

echo "メモリ使用率:"
free | grep Mem | awk '{printf "%.1f%%\n", $3/$2 * 100.0}'

echo "================================================"
echo "安定したベンチマーク実行完了"
echo "================================================"
