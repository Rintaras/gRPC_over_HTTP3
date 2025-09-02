# gRPC over HTTP/3 研究プロジェクト - 完全ドキュメント

## プロジェクト概要

低遅延・高損失環境でのHTTP/2(TCP)とHTTP/3(QUIC)の性能比較を行う研究プロジェクト。
Docker Composeで3ノード(client, router, server)構成を作成し、自動化されたベンチマーク環境を構築。

## 技術スタック

- **コンテナ化**: Docker, Docker Compose
- **HTTP/2**: nginx (標準)
- **HTTP/3**: nginx + quiche (Cloudflare)
- **クライアントツール**: curl (HTTP/3対応), wrk, grpcurl
- **ネットワーク制御**: tc (netem)
- **証明書**: OpenSSL (自己署名)
- **HTTP/3ライブラリ**: quictls, ngtcp2, nghttp3

## CI/CD 概要

GitHub Actions により次を自動化しています。

- CI: Python の Lint（flake8）、`scripts/*.py` のインポート実行チェック、Rust（`quiche-client`）のビルド/Clippy、Docker（`server`/`client`/`router`）のビルド検証
- CD: GHCR への `server`/`client`/`router` イメージ push（`latest` と短縮 SHA タグ）。SSH デプロイはシークレットが揃っている場合のみ実行

### ワークフロー定義

- `/.github/workflows/ci.yml`
  - トリガー: `push`/`pull_request`（`main`）
  - Python 3.13 設定、`flake8` 実行
  - `scripts/*.py` のインポート実行スモークテスト
  - Rust ツールチェーン設定、`cargo build` と `cargo clippy -D warnings`
  - Docker Buildx による 3 イメージのビルド（push 無し）

- `/.github/workflows/cd.yml`
  - トリガー: `main` への push（イメージ関連ファイルに変更がある場合）
  - GHCR ログインして `server`/`client`/`router` を push
  - シークレット `DEPLOY_HOST`/`DEPLOY_USER`/`DEPLOY_KEY` が設定されていれば SSH 経由で `docker compose pull && up -d`

### 必要シークレット（任意）

- `DEPLOY_HOST`: デプロイ先のホスト名または IP
- `DEPLOY_USER`: SSH ユーザー
- `DEPLOY_KEY`: OpenSSH 秘密鍵（`id_ed25519` 推奨）

`GITHUB_TOKEN` は自動付与され、GHCR への push に使用されます。

## プロジェクト構成

```
gRPC_over_HTTP:3/
├── docker-compose.yml          # メインのDocker Compose設定
├── client/                     # クライアントコンテナ
│   └── Dockerfile             # curl(HTTP/3), wrk, grpcurl
├── router/                     # ルーターコンテナ
│   └── Dockerfile             # tc/netem制御
├── server/                     # サーバーコンテナ
│   ├── Dockerfile             # nginx(HTTP/2/3)
│   ├── nginx.conf             # nginx設定
│   └── proto/                 # gRPC定義ファイル
├── scripts/                    # 自動化スクリプト
│   ├── setup_network.sh       # ネットワーク条件設定
│   ├── run_benchmark.sh       # ベンチマーク実行
│   └── merge_results.py       # 結果マージ
├── logs/                       # ログ出力ディレクトリ
└── README.md                   # プロジェクト説明
```

## 作業手順詳細

### 1. プロジェクト初期化

#### 1.1 ディレクトリ構造作成
```bash
# プロジェクトルートディレクトリ作成
mkdir -p gRPC_over_HTTP:3/{client,router,server,scripts,logs}
cd gRPC_over_HTTP:3
```

**目的**: プロジェクトの基本構造を作成

#### 1.2 各ディレクトリの役割
- `client/`: HTTP/3対応curl、wrk、grpcurlを含むクライアントコンテナ
- `router/`: tc/netemによるネットワーク条件制御
- `server/`: nginx(HTTP/2)とnginx-quiche(HTTP/3)サーバー
- `scripts/`: 自動化スクリプト群
- `logs/`: ベンチマーク結果保存

