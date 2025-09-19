#!/bin/bash

# Go gRPC over HTTP/2/3 Benchmark Runner

set -e

echo "================================================"
echo "Go gRPC over HTTP/2/3 Benchmark"
echo "================================================"

# 環境起動
echo "Starting environment..."
docker-compose up -d

# ヘルスチェック待機
echo "Waiting for services to be ready..."
sleep 30

# ヘルスチェック
echo "Checking server health..."
if ! curl -f http://localhost:8080/health; then
    echo "Server health check failed"
    exit 1
fi

echo "Checking router health..."
if ! curl -f http://localhost:8081/health; then
    echo "Router health check failed"
    exit 1
fi

echo "Services are ready!"

# ベンチマーク実行
echo "Running benchmark..."
docker exec go-grpc-client ./client

echo "================================================"
echo "Benchmark completed!"
echo "================================================"

echo "Results are available in:"
echo "  ./logs/benchmark_*/"
echo ""
echo "To view logs:"
echo "  docker-compose logs"
echo ""
echo "To stop environment:"
echo "  docker-compose down"
