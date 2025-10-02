# プロトコル比較プロジェクト - HTTP/2 vs HTTP/3

## 概要

このプロジェクトは、HTTP/2とHTTP/3のパフォーマンス比較を行うためのDocker環境です。ネットワーク帯域制限機能を持つルーターを実装し、異なるネットワーク条件下での両プロトコルの動作を測定できます。

## 技術スタック

### サーバーサイド
- **Go 1.21**
- **quic-go v0.40.1** - HTTP/3 (QUIC) プロトコル実装
- **golang.org/x/net/http2** - HTTP/2実装
- **Ubuntu 22.04** - Dockerベースイメージ
- **TLS 1.2/1.3** - セキュア通信（ALPN対応）

### ネットワーク
- **Docker Compose** - マルチコンテナオーケストレーション
- **Docker Bridge Network** - コンテナ間通信
- **mkcert** - ローカルSSL証明書生成
- **カスタムルーター** - TCP/UDPプロキシ
  - **tc (Traffic Control)** - Linux カーネルレベルのネットワーク制御
  - **HTB (Hierarchical Token Bucket)** - 帯域制限実装
  - **netem (Network Emulator)** - 遅延・パケット損失エミュレーション
  - **iproute2** - トラフィック制御ツール

### ベンチマーク
- **スケジューラー解析** - OS/CPU最適化（cpuset, nice優先度）
- **統計分析** - 平均、中央値、パーセンタイル（P50/P90/P95/P99）
- **GC最適化** - メモリ管理の影響排除（debug.SetGCPercent）
- **runtime制御** - GOMAXPROCS最適化

## プロジェクト構成

```
protocol_comparison/
├── server/                          # サーバー実装
│   ├── main.go                      # HTTP/2 & HTTP/3サーバー
│   ├── go.mod                       # 依存関係
│   └── Dockerfile                   # イメージ定義
├── router/                          # ルーター実装
│   ├── main.go                      # TCP/UDPプロキシ
│   └── go.mod                       # 依存関係
├── client/                          # クライアント実装
│   ├── http3_client.go              # HTTP/3クライアント
│   ├── (その他のクライアント)
│   └── go.mod                       # 依存関係
├── certs/                           # SSL証明書 🔐
│   ├── localhost+2.pem              # 公開鍵
│   ├── localhost+2-key.pem          # 秘密鍵
│   └── README.md                    # 証明書生成ガイド
├── logs/                            # ベンチマーク結果 📊
│   └── YYYYMMDD_HHMMSS/             # タイムスタンプ別
│       ├── benchmark_results.csv    # 生データ
│       ├── response_time_comparison.png
│       ├── stability_comparison.png
│       ├── benchmark_visualization.png
│       └── benchmark_analysis.png
├── docs/                            # ドキュメント 📚
│   ├── QUICK_START.md               # クイックスタート 🚀
│   ├── README_GRAPHS.md             # グラフガイド
│   ├── BENCHMARK_ANALYSIS.md        # 分析結果
│   ├── EXPERIMENT_CONDITIONS.md     # 実験条件
│   ├── RESULTS.md                   # 結果サマリー
│   └── FINAL_STRUCTURE.md           # 構成説明
├── scripts/                         # スクリプト 🔧
│   ├── benchmark_latency.sh         # メインベンチマーク
│   ├── generate_all_graphs.sh       # グラフ再生成
│   ├── view_latest_results.sh       # 最新結果確認
│   ├── tc_setup.sh                  # tc設定
│   ├── tc_reset.sh                  # tcリセット
│   ├── visualize_response_time.py   # 応答速度グラフ
│   ├── visualize_stability.py       # 安定性グラフ
│   └── visualize_results.py         # 総合グラフ
├── docker-compose.router_tc.yml     # Docker構成
├── Dockerfile.router_tc             # ルーターイメージ
├── Dockerfile.http3_test            # HTTP/3クライアントイメージ
├── run_benchmark.sh                 # ベンチマーク実行 ⭐
├── view_results.sh                  # 結果確認
└── monitor_benchmark.sh             # 進捗監視
```

## セットアップ

### 1. 証明書の準備

```bash
mkcert -install
cd certs/
mkcert localhost 127.0.0.1 ::1
cd ..
```