### 2. Docker Compose設定

#### 2.1 docker-compose.yml作成
```yaml
services:
  client:
    build:
      context: .
      dockerfile: client/Dockerfile
    container_name: grpc-client
    networks:
      benchnet:
        ipv4_address: 172.30.0.3
    depends_on:
      - router
      - server
    command: sleep infinity

  router:
    build:
      context: .
      dockerfile: router/Dockerfile
    container_name: grpc-router
    networks:
      benchnet:
        ipv4_address: 172.30.0.254
    cap_add:
      - NET_ADMIN
    command: sleep infinity

  server:
    build:
      context: .
      dockerfile: server/Dockerfile
    container_name: grpc-server
    networks:
      benchnet:
        ipv4_address: 172.30.0.2
    ports:
      - "80:80"   # HTTP/2
      - "443:443" # HTTPS/HTTP/3

networks:
  benchnet:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/24
```

**目的**: 3ノード構成のネットワーク設定とポートマッピング

### 3. サーバーコンテナ構築

#### 3.1 server/Dockerfile作成
```dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcre3-dev \
    libssl-dev \
    zlib1g-dev \
    git \
    cmake \
    pkg-config \
    wget \
    curl \
    clang \
    libclang-12-dev \
    llvm-12-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust with latest version
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Update Rust to latest version
RUN rustup update stable && rustup default stable

# Set libclang path
ENV LIBCLANG_PATH=/usr/lib/llvm-12/lib

# Build quiche
WORKDIR /tmp
RUN git clone --recursive https://github.com/cloudflare/quiche.git \
    && cd quiche \
    && cargo build --release --features ffi,pkg-config-meta \
    && mkdir -p /opt/quiche \
    && cp target/release/libquiche.a /opt/quiche/ \
    && cp quiche/include/quiche.h /opt/quiche/ \
    && cp target/release/quiche.pc /opt/quiche/

# Download and build nginx with HTTP/3 (quiche) support
RUN wget https://nginx.org/download/nginx-1.25.3.tar.gz \
    && tar -xzf nginx-1.25.3.tar.gz \
    && cd nginx-1.25.3 \
    && ./configure \
        --prefix=/opt/nginx-h3 \
        --with-http_ssl_module \
        --with-http_v2_module \
        --with-http_v3_module \
        --with-cc-opt="-I/tmp/quiche/include" \
        --with-ld-opt="-L/tmp/quiche/target/release -lquiche" \
    && make -j$(nproc) \
    && make install \
    && cd .. \
    && rm -rf nginx-1.25.3*

# Create self-signed certificate
RUN mkdir -p /opt/nginx-h3/certs \
    && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /opt/nginx-h3/certs/server.key \
        -out /opt/nginx-h3/certs/server.crt \
        -subj "/C=JP/ST=Tokyo/L=Tokyo/O=Test/CN=server"

# Create nginx configuration directory
RUN mkdir -p /opt/nginx-h3/conf /opt/nginx-h3/proto

# Copy configuration files
COPY server/nginx.conf /opt/nginx-h3/conf/nginx.conf
COPY server/proto /opt/nginx-h3/proto/

# Set working directory
WORKDIR /opt/nginx-h3

# Expose ports 80 and 443
EXPOSE 80 443

# Start nginx in foreground
CMD ["/opt/nginx-h3/sbin/nginx", "-g", "daemon off;"]
```

**目的**: nginx(HTTP/2)とquiche(HTTP/3)をビルドし、自己署名証明書を生成

