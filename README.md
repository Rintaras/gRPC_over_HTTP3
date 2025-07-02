# HTTP/2 vs HTTP/3 Performance Benchmark

HTTP/2（TCP）とHTTP/3（QUIC）の性能比較研究プロジェクトです。3ノードのDocker Compose構成でネットワーク遅延・損失をエミュレートしながらベンチマークを実施します。

## 🎯 プロジェクト概要

このプロジェクトは、異なるネットワーク条件下でのHTTP/2とHTTP/3の性能を公平に比較することを目的としています。

### 主要特徴
- **公平性を重視した比較**: 接続確立のオーバーヘッドを除外した純粋なリクエスト処理性能を測定
- **多様なネットワーク条件**: 0ms〜150ms遅延、0%〜3%パケット損失をエミュレート
- **包括的なメトリクス**: スループット、レイテンシ、統計値（p95、p99）を詳細分析
- **自動化されたベンチマーク**: 一括実行と結果分析

## 🏗️ アーキテクチャ

```
[Client] --(HTTP/2/3)--> [Router] --(HTTP/2/3)--> [Server]
  172.30.0.3             172.30.0.254             172.30.0.2
```

### コンポーネント
- **Client**: curl（HTTP/3対応）、h2load（HTTP/2/3対応）、grpcurl
- **Router**: tc netemで遅延・損失エミュレーション
- **Server**: nginx + quiche（HTTP/2/3対応）

## 🚀 セットアップ

### 前提条件
- Docker & Docker Compose
- Python 3.7+
- ネットワーク管理権限（tc netem使用のため）

### インストール
```bash
git clone <repository>
cd gRPC_over_HTTP3
docker-compose up -d --build
```

## 📊 ベンチマーク実行

### 基本実行
```bash
docker exec grpc-client /scripts/run_bench.sh
```

### テストケース
- **理想環境**: 0ms遅延、0%損失
- **中程度遅延**: 50ms遅延、0%損失  
- **高遅延低損失**: 100ms遅延、1%損失
- **高遅延高損失**: 150ms遅延、3%損失

### パラメータ
- 総リクエスト数: 10,000
- 同時接続数: 100
- 並列スレッド数: 20
- 最大同時ストリーム数: 100

## 📈 結果分析

### 生成されるファイル
- `logs/comparison_report.txt`: 包括的比較レポート
- `logs/fair_comparison_report.txt`: 公平性を考慮した詳細分析
- `logs/comparison_data.csv`: 全データのCSV形式
- `logs/fair_comparison_data.csv`: 公平性分析データ

### 主要メトリクス
- **スループット**: 1秒あたりのリクエスト数
- **レイテンシ**: 平均、最小、最大、標準偏差
- **接続時間**: TCP/QUIC接続確立時間
- **処理時間**: 接続確立後の純粋なリクエスト処理時間
- **成功率**: エラー率とリトライ統計

## 🔬 公平性の改善

### 従来の問題点
- HTTP/2とHTTP/3で接続処理が異なる（TCP vs QUIC）
- 接続確立のオーバーヘッドが性能比較に影響
- 実装の成熟度の違いによる不公平

### 改善策
1. **接続確立の分離**: ウォームアップ期間で接続を確立
2. **純粋な処理時間測定**: 接続時間を除外したリクエスト処理性能
3. **統一された負荷パラメータ**: 両プロトコルで同じ条件
4. **統計的有意性**: 十分なサンプルサイズと信頼区間

### 公平性パラメータ
- ウォームアップリクエスト: 1,000
- 測定リクエスト: 9,000
- 接続安定化時間: 2秒

## 🛠️ 技術スタック

### プロトコル実装
- **HTTP/2**: nginx + h2load
- **HTTP/3**: nginx + quiche + h2load（HTTP/3対応版）

### ネットワークエミュレーション
- **tc netem**: 遅延・損失・ジッター制御
- **Docker network**: 分離されたテスト環境

### 分析ツール
- **Python**: 統計分析とレポート生成
- **h2load**: 負荷テストとメトリクス収集
- **curl**: HTTP/3接続検証

## 📋 使用技術

### プロトコル
- HTTP/2 over TLS
- HTTP/3 over QUIC
- gRPC over HTTP/2/3

### ネットワーク
- TCP (HTTP/2)
- QUIC (HTTP/3)
- TLS 1.3
- ALPN (Application-Layer Protocol Negotiation)

### コンテナ技術
- Docker
- Docker Compose
- カスタムネットワーク

### 分析・可視化
- Python 3.7+
- NumPy (統計計算)
- CSV/JSON (データ形式)
- 日本語レポート生成

## 🔍 トラブルシューティング

### よくある問題
1. **HTTP/3接続失敗**: サーバーのquiche実装を確認
2. **ネットワークエミュレーション**: tc netemの権限確認
3. **メモリ不足**: Dockerリソース制限の調整

### ログ確認
```bash
# サーバーログ
docker logs grpc-server

# ルーターログ  
docker logs grpc-router

# クライアントログ
docker logs grpc-client
```

## 📚 参考文献

- [HTTP/3 Specification](https://quicwg.org/base-drafts/draft-ietf-quic-http.html)
- [QUIC Protocol](https://tools.ietf.org/html/draft-ietf-quic-transport)
- [nginx HTTP/3 Module](https://github.com/cloudflare/quiche)
- [h2load Documentation](https://nghttp2.org/documentation/h2load-howto.html)

## 📄 ライセンス

MIT License

## 🤝 貢献

プルリクエストやイシューの報告を歓迎します。 