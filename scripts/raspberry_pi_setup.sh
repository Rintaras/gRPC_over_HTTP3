#!/bin/bash

# Raspberry Pi 5 Setup Script for gRPC over HTTP/3 Benchmark
# This script should be run on the Raspberry Pi 5

echo "================================================"
echo "Raspberry Pi 5 Setup for gRPC over HTTP/3 Benchmark"
echo "================================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install required packages
echo "Installing required packages..."
apt install -y \
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

# Create nginx user
echo "Creating nginx user..."
useradd -r -s /bin/false nginx

# Create necessary directories
echo "Creating directories..."
mkdir -p /var/log/nginx
mkdir -p /var/cache/nginx
mkdir -p /var/www/html
mkdir -p /etc/ssl/certs
mkdir -p /etc/ssl/private

# Set permissions
chown -R nginx:nginx /var/log/nginx
chown -R nginx:nginx /var/cache/nginx
chown -R www-data:www-data /var/www/html

# Generate SSL certificate
echo "Generating SSL certificate..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/grpc-server.key \
    -out /etc/ssl/certs/grpc-server.crt \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=GRPC-Benchmark/OU=IT/CN=grpc-server-pi.local"

# Set certificate permissions
chmod 600 /etc/ssl/private/grpc-server.key
chmod 644 /etc/ssl/certs/grpc-server.crt

# Create nginx configuration
echo "Creating nginx configuration..."
cat > /etc/nginx/nginx.conf << 'EOF'
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
EOF

# Create systemd service file
echo "Creating systemd service..."
cat > /etc/systemd/system/nginx.service << 'EOF'
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
EOF

# Create default HTML page
echo "Creating default HTML page..."
cat > /var/www/html/index.html << 'EOF'
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
EOF

# Enable and start nginx
echo "Enabling and starting nginx..."
systemctl daemon-reload
systemctl enable nginx
systemctl start nginx

# Check nginx status
echo "Checking nginx status..."
systemctl status nginx --no-pager

# Test HTTP/2 and HTTP/3
echo "Testing HTTP/2..."
curl -k --http2 https://localhost/health

echo "Testing HTTP/3..."
curl -k --http3 https://localhost/health

# Configure firewall (if ufw is installed)
if command -v ufw > /dev/null; then
    echo "Configuring firewall..."
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
fi

# Set up monitoring script
echo "Creating monitoring script..."
cat > /usr/local/bin/monitor_raspberry_pi.sh << 'EOF'
#!/bin/bash

echo "=== Raspberry Pi 5 System Status ==="
echo "Date: $(date)"
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
EOF

chmod +x /usr/local/bin/monitor_raspberry_pi.sh

# Create log rotation for nginx
echo "Setting up log rotation..."
cat > /etc/logrotate.d/nginx << 'EOF'
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
EOF

echo "================================================"
echo "Raspberry Pi 5 setup completed!"
echo "================================================"
echo "Server IP: $(hostname -I | awk '{print $1}')"
echo "Nginx Status: $(systemctl is-active nginx)"
echo "HTTP/2 Test: curl -k --http2 https://localhost/health"
echo "HTTP/3 Test: curl -k --http3 https://localhost/health"
echo "================================================"
echo "Next steps:"
echo "1. Configure static IP address"
echo "2. Update /etc/hosts on client machine"
echo "3. Run benchmark script from client machine"
echo "================================================"
