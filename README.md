# gRPC over HTTP/3 Performance Benchmark

HTTP/2（TCP）とHTTP/3（QUIC）の性能比較研究プロジェクトです。Docker Composeを使用した3ノード構成で、様々なネットワーク条件下での性能を測定します。

## 構成

### アーキテクチャ
```
Client (h2load + curl) ←→ Router (tc netem) ←→ Server (nginx + quiche)
```

### コンポーネント
- **Client**: h2load（HTTP/2）、curl（HTTP/3）による負荷テスト
- **Router**: tc netemによる遅延・損失エミュレーション
- **Server**: nginx + quiche（HTTP/2/3対応）

## 技術スタック

### クライアント
- **h2load**: nghttp2 1.67.0-DEV（HTTP/2負荷テスト）
- **curl**: HTTP/3対応版（HTTP/3負荷テスト）
- **GNU parallel**: 並列処理
- **bc**: 数値計算

### ルーター
- **tc netem**: ネットワーク遅延・損失エミュレーション
- **iptables**: パケット制御

### サーバー
- **nginx**: 1.25.3 + quiche（HTTP/2/3対応）
- **quiche**: Cloudflare製QUIC実装
- **OpenSSL**: TLS 1.3対応

## ベンチマーク条件

### ネットワーク条件
| 遅延 | 損失 | 説明 |
|------|------|------|
| 0ms | 0% | 理想的な環境 |
| 50ms | 0% | 中程度の遅延 |
| 100ms | 1% | 高遅延 + 低損失 |
| 150ms | 3% | 高遅延 + 高損失 |

### 負荷パラメータ
- **リクエスト数**: 1,000
- **接続数**: 10
- **スレッド数**: 2
- **最大同時ストリーム**: 10

## 使用方法

### 1. 環境構築
```bash
# コンテナビルド・起動
docker-compose up -d

# 動作確認
docker exec grpc-client curl -sk --http3 https://172.30.0.2/echo
```

### 2. ベンチマーク実行
```bash
# 全条件でベンチマーク実行
docker exec grpc-client /scripts/run_bench.sh
```

### 3. 結果分析
```bash
# CSVレポート生成
docker exec grpc-client python3 /scripts/merge_results.py
```

## ベンチマーク手法

### HTTP/2
- **ツール**: h2load
- **プロトコル**: HTTP/2 over TLS 1.3
- **負荷**: 多接続・多ストリーム並列処理

### HTTP/3
- **ツール**: curl（h2loadがHTTP/3未対応のため）
- **プロトコル**: HTTP/3 over QUIC
- **負荷**: h2loadと同等の負荷条件を再現

### 負荷条件の統一
両プロトコルで同じ負荷条件を適用：
- 接続数、スレッド数、同時ストリーム数を統一
- 並列処理パターンを類似化
- ネットワーク条件を同一に設定

## 結果分析

### 測定項目
- **スループット**: リクエスト/秒
- **レイテンシ**: 平均・最小・最大・標準偏差
- **成功率**: 成功リクエスト率
- **接続時間**: 接続確立時間
- **初回バイト時間**: Time to First Byte

### 出力形式
- **詳細ログ**: 各条件の生データ
- **CSVレポート**: 全条件の比較データ
- **比較レポート**: プロトコル間の直接比較

## ファイル構成

```
gRPC_over_HTTP3/
├── client/
│   └── Dockerfile          # h2load + curl環境
├── router/
│   └── Dockerfile          # tc netem環境
├── server/
│   ├── Dockerfile          # nginx + quiche環境
│   ├── nginx.conf          # HTTP/2/3設定
│   └── proto/
│       └── echo.proto      # gRPC定義
├── scripts/
│   ├── run_bench.sh        # ベンチマーク実行
│   ├── netem_delay_loss.sh # ネットワーク条件設定
│   └── merge_results.py    # 結果分析
├── logs/                   # 結果ログ
└── docker-compose.yml      # コンテナ構成
```

## 技術的詳細

### HTTP/3実装
- **QUIC**: UDPベースの信頼性のあるトランスポート
- **0-RTT**: 接続再利用による高速化
- **マルチプレクシング**: 単一接続での複数ストリーム
- **ヘッダー圧縮**: QPACKによる効率化

### ネットワークエミュレーション
- **tc netem**: Linuxカーネルレベルでの遅延・損失制御
- **リアルタイム制御**: 動的な条件変更
- **統計的制御**: パケットレベルでの正確な制御

### 負荷テスト最適化
- **並列処理**: マルチスレッド・マルチプロセス
- **接続プール**: 効率的な接続管理
- **メモリ最適化**: 大量リクエスト処理
- **エラーハンドリング**: 堅牢な失敗処理

## 今後の拡張

- [ ] HTTP/3対応h2loadの実装
- [ ] より多様なネットワーク条件
- [ ] リアルタイム可視化
- [ ] 自動化された継続的ベンチマーク
- [ ] より大規模な負荷テスト 