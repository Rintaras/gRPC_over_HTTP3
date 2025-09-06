# Raspberry Pi 5 実機サーバー構築プロジェクト

## プロジェクト概要

現在のDockerベースのgRPC over HTTP/3ベンチマーク環境を、Raspberry Pi 5を実機サーバーとして使用する構成に拡張するプロジェクトです。

## 技術スタック

### サーバー側（Raspberry Pi 5）
- **OS**: Raspberry Pi OS (64-bit)
- **Webサーバー**: Nginx (HTTP/2 + HTTP/3対応)
- **プロトコル**: HTTP/2, HTTP/3 (QUIC)
- **SSL/TLS**: 自己署名証明書
- **言語**: Bash, C (Nginxビルド)
- **インストール**: ネイティブインストール（Docker不使用）

### クライアント側（Docker）
- **クライアント**: h2load (HTTP/2/3 ベンチマークツール)
- **ルーター**: Dockerコンテナ（ネットワークエミュレーション）
- **ネットワーク**: Docker Bridge Network
- **エミュレーション**: tc (Traffic Control)

## ファイル構成

```
gRPC_over_HTTP3/
├── scripts/
│   ├── run_bench.sh                    # 既存のDockerベンチマーク
│   ├── run_bench_raspberry_pi.sh       # Raspberry Pi用ベンチマーク
│   └── raspberry_pi_setup.sh           # Raspberry Pi初期設定スクリプト
├── RASPBERRY_PI_SETUP.md               # 詳細セットアップガイド
└── README_RASPBERRY_PI.md              # このファイル
```

## セットアップ手順

### 1. Raspberry Pi 5 の準備

#### ハードウェア要件
- Raspberry Pi 5 (推奨: 8GB RAM)
- microSDカード (32GB以上、Class 10以上)
- 電源アダプター (5V/3A以上)
- 有線LAN接続用ケーブル
- 冷却ファン（推奨）

#### 初期セットアップ
1. Raspberry Pi OS (64-bit) をインストール
2. SSHを有効化
3. 固定IPアドレスを設定 (推奨: 172.30.0.2/24)

### 2. サーバーソフトウェアの構築（ネイティブインストール）

Raspberry Pi 5にSSH接続して以下のコマンドを実行：

```bash
# セットアップスクリプトをダウンロード
wget https://raw.githubusercontent.com/your-repo/gRPC_over_HTTP3/main/scripts/raspberry_pi_setup.sh
chmod +x raspberry_pi_setup.sh
sudo ./raspberry_pi_setup.sh
```

**注意**: Raspberry Pi 5ではDockerを使用せず、ネイティブインストールのみです。

### 3. ネットワーク設定

#### Dockerネットワーク設定（クライアント側）
```bash
# 既存のDockerネットワーク確認
docker network ls

# 必要に応じて新しいネットワーク作成
docker network create --subnet=172.30.0.0/24 grpc-benchmark
```

#### ルーター設定の調整（クライアント側）
```bash
# ルーターコンテナの設定確認
docker exec grpc-router ip route show
docker exec grpc-router iptables -L
```

#### Raspberry Pi 5側の設定
```bash
# 固定IP設定（Raspberry Pi 5上で実行）
sudo nano /etc/dhcpcd.conf

# 以下を追加
interface eth0
static ip_address=172.30.0.2/24
static routers=172.30.0.254
static domain_name_servers=8.8.8.8
```

### 4. ベンチマーク実行

#### 接続テスト
```bash
# Raspberry Piへの接続確認
ping 172.30.0.2

# HTTP/2接続テスト
curl -k --http2 https://172.30.0.2/echo

# HTTP/3接続テスト
curl -k --http3 https://172.30.0.2/echo
```

#### ベンチマーク実行
```bash
# Raspberry Pi用ベンチマーク実行
./scripts/run_bench_raspberry_pi.sh
```

## ベンチマーク仕様

### テスト条件
- **遅延**: 0ms, 75ms, 150ms, 225ms
- **パケットロス**: 3% (固定)
- **総リクエスト数**: 50,000
- **同時接続数**: 100
- **並列スレッド数**: 20

### 測定項目
- 平均応答時間
- 中央値応答時間
- 最小/最大応答時間
- 標準偏差
- スループット

## 期待される効果

### 実機環境での測定
- より現実的なネットワーク条件
- ハードウェア制約の影響測定
- 実際のデバイス間通信の特性

### パフォーマンス比較
- Docker vs 実機の性能差
- ネットワークスタックの違い
- リソース制約の影響

## 監視とログ

### システム監視（Raspberry Pi 5上で実行）
```bash
# CPU使用率
htop

# ディスクI/O
iotop

# ネットワーク使用量
nethogs

# システム状態確認
/usr/local/bin/monitor_raspberry_pi.sh

# Nginx状態確認
sudo systemctl status nginx

# アクティブ接続数確認
ss -tuln | grep :443
```

### ログファイル
- Nginxアクセスログ: `/var/log/nginx/access.log` (Raspberry Pi 5上)
- Nginxエラーログ: `/var/log/nginx/error.log` (Raspberry Pi 5上)
- ベンチマークログ: `logs/benchmark_raspberry_pi_YYYYMMDD_HHMMSS/` (クライアント側)

## トラブルシューティング

### よくある問題

1. **接続できない**
   - ファイアウォール設定確認
   - IPアドレス設定確認
   - ネットワーク接続確認

2. **SSL証明書エラー**
   - 証明書の有効性確認
   - 自己署名証明書の受け入れ設定

3. **HTTP/3が動作しない**
   - Nginx設定確認
   - クライアント対応確認
   - ネットワーク設定確認

4. **パフォーマンス低下**
   - 冷却状況確認
   - CPU使用率確認
   - メモリ使用量確認

### デバッグコマンド

#### クライアント側（Docker環境）
```bash
# 接続確認
telnet 172.30.0.2 443

# SSL証明書確認
openssl s_client -connect 172.30.0.2:443 -servername grpc-server-pi.local

# HTTP/3確認
curl -k --http3 -v https://172.30.0.2/echo
```

#### Raspberry Pi 5側（ネイティブ環境）
```bash
# システム状態確認
sudo systemctl status nginx

# ポート確認
sudo ss -tuln | grep :443

# ログ確認
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# プロセス確認
ps aux | grep nginx
```

## セキュリティ考慮事項

- 自己署名証明書の使用
- ファイアウォール設定
- SSH接続のセキュリティ
- 定期的なシステム更新

## 今後の拡張

1. **複数デバイス対応**
   - 複数のRaspberry Piでの負荷分散
   - クラスター構成でのベンチマーク

2. **高度な監視**
   - Prometheus + Grafanaでの監視
   - リアルタイムメトリクス収集

3. **自動化の拡張**
   - CI/CDパイプラインの構築
   - 自動ベンチマーク実行

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグ報告や機能追加の提案は、GitHubのIssueまたはPull Requestでお願いします。

## 連絡先

プロジェクトに関する質問やサポートが必要な場合は、GitHubのIssueでお知らせください。
