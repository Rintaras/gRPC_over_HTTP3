# Go gRPC over HTTP/2/3 Implementation

## 概要

この実装は、nginx + Rust quicheベースの既存システムからGo言語ベースのHTTP/2・HTTP/3実装への移行版です。既存の実験内容とベンチマークを維持しながら、使用技術のみを変更しています。

## 技術スタック

- **言語**: Go 1.21+
- **HTTP/2**: `golang.org/x/net/http2`
- **HTTP/3**: `github.com/quic-go/quic-go`
- **gRPC**: `google.golang.org/grpc`
- **プロトコルバッファ**: `google.golang.org/protobuf`
- **ログ**: `log/slog` (構造化ログ)
- **監視**: カスタムメトリクス + ヘルスチェック

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                    Ubuntu Docker Environment                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │   Go Client     │    │   Go Router     │    │  Go Server   │ │
│  │   HTTP/2 & /3   │◄──►│   Network       │◄──►│  HTTP/2 & /3 │ │
│  │   quic-go       │    │   Emulation     │    │  quic-go     │ │
│  │   gRPC-Go       │    │   tc netem      │    │  gRPC-Go     │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 構成要素

### サーバー (go-server)
- **ポート**: 443 (HTTP/2), 4433 (HTTP/3), 8080 (ヘルスチェック)
- **機能**: gRPC over HTTP/2/3, 自己署名証明書生成, ヘルスチェック
- **プロトコル**: echo.proto ベースのEchoService

### クライアント (go-client)
- **機能**: HTTP/2/3ベンチマーク実行, 統計分析, レポート生成
- **測定項目**: レイテンシ、スループット、エラー率、パーセンタイル

### ルーター (go-router)
- **ポート**: 8080 (API), 8081 (外部アクセス)
- **機能**: ネットワークエミュレーション制御 (tc/netem)
- **API**: REST API でネットワーク条件を制御

## クイックスタート

### 1. 環境構築
```bash
cd go-impl
chmod +x scripts/*.sh
./scripts/build.sh
```

### 2. 環境起動
```bash
docker-compose up -d
```

### 3. ヘルスチェック
```bash
# サーバー
curl http://localhost:8080/health

# ルーター
curl http://localhost:8081/health
```

### 4. ベンチマーク実行
```bash
./scripts/run_benchmark.sh
```

## ベンチマーク仕様

### テストケース
- **ネットワーク条件**: 0ms, 75ms, 150ms, 225ms遅延 + 3%パケット損失
- **リクエスト数**: 50,000リクエスト
- **同時接続数**: 100接続
- **測定項目**: スループット、レイテンシ、エラー率、パーセンタイル

### 出力ファイル
- `benchmark_results.csv`: 詳細結果
- `performance_report_*.txt`: パフォーマンスレポート
- `benchmark_*/`: ログディレクトリ

## API リファレンス

### ルーター API

#### ネットワーク条件設定
```bash
curl -X POST http://localhost:8081/network/config \
  -H "Content-Type: application/json" \
  -d '{"delay": 150, "loss": 3}'
```

#### ネットワーク状態取得
```bash
curl http://localhost:8081/network/status
```

#### ネットワーク条件クリア
```bash
curl -X POST http://localhost:8081/network/clear
```

### サーバーヘルスチェック
```bash
curl http://localhost:8080/health
curl http://localhost:8080/ready
```

## 開発・デバッグ

### ログ確認
```bash
# 全サービス
docker-compose logs

# 個別サービス
docker-compose logs go-server
docker-compose logs go-client
docker-compose logs go-router
```

### コンテナ内でデバッグ
```bash
# サーバー
docker exec -it go-grpc-server bash

# クライアント
docker exec -it go-grpc-client bash

# ルーター
docker exec -it go-grpc-router bash
```

### ネットワーク状態確認
```bash
# ルーター内で
docker exec go-grpc-router tc qdisc show dev eth0
```

## 設定

### 環境変数

#### サーバー
- `SERVER_PORT`: HTTP/2ポート (デフォルト: 443)
- `HTTP3_PORT`: HTTP/3ポート (デフォルト: 4433)
- `LOG_LEVEL`: ログレベル (DEBUG, INFO, WARN, ERROR)

#### クライアント
- `LOG_LEVEL`: ログレベル

#### ルーター
- `LOG_LEVEL`: ログレベル

## トラブルシューティング

### よくある問題

1. **証明書エラー**
   ```bash
   # 証明書再生成
   docker-compose down
   docker-compose up -d
   ```

2. **ネットワークエミュレーション失敗**
   ```bash
   # ルーター権限確認
   docker exec go-grpc-router tc qdisc show dev eth0
   ```

3. **接続タイムアウト**
   ```bash
   # ヘルスチェック確認
   curl -v http://localhost:8080/health
   ```

### ログレベル変更
```bash
# デバッグレベルで再起動
docker-compose down
LOG_LEVEL=DEBUG docker-compose up -d
```

## パフォーマンス最適化

### 推奨設定
- **接続プール**: 100接続
- **バッチサイズ**: 100リクエスト
- **タイムアウト**: 30秒
- **メモリ**: 2GB以上推奨

### 監視
- ヘルスチェック: 30秒間隔
- メトリクス: 構造化ログで出力
- リソース使用量: Docker stats で監視

## ライセンス

このプロジェクトは研究目的で作成されています。
