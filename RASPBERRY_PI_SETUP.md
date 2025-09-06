# Raspberry Pi 5 実機サーバー構築ガイド

## 概要
現在のDockerベースのベンチマーク環境を、Raspberry Pi 5を実機サーバーとして使用する構成に変更するための手順書です。

## 現在の構成
- **クライアント**: Dockerコンテナ (grpc-client)
- **ルーター**: Dockerコンテナ (grpc-router) - ネットワークエミュレーション
- **サーバー**: Dockerコンテナ (grpc-server)

## 変更後の構成
- **クライアント**: Dockerコンテナ (grpc-client) - 変更なし
- **ルーター**: Dockerコンテナ (grpc-router) - 変更なし
- **サーバー**: **Raspberry Pi 5実機（Docker不使用）** - 新規構築

## 必要な作業

### 1. Raspberry Pi 5 の準備

#### 1.1 ハードウェア要件
- Raspberry Pi 5 (推奨: 8GB RAM)
- microSDカード (32GB以上、Class 10以上)
- 電源アダプター (5V/3A以上)
- 有線LAN接続用ケーブル
- 冷却ファン（推奨）

#### 1.2 OS セットアップ
```bash
# Raspberry Pi OS (64-bit) のインストール
# 公式イメージ: https://www.raspberrypi.org/downloads/

# 初期設定
sudo raspi-config
# - SSH有効化
# - 有線LAN設定
# - ホスト名設定: grpc-server-pi
```

#### 1.3 ネットワーク設定（無線LAN）
```bash
# 無線LAN固定IP設定
sudo nano /etc/dhcpcd.conf

# 以下を追加（無線LANインターフェース）
interface wlan0
static ip_address=172.30.0.2/24
static routers=172.30.0.254
static domain_name_servers=8.8.8.8

# または、有線LANと無線LANの両方に対応
interface eth0
static ip_address=172.30.0.2/24
static routers=172.30.0.254
static domain_name_servers=8.8.8.8

interface wlan0
static ip_address=172.30.0.2/24
static routers=172.30.0.254
static domain_name_servers=8.8.8.8
```

**注意**: 無線LANと有線LANで同じIPアドレスを使用する場合は、同時に接続しないでください。

### 2. サーバーソフトウェアの構築

#### 2.1 必要なパッケージのインストール
```bash
# システム更新
sudo apt update && sudo apt upgrade -y

# 必要なパッケージ（Docker不使用）
sudo apt install -y \
    nginx \
    nginx-extras \
    curl \
    wget \
    git \
    build-essential \
    cmake \
    pkg-config \
    libssl-dev \
    libnghttp2-dev \
    libngtcp2-dev \
    libnghttp3-dev \
    libbrotli-dev \
    zlib1g-dev \
    libev-dev \
    libevent-dev \
    libjansson-dev \
    libc-ares-dev \
    libxml2-dev \
    libhiredis-dev \
    libmaxminddb-dev \
    liblmdb-dev \
    libcurl4-openssl-dev \
    libunistring-dev \
    libsqlite3-dev \
    libh2o-dev \
    libh2o-evloop-dev \
    htop \
    iotop \
    nethogs
```

#### 2.2 Nginx HTTP/3対応ビルド
```bash
# ソースディレクトリ作成
mkdir -p /opt/nginx-build
cd /opt/nginx-build

# Nginx ソースダウンロード
wget http://nginx.org/download/nginx-1.25.3.tar.gz
tar -xzf nginx-1.25.3.tar.gz

# HTTP/3対応Nginxビルド
cd nginx-1.25.3

./configure \
    --prefix=/etc/nginx \
    --sbin-path=/usr/sbin/nginx \
    --conf-path=/etc/nginx/nginx.conf \
    --error-log-path=/var/log/nginx/error.log \
    --http-log-path=/var/log/nginx/access.log \
    --pid-path=/var/run/nginx.pid \
    --lock-path=/var/run/nginx.lock \
    --http-client-body-temp-path=/var/cache/nginx/client_temp \
    --http-proxy-temp-path=/var/cache/nginx/proxy_temp \
    --http-fastcgi-temp-path=/var/cache/nginx/fastcgi_temp \
    --http-uwsgi-temp-path=/var/cache/nginx/uwsgi_temp \
    --http-scgi-temp-path=/var/cache/nginx/scgi_temp \
    --user=nginx \
    --group=nginx \
    --with-http_ssl_module \
    --with-http_realip_module \
    --with-http_addition_module \
    --with-http_sub_module \
    --with-http_dav_module \
    --with-http_flv_module \
    --with-http_mp4_module \
    --with-http_gunzip_module \
    --with-http_gzip_static_module \
    --with-http_random_index_module \
    --with-http_secure_link_module \
    --with-http_stub_status_module \
    --with-http_auth_request_module \
    --with-http_xslt_module=dynamic \
    --with-http_image_filter_module=dynamic \
    --with-http_geoip_module=dynamic \
    --with-threads \
    --with-stream \
    --with-stream_ssl_module \
    --with-stream_ssl_preread_module \
    --with-stream_realip_module \
    --with-stream_geoip_module=dynamic \
    --with-http_slice_module \
    --with-http_v2_module \
    --with-http_v3_module \
    --with-stream_geoip_module=dynamic \
    --with-http_geoip_module=dynamic

make -j4
sudo make install
```

#### 2.3 Nginx設定ファイル
```bash
# /etc/nginx/nginx.conf の設定
sudo nano /etc/nginx/nginx.conf
```