生成される証明書は`certs/`ディレクトリに保存されます。

### 2. サービス起動

#### tcベースルーター（推奨）

```bash
BANDWIDTH=10mbit LATENCY=50ms LOSS=0% docker-compose -f docker-compose.router_tc.yml up -d --build
```

#### 基本構成

```bash
docker-compose up -d --build
```

### 3. 動作確認

```bash
docker-compose -f docker-compose.router_tc.yml ps
docker-compose -f docker-compose.router_tc.yml logs http3-server
docker-compose -f docker-compose.router_tc.yml logs router
docker exec network-router tc qdisc show dev eth0
```

### 4. テストリクエスト

```bash
curl -k --http2 https://localhost:8444/
curl -k --http3 https://localhost:8443/
curl -k --http2 https://localhost:8444/large -o /dev/null -w "時間: %{time_total}s\n"
```

## 機能

### HTTP/3サーバー

- **ポート**: 8443 (UDP/TCP)
- **プロトコル**: HTTP/1.1, HTTP/2, HTTP/3
- **TLS**: localhost+2証明書使用
- **Alt-Svc**: HTTP/3広告ヘッダー

### ネットワークルーター（tcベース）

- **TCP Proxy**: ポート8444 (HTTP/2用、TLSパススルー)
- **UDP Proxy**: ポート8443 (HTTP/3用)
- **トラフィック制御**: Linux tcコマンドによるカーネルレベル制御

#### ネットワーク条件の変更

コンテナ内でtcコマンドを実行：

```bash
docker exec network-router ./tc_setup.sh eth0 5mbit 100ms 1%
```

パラメータ：
- 第1引数: インターフェース名（通常はeth0）
- 第2引数: 帯域幅（例: 1mbit, 5mbit, 10mbit, 100mbit）
- 第3引数: 遅延（例: 0ms, 25ms, 50ms, 75ms, 100ms, 125ms, 150ms, 175ms, 200ms）
- 第4引数: パケット損失率（例: 0%, 1%, 5%）

#### 設定のリセット

```bash
docker exec network-router ./tc_reset.sh eth0
```

#### tc設定の確認

```bash
docker exec network-router tc qdisc show dev eth0
```

### ベンチマーク

#### メインベンチマーク（推奨）

遅延影響を測定し、自動でグラフを生成：

```bash
./benchmark_latency.sh
```

実行内容：
- 帯域: 5Mbps (固定)
- 遅延: 0ms, 25ms, 50ms, 75ms, 100ms, 125ms, 150ms, 175ms, 200ms
- データサイズ: 1MB
- リクエスト数: 各25回
- 自動でグラフ生成（4種類）

#### グラフのみ再生成

既存のCSVファイルからグラフを再作成：

```bash
./generate_all_graphs.sh
```

## ベンチマーク結果の見方

### 測定項目

- **平均接続時間**: 全接続の平均
- **中央値(P50)**: 中央値
- **最速上位20%の平均**: 最も安定した接続の平均
- **P90/P95/P99**: パーセンタイル値
- **スケジューリング遅延**: OS非自発的コンテキストスイッチ

### 最適化内容

1. **GC無効化**: `debug.SetGCPercent(-1)`
2. **プロセス優先度**: 最高優先度に設定
3. **シングルスレッド**: `GOMAXPROCS=1`
4. **IPv6無効化**: ネットワークスタック簡素化
5. **CPU固定**: Docker cpuset使用

## ネットワーク構成

```
クライアント (localhost)
    ↓
ネットワークルーター (tcによるトラフィック制御)
    ├─ TCP:8444 (HTTP/2) → http3-server:8443 (TLSパススルー)
    └─ UDP:8443 (HTTP/3) → http3-server:8443
    ↓
HTTP/3サーバー :8443 (HTTP/1.1, HTTP/2, HTTP/3対応)
```

### 動作フロー

1. **クライアント → ルーター**
   - HTTP/2: `localhost:8444/tcp` (TLS + ALPN)
   - HTTP/3: `localhost:8443/udp` (QUIC)

2. **ルーター内のトラフィック制御 (tc)**
   - **HTB qdisc**: 帯域制限（1mbit〜100mbit）
   - **netem qdisc**: 遅延付加（0ms〜200ms）
   - **パケット損失**: 確率的損失（0%〜10%）
   - カーネルレベルで適用（アプリケーション層より正確）

