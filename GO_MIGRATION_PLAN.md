# Docker環境のGo言語ベース技術スタック移行計画

## 概要

現在のDocker環境（nginx + Rust quiche + C++実装）から、Ubuntu OS上でGo言語ライブラリを使用したHTTP/2・HTTP/3実装への移行計画です。実験内容とベンチマークは同様のものを維持し、使用技術のみを変更します。

## 現在の技術スタック分析

### 現行構成
- **OS**: Ubuntu 22.04 (Docker)
- **サーバー**: nginx + quiche (Rust実装)
- **クライアント**: h2load + quiche-client
- **ルーター**: Linux tc/netem (ネットワークエミュレーション)
- **プロトコル**: HTTP/2, HTTP/3 (QUIC)
- **gRPC**: echo.proto ベースのEchoService

### 実験内容
- ネットワーク条件: 0ms, 75ms, 150ms, 225ms遅延 + 3%パケット損失
- ベンチマーク: 50,000リクエスト、100同時接続、20スレッド
- 測定項目: スループット、レイテンシ、エラー率

## 新技術スタック設計

### 全体アーキテクチャ
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

### 技術スタック詳細

#### サーバー (Go Server)
- **OS**: Ubuntu 22.04
- **言語**: Go 1.21+
- **HTTP/2**: `golang.org/x/net/http2`
- **HTTP/3**: `github.com/quic-go/quic-go`
- **gRPC**: `google.golang.org/grpc`
- **プロトコルバッファ**: `google.golang.org/protobuf`
- **TLS**: `crypto/tls` (標準ライブラリ)

#### クライアント (Go Client)
- **OS**: Ubuntu 22.04
- **言語**: Go 1.21+
- **HTTP/2**: `golang.org/x/net/http2`
- **HTTP/3**: `github.com/quic-go/quic-go`
- **gRPC**: `google.golang.org/grpc`
- **ベンチマーク**: カスタムGo実装 (h2load代替)
- **データ分析**: 標準ライブラリ + `gonum.org/v1/plot`

#### ルーター (Go Router)
- **OS**: Ubuntu 22.04
- **言語**: Go 1.21+
- **ネットワークエミュレーション**: Linux tc/netem (既存維持)
- **トラフィック制御**: Go + exec (tc コマンド実行)
- **モニタリング**: Go 標準ライブラリ

## 実装計画

### Phase 1: 基盤構築 (1-2週間)

#### 1.1 Docker環境の再設計
```dockerfile
# 新しいDockerfile構造
FROM golang:1.21-bullseye as base
# 共通のGo環境セットアップ

FROM base as server
# Go HTTP/2/3 + gRPC サーバー実装

FROM base as client  
# Go HTTP/2/3 + gRPC クライアント実装

FROM base as router
# Go ルーター実装 (tc/netem制御)
```

#### 1.2 Go依存関係の定義
```go
// go.mod (各コンポーネント共通)
module grpc-over-http3

go 1.21

require (
    github.com/quic-go/quic-go v0.40.1
    google.golang.org/grpc v1.59.0
    google.golang.org/protobuf v1.31.0
    golang.org/x/net v0.17.0
    gonum.org/v1/plot v0.14.0
)
```

### Phase 2: サーバー実装 (2-3週間)

#### 2.1 HTTP/2 + gRPC サーバー
```go
// server/http2_server.go
package main

import (
    "context"
    "net/http"
    "golang.org/x/net/http2"
    "google.golang.org/grpc"
    pb "grpc-over-http3/proto"
)

type EchoServer struct {
    pb.UnimplementedEchoServiceServer
}

func (s *EchoServer) Echo(ctx context.Context, req *pb.EchoRequest) (*pb.EchoResponse, error) {
    return &pb.EchoResponse{
        Message:   req.Message,
        Timestamp: time.Now().UnixNano(),
        Protocol:  "HTTP/2",
    }, nil
}

func (s *EchoServer) StreamEcho(stream pb.EchoService_StreamEchoServer) error {
    // ストリーミング実装
}

func main() {
    // HTTP/2 + gRPC サーバー起動
    grpcServer := grpc.NewServer()
    pb.RegisterEchoServiceServer(grpcServer, &EchoServer{})
    
    server := &http.Server{
        Addr: ":443",
        Handler: grpcServer,
    }
    http2.ConfigureServer(server, &http2.Server{})
    server.ListenAndServeTLS("certs/server.crt", "certs/server.key")
}
```