```nginx
user nginx;
worker_processes auto;
pid /run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # HTTP/3設定
    http3 on;
    http3_hq on;
    http3_stream_buffer_size 64k;

    # ログ設定
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'protocol=$server_protocol';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # パフォーマンス設定
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 16M;

    # gzip設定
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # サーバー設定
    server {
        listen 80;
        listen 443 ssl http2;
        listen 443 http3 reuseport;
        
        server_name grpc-server-pi.local;
        
        # SSL証明書設定
        ssl_certificate /etc/ssl/certs/grpc-server.crt;
        ssl_certificate_key /etc/ssl/private/grpc-server.key;
        
        # SSL設定
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        
        # HTTP/3設定
        add_header Alt-Svc 'h3=":443"; ma=86400';
        
        # ルート設定
        location / {
            root /var/www/html;
            index index.html index.htm;
            try_files $uri $uri/ =404;
        }
        
        # Echo エンドポイント
        location /echo {
            return 200 "Hello from Raspberry Pi 5 HTTP/3 server - $request_body";
            add_header Content-Type text/plain;
        }
        
        # ヘルスチェック
        location /health {
            return 200 "OK";
            add_header Content-Type text/plain;
        }
    }
}
```

#### 2.4 SSL証明書の生成
```bash
# 証明書ディレクトリ作成
sudo mkdir -p /etc/ssl/certs /etc/ssl/private

# 自己署名証明書生成
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/grpc-server.key \
    -out /etc/ssl/certs/grpc-server.crt \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=GRPC-Benchmark/OU=IT/CN=grpc-server-pi.local"

# 権限設定
sudo chmod 600 /etc/ssl/private/grpc-server.key
sudo chmod 644 /etc/ssl/certs/grpc-server.crt
```

#### 2.5 Nginxユーザー作成とサービス設定
```bash
# nginxユーザー作成
sudo useradd -r -s /bin/false nginx

# ログディレクトリ作成
sudo mkdir -p /var/log/nginx /var/cache/nginx
sudo chown -R nginx:nginx /var/log/nginx /var/cache/nginx

# systemdサービスファイル作成
sudo nano /etc/systemd/system/nginx.service
```

```ini
[Unit]
Description=The nginx HTTP and reverse proxy server
After=network.target remote-fs.target nss-lookup.target

[Service]
Type=forking
PIDFile=/run/nginx.pid
ExecStartPre=/usr/sbin/nginx -t
ExecStart=/usr/sbin/nginx
ExecReload=/bin/kill -s HUP $MAINPID
KillSignal=SIGQUIT
TimeoutStopSec=5
KillMode=process
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
# サービス有効化
sudo systemctl daemon-reload
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 3. ベンチマークスクリプトの修正

#### 3.1 新しいスクリプト作成
```bash
# Raspberry Pi用ベンチマークスクリプト
cp scripts/run_bench.sh scripts/run_bench_raspberry_pi.sh
```

#### 3.2 設定変更点
- `SERVER_IP`: `172.30.0.2` (Raspberry PiのIP)
- ネットワークエミュレーション: Dockerルーター経由
- 証明書検証: 自己署名証明書対応

### 4. ネットワーク設定

#### 4.1 Dockerネットワーク設定
```bash
# 既存のDockerネットワーク確認
docker network ls

# 必要に応じて新しいネットワーク作成
docker network create --subnet=172.30.0.0/24 grpc-benchmark
```

#### 4.2 ルーター設定の調整
```bash
# ルーターコンテナの設定確認
docker exec grpc-router ip route show
docker exec grpc-router iptables -L
```

### 5. テスト手順

#### 5.1 接続テスト
```bash
# Raspberry Piへの接続確認
ping 172.30.0.2

# HTTP/2接続テスト
curl -k --http2 https://172.30.0.2/echo

# HTTP/3接続テスト
curl -k --http3 https://172.30.0.2/echo
```

#### 5.2 ベンチマーク実行
```bash
# Raspberry Pi用ベンチマーク実行
./scripts/run_bench_raspberry_pi.sh
```

### 6. 監視とログ

#### 6.1 Raspberry Pi監視
```bash
# システムリソース監視
htop
iotop
nethogs

# Nginxログ監視
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

#### 6.2 ネットワーク監視
```bash
# ネットワーク統計
ss -tuln
netstat -i
```

### 7. トラブルシューティング

#### 7.1 よくある問題
1. **接続できない**: ファイアウォール設定確認
2. **SSL証明書エラー**: 証明書の有効性確認
3. **HTTP/3が動作しない**: Nginx設定とクライアント対応確認
4. **パフォーマンス低下**: 冷却とCPU使用率確認

#### 7.2 デバッグコマンド
```bash
# 接続確認
telnet 172.30.0.2 443

# SSL証明書確認
openssl s_client -connect 172.30.0.2:443 -servername grpc-server-pi.local

# HTTP/3確認
curl -k --http3 -v https://172.30.0.2/echo
```

### 8. 期待される効果

#### 8.1 実機環境での測定
- より現実的なネットワーク条件
- ハードウェア制約の影響測定
- 実際のデバイス間通信の特性

#### 8.2 パフォーマンス比較
- Docker vs 実機の性能差
- ネットワークスタックの違い
- リソース制約の影響

### 9. 次のステップ

1. Raspberry Pi 5のセットアップ完了
2. ベンチマークスクリプトの修正
3. 接続テストの実行
4. 本格的なベンチマーク実行
5. 結果の分析と比較

## 注意事項

- Raspberry Pi 5は十分な冷却が必要
- ネットワーク設定は慎重に行う
- セキュリティ設定（ファイアウォール等）を適切に設定
- 定期的なバックアップを推奨
