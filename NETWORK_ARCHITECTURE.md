# ネットワークアーキテクチャ - Raspberry Pi 5実機サーバー構成

## 通信の仕組み

### 全体構成

```
┌─────────────────────────────────────────────────────────────────┐
│                        クライアント側（Docker環境）                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │   grpc-client   │    │   grpc-router   │                    │
│  │   (Docker)      │◄──►│   (Docker)      │                    │
│  │   h2load        │    │   tc netem      │                    │
│  │   HTTP/2 & /3   │    │   Network       │                    │
│  └─────────────────┘    │   Emulation     │                    │
│                         └─────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ 物理ネットワーク接続
                                │ (有線LAN)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Raspberry Pi 5実機サーバー                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                nginx (ネイティブインストール)                │ │
│  │                HTTP/2 + HTTP/3対応                         │ │
│  │                IP: 172.30.0.2:443                         │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 詳細な通信フロー

### 1. ネットワーク設定

#### クライアント側（Docker環境）
```bash
# Dockerネットワーク設定
docker network create --subnet=172.30.0.0/24 grpc-benchmark

# コンテナ起動
docker-compose up -d

# ネットワーク確認
docker network inspect grpc-benchmark
```

#### Raspberry Pi 5側（ネイティブ環境）
```bash
# 固定IP設定
sudo nano /etc/dhcpcd.conf

# 以下を追加
interface eth0
static ip_address=172.30.0.2/24
static routers=172.30.0.254
static domain_name_servers=8.8.8.8
```

### 2. 通信経路

#### 物理的な接続
1. **有線LAN接続**: Raspberry Pi 5とクライアントマシンを同じLANに接続
2. **IPアドレス割り当て**:
   - Raspberry Pi 5: `172.30.0.2/24`
   - Dockerルーター: `172.30.0.254/24`
   - Dockerクライアント: `172.30.0.x/24` (動的割り当て)

#### 論理的な通信フロー
```
クライアント (172.30.0.x) 
    ↓ HTTP/2 or HTTP/3
ルーター (172.30.0.254) 
    ↓ ネットワークエミュレーション (tc netem)
物理ネットワーク (有線LAN)
    ↓
Raspberry Pi 5 (172.30.0.2:443)
```

### 3. プロトコル別の通信詳細

#### HTTP/2通信
```bash
# クライアント側での実行
docker exec grpc-client h2load \
    --connect-to 172.30.0.2:443 \
    --insecure \
    https://172.30.0.2/echo
```

**通信の流れ**:
1. TLS 1.3ハンドシェイク
2. HTTP/2接続確立
3. ストリーム作成
4. リクエスト送信
5. レスポンス受信

#### HTTP/3通信
```bash
# クライアント側での実行
docker exec grpc-client h2load \
    --connect-to 172.30.0.2:443 \
    --alpn-list=h3,h2 \
    --insecure \
    https://172.30.0.2/echo
```

**通信の流れ**:
1. QUIC接続確立（UDP上）
2. TLS 1.3ハンドシェイク（QUIC内）
3. HTTP/3ストリーム作成
4. リクエスト送信
5. レスポンス受信

### 4. ネットワークエミュレーション

#### ルーターコンテナでの設定
```bash
# 遅延とパケットロスの設定
docker exec grpc-router tc qdisc add dev eth0 root netem \
    delay 75ms loss 3%

# 設定確認
docker exec grpc-router tc qdisc show dev eth0
```

#### エミュレーション対象
- **遅延**: 0ms, 75ms, 150ms, 225ms
- **パケットロス**: 3% (固定)
- **帯域制限**: 必要に応じて設定可能

### 5. セキュリティ設定

#### SSL/TLS証明書
```bash
# Raspberry Pi 5上で生成
sudo openssl req -x509 -newkey rsa:2048 \
    -keyout /etc/ssl/private/grpc-server.key \
    -out /etc/ssl/certs/grpc-server.crt \
    -days 365 -nodes \
    -subj "/CN=grpc-server-pi.local"
```

#### 証明書の検証
- **自己署名証明書**: 開発・テスト用
- **IPアドレス対応**: 172.30.0.2での接続
- **クライアント側**: `--insecure`フラグで証明書検証をスキップ

### 6. ポート設定

#### Raspberry Pi 5側
```nginx
# nginx設定
server {
    listen 80;
    listen 443 ssl http2;      # HTTP/2
    listen 443 http3 reuseport; # HTTP/3
    
    ssl_certificate /etc/ssl/certs/grpc-server.crt;
    ssl_certificate_key /etc/ssl/private/grpc-server.key;
}
```

#### ファイアウォール設定
```bash
# Raspberry Pi 5上で実行
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS/HTTP2/HTTP3
sudo ufw --force enable
```

### 7. 接続テスト

#### 基本的な接続確認
```bash
# Pingテスト
ping 172.30.0.2

# ポート確認
telnet 172.30.0.2 443

# SSL証明書確認
openssl s_client -connect 172.30.0.2:443 -servername grpc-server-pi.local
```

#### HTTP/2接続テスト
```bash
# クライアント側
docker exec grpc-client curl -k --http2 https://172.30.0.2/health
```

#### HTTP/3接続テスト
```bash
# クライアント側
docker exec grpc-client curl -k --http3 https://172.30.0.2/health
```

### 8. トラブルシューティング

#### 接続できない場合
1. **ネットワーク接続確認**
   ```bash
   # クライアント側
   ping 172.30.0.2
   
   # Raspberry Pi側
   ping 172.30.0.254
   ```

2. **ポート確認**
   ```bash
   # Raspberry Pi側
   sudo ss -tuln | grep :443
   sudo systemctl status nginx
   ```

3. **ルーティング確認**
   ```bash
   # クライアント側
   docker exec grpc-client ip route show
   
   # Raspberry Pi側
   ip route show
   ```

#### パフォーマンス問題
1. **ネットワーク統計確認**
   ```bash
   # クライアント側
   docker exec grpc-client ss -s
   
   # Raspberry Pi側
   ss -s
   netstat -i
   ```

2. **リソース使用量確認**
   ```bash
   # Raspberry Pi側
   htop
   iotop
   nethogs
   ```

### 9. 監視とログ

#### クライアント側ログ
- Dockerコンテナログ: `docker logs grpc-client`
- ベンチマークログ: `logs/benchmark_raspberry_pi_*/`

#### Raspberry Pi側ログ
- Nginxアクセスログ: `/var/log/nginx/access.log`
- Nginxエラーログ: `/var/log/nginx/error.log`
- システムログ: `/var/log/syslog`

### 10. 最適化のポイント

#### ネットワーク最適化
- **MTU設定**: 1500バイト（標準）
- **TCP設定**: カーネルパラメータ調整
- **UDP設定**: QUIC用の最適化

#### サーバー最適化
- **Nginx設定**: ワーカープロセス数調整
- **システム設定**: ファイルディスクリプタ制限
- **メモリ設定**: バッファサイズ調整

## まとめ

この構成では、Docker環境のクライアントとRaspberry Pi 5実機サーバーが物理ネットワーク経由で通信し、Dockerルーターコンテナがネットワークエミュレーションを提供します。これにより、実機環境での現実的な性能測定が可能になります。