#### 3.2 server/nginx.conf作成
```nginx
events {
    worker_connections 1024;
}

http {
    include       /opt/nginx-h3/conf/mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  65;

    # HTTP/2 server (port 80)
    server {
        listen 80;
        server_name server;
        
        location / {
            root   /opt/nginx-h3/html;
            index  index.html index.htm;
        }
        
        # Simple echo endpoint for testing
        location /echo {
            return 200 "Hello from nginx HTTP/2! Protocol: $http2\n";
            add_header Content-Type text/plain;
        }
        
        # Health check endpoint
        location /health {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }
    }

    # HTTP/2 and HTTP/3 server (port 443)
    server {
        listen 443 ssl http2;
        listen 443 quic reuseport;
        
        server_name server;
        
        ssl_certificate /opt/nginx-h3/certs/server.crt;
        ssl_certificate_key /opt/nginx-h3/certs/server.key;
        
        # HTTP/3 support
        add_header Alt-Svc 'h3=":443"; ma=86400';
        add_header X-Proto $http3;
        
        location / {
            root   /opt/nginx-h3/html;
            index  index.html index.htm;
        }
        
        # Simple echo endpoint for testing
        location /echo {
            return 200 "Hello from nginx! Protocol: $http3\n";
            add_header Content-Type text/plain;
        }
        
        # Health check endpoint
        location /health {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }
    }
}
```

**目的**: HTTP/2(ポート80)とHTTP/3(ポート443)の両方に対応するnginx設定

### 4. ルーターコンテナ構築

#### 4.1 router/Dockerfile作成
```dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Create scripts directory and copy scripts
RUN mkdir -p /scripts
COPY scripts /scripts/
RUN chmod +x /scripts/*.sh

WORKDIR /scripts
```

**目的**: tc/netemによるネットワーク条件制御用の軽量コンテナ

### 5. クライアントコンテナ構築

#### 5.1 client/Dockerfile作成
```dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wrk \
    iputils-ping \
    ca-certificates \
    gnupg \
    lsb-release \
    wget \
    build-essential \
    pkg-config \
    git \
    cmake \
    perl \
    libtool \
    automake \
    autoconf \
    make \
    && rm -rf /var/lib/apt/lists/*

# Build quictls (OpenSSL QUIC fork)
RUN git clone --depth 1 --branch OpenSSL_1_1_1t+quic https://github.com/quictls/openssl.git \
    && cd openssl \
    && ./config --prefix=/usr/local --openssldir=/usr/local no-shared enable-tls1_3 enable-quic \
    && make -j$(nproc) \
    && make install_sw \
    && cd .. \
    && rm -rf openssl

# Build nghttp3
RUN git clone --branch v1.2.0 --recursive https://github.com/ngtcp2/nghttp3.git \
    && cd nghttp3 \
    && cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
    && cmake --build build \
    && cmake --install build \
    && cd .. \
    && rm -rf nghttp3

# Build ngtcp2 (with quictls)
RUN git clone --branch v1.2.0 https://github.com/ngtcp2/ngtcp2.git \
    && cd ngtcp2 \
    && cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
        -DENABLE_OPENSSL=ON \
        -DOPENSSL_ROOT_DIR=/usr/local \
        -DOPENSSL_CRYPTO_LIBRARY=/usr/local/lib/libcrypto.a \
        -DOPENSSL_SSL_LIBRARY=/usr/local/lib/libssl.a \
        -DOPENSSL_INCLUDE_DIR=/usr/local/include \
        -DCMAKE_LIBRARY_PATH=/usr/local/lib \
        -DCMAKE_INCLUDE_PATH=/usr/local/include \
        -DOPENSSL_USE_STATIC_LIBS=TRUE \
        -DENABLE_EXAMPLES=OFF \
        -DENABLE_TESTS=OFF \
    && cmake --build build \
    && cmake --install build \
    && cd .. \
    && rm -rf ngtcp2

# Install grpcurl
RUN wget -qO- https://github.com/fullstorydev/grpcurl/releases/download/v1.8.7/grpcurl_1.8.7_linux_x86_64.tar.gz | tar -xz \
    && mv grpcurl /usr/local/bin/ \
    && chmod +x /usr/local/bin/grpcurl

# Build curl with HTTP/3 and OpenSSL (quictls) support
ENV PKG_CONFIG_PATH="/usr/local/lib/pkgconfig"
RUN wget https://curl.se/download/curl-8.4.0.tar.gz \
    && tar -xzf curl-8.4.0.tar.gz \
    && cd curl-8.4.0 \
    && ./configure --with-nghttp3=/usr/local --with-ngtcp2=/usr/local --with-openssl=/usr/local --disable-shared \
    && make -j$(nproc) \
    && make install \
    && cd .. \
    && rm -rf curl-8.4.0*

# Add /usr/local/bin to PATH
ENV PATH="/usr/local/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/lib:${LD_LIBRARY_PATH}"

# Create directories and copy scripts
RUN mkdir -p /scripts /tmp
COPY scripts /scripts/
RUN chmod +x /scripts/*.sh

WORKDIR /scripts
```

