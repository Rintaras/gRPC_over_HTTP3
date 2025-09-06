# Cursor用 Raspberry Pi 5 サーバー構築ガイド

## プロジェクト概要

このプロジェクトは、**HTTP/2とHTTP/3の性能比較ベンチマーク**を実機環境で実施するためのRaspberry Pi 5サーバーを構築するものです。

### プロジェクトの目的
1. **HTTP/2 vs HTTP/3の性能比較**: 異なるネットワーク条件での性能測定
2. **実機環境での検証**: Docker環境と実機環境での性能差の測定
3. **ネットワークエミュレーション**: 遅延・パケットロス環境での性能評価
4. **自動化されたベンチマーク**: グラフ生成まで完全自動化

### 実験環境
- **クライアント側**: Docker環境（h2loadベンチマークツール）
- **サーバー側**: Raspberry Pi 5実機（Nginx HTTP/2/3対応）
- **ネットワーク**: 物理ネットワーク（無線LAN/有線LAN）
- **エミュレーション**: Dockerルーターでtc netemを使用

### 測定項目
- 平均応答時間
- スループット
- パケットロス耐性
- 遅延環境での性能
- プロトコル別の性能差

Docker環境のクライアントからRaspberry Pi 5実機サーバーに対して通信テストを行い、グラフ生成まで自動化します。

## 技術要件

### サーバー側（Raspberry Pi 5）
- **OS**: Raspberry Pi OS (64-bit)
- **Webサーバー**: Nginx (HTTP/2 + HTTP/3対応)
- **プロトコル**: HTTP/2, HTTP/3 (QUIC)
- **SSL/TLS**: 自己署名証明書
- **ネットワーク**: 無線LAN (wlan0) または有線LAN (eth0)
- **IPアドレス**: 172.30.0.2/24
- **ポート**: 443 (HTTP/2とHTTP/3共用)

### クライアント側（Docker環境）
- **クライアント**: h2load (HTTP/2/3 ベンチマークツール)
- **ルーター**: Dockerコンテナ（ネットワークエミュレーション）
- **ネットワーク**: Docker Bridge Network
- **エミュレーション**: tc (Traffic Control)

## 構築手順

### 1. 初期セットアップ

#### 1.1 システム更新
```bash
sudo apt update && sudo apt upgrade -y
```

#### 1.2 必要なパッケージのインストール
```bash
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
    nethogs \
    systemd
```

### 2. ネットワーク設定

#### 2.1 固定IP設定
```bash
# 設定ファイルを編集
sudo nano /etc/dhcpcd.conf

# 無線LANの場合
interface wlan0
static ip_address=172.30.0.2/24
static routers=172.30.0.254
static domain_name_servers=8.8.8.8

# 有線LANの場合（必要に応じて）
interface eth0
static ip_address=172.30.0.2/24
static routers=172.30.0.254
static domain_name_servers=8.8.8.8
```

#### 2.2 設定の適用
```bash
sudo systemctl restart dhcpcd
```

### 3. Nginx HTTP/3対応ビルド

#### 3.1 ソースダウンロード
```bash
mkdir -p /opt/nginx-build
cd /opt/nginx-build
wget http://nginx.org/download/nginx-1.25.3.tar.gz
tar -xzf nginx-1.25.3.tar.gz
cd nginx-1.25.3
```

#### 3.2 ビルド設定
```bash
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
```

#### 3.3 ビルド実行
```bash
make -j4
sudo make install
```

### 4. SSL証明書生成

#### 4.1 証明書ディレクトリ作成
```bash
sudo mkdir -p /etc/ssl/certs /etc/ssl/private
```

#### 4.2 自己署名証明書生成
```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/grpc-server.key \
    -out /etc/ssl/certs/grpc-server.crt \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=GRPC-Benchmark/OU=IT/CN=grpc-server-pi.local"
```

#### 4.3 権限設定
```bash
sudo chmod 600 /etc/ssl/private/grpc-server.key
sudo chmod 644 /etc/ssl/certs/grpc-server.crt
```

### 5. Nginx設定

#### 5.1 ユーザー作成
```bash
sudo useradd -r -s /bin/false nginx
```

#### 5.2 ディレクトリ作成
```bash
sudo mkdir -p /var/log/nginx /var/cache/nginx
sudo chown -R nginx:nginx /var/log/nginx /var/cache/nginx
```