#### 2.2 HTTP/3 + gRPC サーバー
```go
// server/http3_server.go
package main

import (
    "github.com/quic-go/quic-go/http3"
    "google.golang.org/grpc"
    pb "grpc-over-http3/proto"
)

func main() {
    // HTTP/3 + gRPC サーバー起動
    grpcServer := grpc.NewServer()
    pb.RegisterEchoServiceServer(grpcServer, &EchoServer{})
    
    server := &http3.Server{
        Addr: ":4433",
        Handler: grpcServer,
        TLSConfig: tlsConfig,
    }
    server.ListenAndServe()
}
```

### Phase 3: クライアント実装 (2-3週間)

#### 3.1 ベンチマーククライアント
```go
// client/benchmark.go
package main

import (
    "context"
    "sync"
    "time"
    "github.com/quic-go/quic-go"
    "google.golang.org/grpc"
    pb "grpc-over-http3/proto"
)

type BenchmarkConfig struct {
    Requests      int
    Connections   int
    Threads       int
    MaxConcurrent int
    Protocol      string // "HTTP/2" or "HTTP/3"
}

type BenchmarkResult struct {
    TotalRequests    int
    SuccessfulReqs   int
    FailedReqs       int
    TotalTime        time.Duration
    AvgLatency       time.Duration
    Throughput       float64 // requests/second
    ErrorRate        float64
}

func runHTTP2Benchmark(config BenchmarkConfig) BenchmarkResult {
    // HTTP/2 ベンチマーク実装
}

func runHTTP3Benchmark(config BenchmarkConfig) BenchmarkResult {
    // HTTP/3 ベンチマーク実装
}
```

#### 3.2 データ分析・レポート生成
```go
// client/analysis.go
package main

import (
    "gonum.org/v1/plot"
    "gonum.org/v1/plot/plotter"
    "gonum.org/v1/plot/vg"
)

func generatePerformanceGraph(results []BenchmarkResult) error {
    // パフォーマンス比較グラフ生成
    p := plot.New()
    // グラフ作成ロジック
    return p.Save(8*vg.Inch, 6*vg.Inch, "performance_comparison.png")
}
```

### Phase 4: ルーター実装 (1週間)

#### 4.1 ネットワークエミュレーション制御
```go
// router/network_emulation.go
package main

import (
    "os/exec"
    "strconv"
)

type NetworkEmulation struct {
    Delay int // ms
    Loss  int // percentage
}

func (ne *NetworkEmulation) Apply() error {
    // tc netem コマンド実行
    cmd := exec.Command("tc", "qdisc", "add", "dev", "eth0", "root", "netem",
        "delay", strconv.Itoa(ne.Delay)+"ms",
        "loss", strconv.Itoa(ne.Loss)+"%")
    return cmd.Run()
}

func (ne *NetworkEmulation) Clear() error {
    cmd := exec.Command("tc", "qdisc", "del", "dev", "eth0", "root")
    return cmd.Run()
}
```

### Phase 5: 統合・テスト (1-2週間)

#### 5.1 Docker Compose設定
```yaml
# docker-compose.yml
version: '3.8'

services:
  server:
    build:
      context: .
      dockerfile: server/Dockerfile
    container_name: go-grpc-server
    ports:
      - "80:80"    # HTTP/2
      - "443:443"  # HTTP/2 HTTPS
      - "4433:4433" # HTTP/3
    networks:
      benchnet:
        ipv4_address: 172.30.0.2

  client:
    build:
      context: .
      dockerfile: client/Dockerfile
    container_name: go-grpc-client
    networks:
      benchnet:
        ipv4_address: 172.30.0.3
    volumes:
      - ./logs:/logs
    depends_on:
      - router
      - server

  router:
    build:
      context: .
      dockerfile: router/Dockerfile
    container_name: go-grpc-router
    networks:
      benchnet:
        ipv4_address: 172.30.0.254
    cap_add:
      - NET_ADMIN
    privileged: true

networks:
  benchnet:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/24
```