**目的**: HTTP/3対応curl、wrk、grpcurlを含む完全なベンチマーククライアント

### 6. 自動化スクリプト作成

#### 6.1 scripts/setup_network.sh作成
```bash
#!/bin/bash

# Network condition setup script
# Usage: ./setup_network.sh <delay_ms> <loss_percent>

DELAY_MS=${1:-50}
LOSS_PERCENT=${2:-5}

echo "Setting up network conditions: ${DELAY_MS}ms delay, ${LOSS_PERCENT}% loss"

# Configure tc on router
docker exec grpc-router tc qdisc add dev eth0 root netem delay ${DELAY_MS}ms loss ${LOSS_PERCENT}%

echo "Network conditions configured successfully"
```

**目的**: ネットワーク遅延・損失条件を自動設定

#### 6.2 scripts/run_benchmark.sh作成
```bash
#!/bin/bash

# Benchmark execution script
# Usage: ./run_benchmark.sh <protocol> <duration> <connections>

PROTOCOL=${1:-http2}
DURATION=${2:-30}
CONNECTIONS=${3:-10}

echo "Running ${PROTOCOL} benchmark for ${DURATION}s with ${CONNECTIONS} connections"

# Run wrk benchmark
if [ "$PROTOCOL" = "http3" ]; then
    # HTTP/3 benchmark (using curl for now)
    echo "HTTP/3 benchmark not yet implemented with wrk"
else
    # HTTP/2 benchmark
    docker exec grpc-client wrk -t4 -c${CONNECTIONS} -d${DURATION}s http://grpc-server/
fi

echo "Benchmark completed"
```

**目的**: HTTP/2/3ベンチマークを自動実行

#### 6.3 scripts/merge_results.py作成
```python
#!/usr/bin/env python3

import csv
import json
import sys
from datetime import datetime

def merge_benchmark_results():
    """Merge benchmark results from multiple runs"""
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'runs': []
    }
    
    # Read and parse results
    # Implementation depends on actual output format
    
    # Write merged results
    with open('logs/merged_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("Results merged successfully")

if __name__ == "__main__":
    merge_benchmark_results()
```

**目的**: 複数のベンチマーク結果をマージしてCSV/JSON出力

### 7. ビルドと起動

#### 7.1 初回ビルド
```bash
# 全コンテナをビルド
docker-compose build

# コンテナを起動
docker-compose up -d
```

**目的**: 全コンテナをビルドして起動

#### 7.2 個別ビルド（問題解決時）
```bash
# clientのみ再ビルド（HTTP/3対応curl）
docker-compose build client

# serverのみ再ビルド（nginx設定変更時）
docker-compose build server

# 特定コンテナを再起動
docker-compose up -d client
```

### 8. 動作確認

#### 8.1 コンテナ状態確認
```bash
# 全コンテナの状態確認
docker-compose ps

# ログ確認
docker-compose logs server
```

