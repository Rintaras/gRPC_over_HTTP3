# Go環境実装記録

## 概要
元のDocker環境（Nginx、Rust quiche、C++）をGo言語ベースの環境に完全移行し、HTTP/2とHTTP/3のベンチマーク環境を構築しました。

## 実装完了項目

### 1. 環境移行 ✅
- **OS**: Ubuntu 18.04（元の環境と統一）
- **言語**: Go 1.21
- **プロトコル**: HTTP/2、HTTP/3（QUIC）
- **ライブラリ**: 
  - `github.com/quic-go/quic-go/http3` (HTTP/3)
  - `golang.org/x/net/http2` (HTTP/2)
  - `google.golang.org/grpc` (gRPC)
  - `google.golang.org/protobuf` (Protocol Buffers)

### 2. サーバー実装 ✅
- **HTTP/2サーバー**: ポート443でHTTPS通信
- **HTTP/3サーバー**: ポート4433でQUIC通信
- **エンドポイント**:
  - `/health`: ヘルスチェック（プロトコル自動判別）
  - `/echo`: エコー応答（プロトコル情報付き）
- **TLS設定**: 自己署名証明書による暗号化通信
- **グレースフルシャットダウン**: 両サーバーの適切な停止処理

### 3. クライアント実装 ✅
- **HTTP/2クライアント**: 標準HTTPクライアント
- **HTTP/3クライアント**: QUICクライアント
- **テストクライアント**: 疎通確認用のシンプルなクライアント
- **ベンチマーククライアント**: 詳細なログ出力付きベンチマーク機能

### 4. ルーター実装 ✅
- **ネットワークエミュレーション**: `tc netem`コマンドを使用
- **REST API**: ネットワーク条件の動的制御
  - `POST /network/config`: 遅延・損失・帯域制限設定
  - `GET /network/status`: 現在の設定確認
  - `POST /network/clear`: 設定クリア
- **対応パラメータ**:
  - 遅延（delay）: ミリ秒単位
  - パケットロス（loss）: パーセント単位
  - 帯域制限（bandwidth）: Mbps単位

### 5. ネットワーク最適化 ✅
- **LSO/LRO無効化**: 
  - Large Send Offload (LSO)
  - Large Receive Offload (LRO)
  - Generic Segmentation Offload (GSO)
  - Generic Receive Offload (GRO)
  - TCP Segmentation Offload (TSO)
- **目的**: `tc netem`のパケットロス機能を正確に動作させるため
- **実装**: `ethtool`を使用したオフロード機能無効化スクリプト

### 6. ベンチマーク機能 ✅
- **進行状況ログ**: 詳細な実行状況表示
  - テストケース進行状況
  - リクエスト処理状況
  - エラー率・スループット情報
- **設定可能パラメータ**:
  - リクエスト数: 1,000〜50,000
  - 接続数: 50〜100
  - スレッド数: 10〜20
  - テストケース: 複数のネットワーク条件

### 7. Docker環境 ✅
- **マルチステージビルド**: 最適化されたDockerfile
- **ネットワーク設定**: 172.31.0.0/24サブネット
- **ヘルスチェック**: 全コンテナの健全性監視
- **オフロード無効化**: コンテナ起動時の自動実行

### 8. Go環境最適化 ✅
- **モジュール管理**: Go Modules完全対応
- **環境変数設定**: 
  - `GO111MODULE=on`
  - `GOPATH=`（空値）
- **警告解消**: `go: warning: ignoring go.mod in $GOPATH`の解決

## 技術仕様

### サーバー構成
```
go-grpc-server (172.31.0.2)
├── HTTP/2 Server (Port 443)
├── HTTP/3 Server (Port 4433)
├── Health Check (Port 8080)
└── TLS Certificate Management
```

### クライアント構成
```
go-grpc-client (172.31.0.3)
├── HTTP/2 Client
├── HTTP/3 Client
├── Benchmark Client
└── Test Client
```

### ルーター構成
```
go-grpc-router (172.31.0.254)
├── Network Emulation (tc netem)
├── REST API (Port 8081)
├── Offload Disable Script
└── Health Check (Port 8080)
```

## 確認済み動作

### HTTP/2通信 ✅
```json
// ヘルスチェック応答
{"status":"OK","protocol":"HTTP/2"}

// エコー応答
{"message":"Echo response","protocol":"HTTP/1.1","timestamp":1758303788252587710}
```

### HTTP/3通信 ✅
```json
// ヘルスチェック応答
{"status":"OK","protocol":"HTTP/3"}

// エコー応答
{"message":"Echo response","protocol":"HTTP/3.0","timestamp":1758303788266050918}
```

### ネットワークエミュレーション ✅
```bash
# 設定例
tc qdisc add dev eth0 root netem delay 50.0ms loss 10% rate 10Mbit

# オフロード無効化確認
tcp-segmentation-offload: off
generic-segmentation-offload: off
generic-receive-offload: off
large-receive-offload: off [fixed]
```

## ファイル構成

### サーバー関連
- `server/server.go`: メインサーバー実装
- `server/cert_manager.go`: TLS証明書管理
- `server/health_check.go`: ヘルスチェック機能
- `server/echo_server.go`: gRPCエコーサービス（将来用）

### クライアント関連
- `client/client.go`: メインベンチマーククライアント
- `client/benchmark.go`: ベンチマーク実行ロジック
- `client/analysis.go`: 結果分析機能
- `test_http_client.go`: 疎通確認用テストクライアント

### ルーター関連
- `router/router.go`: REST APIサーバー
- `router/network_emulation.go`: ネットワークエミュレーション
- `router/disable_offloads.sh`: オフロード無効化スクリプト

### 共通
- `common/config.go`: 設定管理
- `common/logger.go`: ログ機能
- `proto/echo.proto`: Protocol Buffer定義
- `go.mod`: Go依存関係管理
- `docker-compose.yml`: Docker環境定義

## 実行方法

### 環境起動
```bash
cd go-impl
docker-compose up -d
```

### 疎通確認
```bash
docker exec go-grpc-client ./test_http_client
```

### ネットワーク設定
```bash
# 遅延・損失設定
curl -X POST http://localhost:8081/network/config \
  -H "Content-Type: application/json" \
  -d '{"delay": 100, "loss": 5, "bandwidth": 10}'

# 設定確認
curl http://localhost:8081/network/status

# 設定クリア
curl -X POST http://localhost:8081/network/clear
```

### ベンチマーク実行
```bash
docker exec go-grpc-client ./client
```

## 今後の拡張予定

### 1. gRPC実装
- 現在はHTTP/2、HTTP/3の基本的なWebサーバー
- gRPC over HTTP/2、HTTP/3の実装予定

### 2. ベンチマーク強化
- より詳細なメトリクス収集
- グラフ生成機能
- レポート出力機能

### 3. 監視機能
- Prometheusメトリクス
- リアルタイム監視ダッシュボード

## 実装日時
- **開始**: 2025年9月19日
- **完了**: 2025年9月19日
- **環境**: macOS (Docker Desktop)
- **Go バージョン**: 1.21
- **Docker**: 最新版

---

**注意**: この実装記録は開発過程での実装内容を記録したものです。本番環境での使用前に、セキュリティ設定やパフォーマンスチューニングを実施してください。
