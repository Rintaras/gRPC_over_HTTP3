#!/bin/bash

# Go gRPC over HTTP/2/3 Environment Build Script

set -e

echo "================================================"
echo "Building Go gRPC over HTTP/2/3 Environment"
echo "================================================"

# ディレクトリ移動
cd "$(dirname "$0")/.."

echo "Building Docker images..."

# Dockerイメージをビルド
docker-compose build

echo "================================================"
echo "Build completed successfully!"
echo "================================================"

echo "To start the environment:"
echo "  docker-compose up -d"
echo ""
echo "To run benchmarks:"
echo "  docker exec go-grpc-client ./client"
echo ""
echo "To check health:"
echo "  curl http://localhost:8080/health  # Server"
echo "  curl http://localhost:8081/health  # Router"