#### 5.3 Nginx設定ファイル
```bash
sudo nano /etc/nginx/nginx.conf
```

設定内容:
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

### 6. システムサービス設定

#### 6.1 systemdサービスファイル
```bash
sudo nano /etc/systemd/system/nginx.service
```

設定内容:
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

#### 6.2 サービス有効化
```bash
sudo systemctl daemon-reload
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 7. ファイアウォール設定

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS/HTTP2/HTTP3
sudo ufw --force enable
```

### 8. テスト用HTMLページ作成

```bash
sudo nano /var/www/html/index.html
```

設定内容:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Raspberry Pi 5 HTTP/3 Server</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>Raspberry Pi 5 HTTP/3 Server</h1>
    <p>This server supports both HTTP/2 and HTTP/3 protocols.</p>
    <h2>Available Endpoints:</h2>
    <ul>
        <li><a href="/health">/health</a> - Health check</li>
        <li><a href="/echo">/echo</a> - Echo service</li>
    </ul>
    <h2>Protocol Support:</h2>
    <ul>
        <li>HTTP/2 (TLS)</li>
        <li>HTTP/3 (QUIC)</li>
    </ul>
</body>
</html>
```

### 9. 監視スクリプト作成

```bash
sudo nano /usr/local/bin/monitor_raspberry_pi.sh
```

設定内容:
```bash
#!/bin/bash

echo "=== Raspberry Pi 5 System Status ==="
echo "Date: $(date)"
echo ""

echo "=== Network Interface ==="
if ip link show wlan0 > /dev/null 2>&1; then
    echo "Active interface: wlan0"
    ip addr show wlan0 | grep inet
    iwconfig wlan0 | grep -E "(ESSID|Signal|Quality)"
else
    echo "Active interface: eth0"
    ip addr show eth0 | grep inet
fi

echo ""
echo "=== CPU Usage ==="
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}'

echo ""
echo "=== Memory Usage ==="
free -h

echo ""
echo "=== Disk Usage ==="
df -h

echo ""
echo "=== Network Statistics ==="
ss -tuln | grep :443

echo ""
echo "=== Nginx Status ==="
systemctl is-active nginx

echo ""
echo "=== Active Connections ==="
ss -tuln | grep :443 | wc -l
```

```bash
sudo chmod +x /usr/local/bin/monitor_raspberry_pi.sh
```

### 10. ログローテーション設定

```bash
sudo nano /etc/logrotate.d/nginx
```

設定内容:
```
/var/log/nginx/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 640 nginx adm
    sharedscripts
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 `cat /var/run/nginx.pid`
        fi
    endscript
}
```

## 動作確認

### 1. サービス状態確認
```bash
sudo systemctl status nginx
```

### 2. ポート確認
```bash
sudo ss -tuln | grep :443
```

### 3. HTTP/2テスト
```bash
curl -k --http2 https://localhost/health
```

### 4. HTTP/3テスト
```bash
curl -k --http3 https://localhost/health
```

### 5. 外部からの接続テスト
```bash
# クライアント側から
curl -k --http2 https://172.30.0.2/health
curl -k --http3 https://172.30.0.2/health
```

## トラブルシューティング

### 1. 接続できない場合
- ファイアウォール設定確認
- IPアドレス設定確認
- ネットワーク接続確認

### 2. SSL証明書エラー
- 証明書の有効性確認
- 権限設定確認

### 3. HTTP/3が動作しない
- Nginx設定確認
- クライアント対応確認

### 4. パフォーマンス低下
- システムリソース確認
- ネットワーク設定確認

## 期待される結果

構築完了後、以下の機能が利用可能になります：

1. **HTTP/2サーバー**: ポート443でHTTP/2通信
2. **HTTP/3サーバー**: ポート443でHTTP/3通信
3. **SSL/TLS暗号化**: 自己署名証明書による暗号化
4. **ヘルスチェック**: `/health`エンドポイント
5. **エコーサービス**: `/echo`エンドポイント
6. **監視機能**: システム状態の監視
7. **ログ機能**: アクセスログとエラーログ

これにより、Docker環境のクライアントからRaspberry Pi 5実機サーバーに対してHTTP/2とHTTP/3の性能比較ベンチマークが実行可能になります。