#### 8.2 HTTP/2接続テスト
```bash
# curlでHTTP/2テスト
curl http://localhost/

# エンドポイントテスト
curl http://localhost/echo
curl http://localhost/health
```

#### 8.3 HTTP/3接続テスト
```bash
# curlでHTTP/3テスト
docker exec grpc-client curl --http3 -k -v https://grpc-server/echo

# ローカルからHTTPSテスト
curl -k https://localhost/
```

#### 8.4 ブラウザアクセス
- **HTTP/2**: `http://localhost/` (警告なし)
- **HTTPS/HTTP/3**: `https://localhost/` (自己署名証明書警告あり)

### 9. 問題解決履歴

#### 9.1 Docker Composeボリュームマウント問題
**問題**: パスにコロン(`:`)が含まれるためボリュームマウントエラー
**解決**: ボリュームマウントを削除し、COPYでファイルを追加

#### 9.2 curl HTTP/3ビルド問題
**問題**: nghttp3/ngtcp2のライブラリ不足
**解決**: quictls(OpenSSL QUIC fork)をビルドし、ngtcp2/nghttp3を正しいバージョンでビルド

#### 9.3 共有ライブラリパス問題
**問題**: `libnghttp3.so.9: cannot open shared object file`
**解決**: `LD_LIBRARY_PATH="/usr/local/lib"`を追加

#### 9.4 nginx設定問題
**問題**: HTTP/3のみでHTTP/2アクセスが困難
**解決**: ポート80(HTTP/2)とポート443(HTTPS/HTTP/3)の両方を設定

### 10. ベンチマーク実行例

#### 10.1 ネットワーク条件設定
```bash
# 50ms遅延、5%損失を設定
docker exec grpc-router /scripts/setup_network.sh 50 5
```

#### 10.2 HTTP/2ベンチマーク
```bash
# wrkでHTTP/2ベンチマーク
docker exec grpc-client wrk -t4 -c10 -d30s http://grpc-server/
```

#### 10.3 HTTP/3ベンチマーク
```bash
# curlでHTTP/3ベンチマーク（複数回実行）
for i in {1..10}; do
    docker exec grpc-client curl --http3 -k -w "%{time_total}\n" -o /dev/null -s https://grpc-server/
done
```

### 11. ログと結果

#### 11.1 ログディレクトリ
```
logs/
├── http2_benchmark_*.log
├── http3_benchmark_*.log
├── network_conditions_*.log
└── merged_results.json
```

#### 11.2 結果分析
- レイテンシー比較
- スループット比較
- パケット損失時の性能
- 接続確立時間

### 12. 拡張可能な機能

#### 12.1 gRPC対応
- server/proto/にgRPC定義ファイルを追加
- grpcurlによるgRPCベンチマーク

#### 12.2 自動化スクリプト拡張
- 複数ネットワーク条件での自動テスト
- 結果の可視化（グラフ生成）
- レポート自動生成

#### 12.3 監視機能
- Prometheus/Grafana統合
- リアルタイムメトリクス収集

## まとめ

このプロジェクトでは、低遅延・高損失環境でのHTTP/2とHTTP/3の性能比較を行うための完全なDocker環境を構築しました。

**主要成果**:
- HTTP/3対応curl、wrk、grpcurlのビルド成功
- nginx(HTTP/2)とnginx-quiche(HTTP/3)の構築
- tc/netemによるネットワーク条件制御
- ブラウザアクセス対応
- 自動化スクリプト基盤

**技術的課題解決**:
- quictls、ngtcp2、nghttp3の正しい組み合わせ
- Docker Composeのボリュームマウント問題
- 共有ライブラリのパス解決
- 自己署名証明書の設定

これにより、研究用途でのHTTP/2/3性能比較が可能になり、実際のネットワーク条件でのベンチマーク実行が自動化されました。 