#### 5.2 ベンチマークスクリプト移植
```go
// scripts/benchmark.go
package main

func main() {
    testCases := []struct {
        delay int
        loss  int
    }{
        {0, 3},    // 0ms delay, 3% loss
        {75, 3},   // 75ms delay, 3% loss
        {150, 3},  // 150ms delay, 3% loss
        {225, 3},  // 225ms delay, 3% loss
    }

    for _, tc := range testCases {
        // ネットワーク条件適用
        // HTTP/2 ベンチマーク実行
        // HTTP/3 ベンチマーク実行
        // 結果収集・分析
    }
}
```

## 実装上の考慮事項

### 1. パフォーマンス最適化
- **HTTP/3**: quic-goの設定最適化
  - 接続プールサイズ調整
  - ストリーム並行数設定
  - バッファサイズ最適化

- **gRPC**: ストリーミング最適化
  - バッチ処理実装
  - メモリプール使用
  - 並行処理制御

### 2. 互換性維持
- **プロトコル**: 既存のecho.proto維持
- **ベンチマーク**: 同一パラメータ・測定項目
- **結果形式**: CSV形式での互換性維持

### 3. 監視・デバッグ
- **ログ**: 構造化ログ (logrus/slog)
- **メトリクス**: Prometheus形式での出力
- **トレーシング**: OpenTelemetry対応

### 4. セキュリティ
- **TLS**: 既存の自己署名証明書継続
- **認証**: 必要に応じてmTLS対応

## 移行スケジュール

### Week 1-2: 基盤構築
- [ ] Go環境セットアップ
- [ ] Dockerfile作成
- [ ] 依存関係定義
- [ ] プロトコルバッファ設定

### Week 3-4: サーバー実装
- [ ] HTTP/2 + gRPC サーバー
- [ ] HTTP/3 + gRPC サーバー
- [ ] 基本テスト実装

### Week 5-6: クライアント実装
- [ ] ベンチマーククライアント
- [ ] データ分析機能
- [ ] レポート生成

### Week 7: ルーター実装
- [ ] ネットワークエミュレーション制御
- [ ] 統合テスト

### Week 8: 統合・検証
- [ ] 全体統合テスト
- [ ] パフォーマンス検証
- [ ] 既存ベンチマークとの比較

## 期待される効果

### 1. 開発効率向上
- **言語統一**: Go言語による統一開発環境
- **型安全性**: 静的型付けによるバグ削減
- **並行処理**: Goroutineによる効率的な並行処理

### 2. パフォーマンス向上
- **HTTP/3**: quic-goの最適化された実装
- **メモリ効率**: Goのガベージコレクション最適化
- **ネットワーク**: より効率的なプロトコル実装

### 3. 保守性向上
- **コード可読性**: シンプルなGo構文
- **テスト**: 標準テストフレームワーク
- **デバッグ**: 豊富なデバッグツール

## リスク管理

### 1. 技術リスク
- **quic-go安定性**: 最新版の安定性確認
- **gRPC互換性**: HTTP/3 + gRPCの互換性検証
- **パフォーマンス**: 既存実装との性能比較

### 2. 対応策
- **段階的移行**: 既存環境との並行運用
- **フォールバック**: 問題時の既存実装への復帰
- **継続的検証**: 各段階での性能検証

## 結論

この移行計画により、Go言語ベースの統一された技術スタックで、既存の実験内容とベンチマークを維持しながら、より効率的で保守性の高いシステムを構築できます。段階的な実装により、リスクを最小化しつつ、期待される効果を最大化できます。