3. **ルーター → サーバー**
   - TCP/UDPプロキシ転送
   - TLSパススルー（暗号化維持）
   - 双方向通信

4. **サーバー → レスポンス**
   - プロトコル自動検出 (ALPN)
   - レスポンス生成
   - ルーター経由でクライアントへ返送

5. **動作確認済み**
   - ✅ HTTP/2リクエスト/レスポンス
   - ✅ tcによる帯域制限（1Mbps, 5Mbps, 10Mbps）
   - ✅ 遅延エミュレーション（25ms, 50ms, 75ms, 100ms, 125ms, 150ms, 175ms, 200ms）
   - ✅ パケット損失シミュレーション（1%, 5%）
   - ✅ カーネルレベルのトラフィック制御

## トラブルシューティング

### ルーターが起動しない

```bash
docker logs network-router
docker-compose -f docker-compose.router_tc.yml down
docker-compose -f docker-compose.router_tc.yml up -d --build
```

### tc設定が反映されない

```bash
docker exec network-router tc qdisc show dev eth0
docker exec network-router ./tc_reset.sh eth0
docker exec network-router ./tc_setup.sh eth0 10mbit 50ms 0%
```

### HTTP/3接続が失敗する

curlのHTTP/3サポートを確認：

```bash
curl --version | grep HTTP3
```

HTTP/3未対応の場合は、HTTP/2でテスト：

```bash
curl -k --http2 https://localhost:8444/large -o /dev/null -w "時間: %{time_total}s\n"
```

### 接続エラー

```bash
docker network inspect protocol_comparison_protocol_net
docker exec -it network-router netstat -tlnp
docker exec -it network-router ps aux
```

### 証明書エラー

```bash
mkcert -install
ls -la localhost+2*.pem
```

## パフォーマンス調整

### macOS固有の制限

- `sysctl` UDP設定は制限あり
- Docker for Macのネットワークオーバーヘッド
- ホストネットワークモード非対応

### HTTP/3 vs HTTP/2 テスト結果

実測値（10MBファイル転送）：

| 条件 | HTTP/2 | HTTP/3 | 勝者 |
|------|--------|--------|------|
| 制限なし | 0.93-0.98秒<br>11.0 MB/s | 0.93秒<br>11.0 MB/s | **同等** |
| 1Mbps | 87.7秒<br>119 KB/s | 90.6秒<br>113 KB/s | **HTTP/2** (3%高速) |
| 5Mbps + 50ms遅延 | 2.2秒<br>465 KB/s | 2.1秒<br>478 KB/s | **HTTP/3** (若干高速) |

**詳細な比較結果は [RESULTS.md](RESULTS.md) を参照してください。**

### 最適化の結果

- 非自発的コンテキストスイッチ: 0回
- ばらつきの主要因: ネットワークI/O処理
- tcによる帯域制限: カーネルレベルで正確に適用
- 遅延・パケット損失: netemによるエミュレーション成功

## 関連ドキュメント

すべてのドキュメントは`docs/`ディレクトリにあります：

- **[docs/QUICK_START.md](docs/QUICK_START.md)**: 5分で始めるガイド 🚀
- **[docs/README_GRAPHS.md](docs/README_GRAPHS.md)**: グラフ生成ガイド
- **[docs/BENCHMARK_ANALYSIS.md](docs/BENCHMARK_ANALYSIS.md)**: 詳細な分析
- **[docs/EXPERIMENT_CONDITIONS.md](docs/EXPERIMENT_CONDITIONS.md)**: 実験条件
- **[docs/RESULTS.md](docs/RESULTS.md)**: 性能比較結果

## 使い方

### すぐに始めたい方
→ **[docs/QUICK_START.md](docs/QUICK_START.md)** をご覧ください

### ベンチマーク実行
```bash
./run_benchmark.sh
```
→ 自動的にグラフが生成され、`logs/タイムスタンプ/`に保存されます

### 結果の確認
```bash
# 最新の実験結果を自動で開く
./view_results.sh

# または手動で確認
ls -lt logs/ | head -5
open logs/$(ls -t logs/ | head -1)/response_time_comparison.png
```

## ライセンス

このプロジェクトは研究用途で作成されました。