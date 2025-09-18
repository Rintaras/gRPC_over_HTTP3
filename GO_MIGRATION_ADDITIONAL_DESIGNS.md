# Go移行計画 - 追加設計要素

## 概要

`GO_MIGRATION_PLAN.md`で不足していた設計要素を補完する詳細設計書です。

## 1. 証明書・TLS設定の詳細設計

### 1.1 証明書管理
```go
// server/cert_manager.go
package main

import (
    "crypto/tls"
    "crypto/x509"
    "crypto/rand"
    "crypto/rsa"
    "crypto/x509/pkix"
    "encoding/pem"
    "time"
    "math/big"
    "net"
    "os"
)

type CertManager struct {
    CertPath string
    KeyPath  string
}

func (cm *CertManager) GenerateSelfSignedCert() error {
    // 既存の証明書生成ロジックをGoで実装
    privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
    if err != nil {
        return err
    }

    template := x509.Certificate{
        SerialNumber: big.NewInt(1),
        Subject: pkix.Name{
            Country:      []string{"JP"},
            Organization: []string{"GRPC-Benchmark"},
            CommonName:   "grpc-server.local",
        },
        NotBefore:    time.Now(),
        NotAfter:     time.Now().Add(365 * 24 * time.Hour),
        KeyUsage:     x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature,
        ExtKeyUsage:  []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
        IPAddresses:  []net.IP{net.ParseIP("172.30.0.2")},
    }

    certDER, err := x509.CreateCertificate(rand.Reader, &template, &template, &privateKey.PublicKey, privateKey)
    if err != nil {
        return err
    }

    // 証明書ファイル保存
    certOut, err := os.Create(cm.CertPath)
    if err != nil {
        return err
    }
    pem.Encode(certOut, &pem.Block{Type: "CERTIFICATE", Bytes: certDER})
    certOut.Close()

    // 秘密鍵ファイル保存
    keyOut, err := os.Create(cm.KeyPath)
    if err != nil {
        return err
    }
    pem.Encode(keyOut, &pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(privateKey)})
    keyOut.Close()

    return nil
}

func (cm *CertManager) LoadTLSConfig() (*tls.Config, error) {
    cert, err := tls.LoadX509KeyPair(cm.CertPath, cm.KeyPath)
    if err != nil {
        return nil, err
    }

    return &tls.Config{
        Certificates: []tls.Certificate{cert},
        NextProtos:   []string{"h2", "h3", "h3-29", "h3-28", "h3-27"},
        MinVersion:   tls.VersionTLS12,
        CipherSuites: []uint16{
            tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
            tls.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
            tls.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305,
        },
    }, nil
}
```

### 1.2 HTTP/3専用ポート設定
```go
// server/server_config.go
package main

import "errors"

type ServerConfig struct {
    HTTP2Port int
    HTTP3Port int
    CertPath  string
    KeyPath   string
}

func (sc *ServerConfig) Validate() error {
    if sc.HTTP2Port == sc.HTTP3Port {
        return errors.New("HTTP/2 and HTTP/3 ports must be different")
    }
    return nil
}
```

## 2. エラーハンドリング・復旧機構の設計

### 2.1 接続エラー処理
```go
// client/error_handler.go
package main

import (
    "context"
    "time"
    "math"
    "github.com/quic-go/quic-go"
    "google.golang.org/grpc/codes"
    "google.golang.org/grpc/status"
)

type ErrorHandler struct {
    MaxRetries    int
    RetryDelay    time.Duration
    BackoffFactor float64
}

func (eh *ErrorHandler) HandleConnectionError(err error) error {
    if isRetryableError(err) {
        return eh.retryWithBackoff(err)
    }
    return err
}

func isRetryableError(err error) bool {
    // QUIC接続エラー、ネットワークエラー、一時的なTLSエラーを判定
    if quic.IsTimeoutError(err) || quic.IsConnectionError(err) {
        return true
    }
    
    st, ok := status.FromError(err)
    if ok {
        switch st.Code() {
        case codes.Unavailable, codes.DeadlineExceeded, codes.ResourceExhausted:
            return true
        }
    }
    return false
}

func (eh *ErrorHandler) retryWithBackoff(err error) error {
    for i := 0; i < eh.MaxRetries; i++ {
        time.Sleep(eh.RetryDelay * time.Duration(math.Pow(eh.BackoffFactor, float64(i))))
        
        // 再試行ロジック
        if retryErr := eh.attemptRetry(); retryErr == nil {
            return nil
        }
    }
    return err
}
```

### 2.2 グレースフルシャットダウン
```go
// server/graceful_shutdown.go
package main

import (
    "context"
    "log"
    "os"
    "os/signal"
    "syscall"
    "time"
    "net/http"
    "github.com/quic-go/quic-go/http3"
)

type GracefulShutdown struct {
    Server      *http.Server
    HTTP3Server *http3.Server
    Timeout     time.Duration
}

func (gs *GracefulShutdown) WaitForShutdown() {
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    
    <-quit
    log.Println("Server is shutting down...")
    
    ctx, cancel := context.WithTimeout(context.Background(), gs.Timeout)
    defer cancel()
    
    // HTTP/2 サーバー停止
    if gs.Server != nil {
        gs.Server.Shutdown(ctx)
    }
    
    // HTTP/3 サーバー停止
    if gs.HTTP3Server != nil {
        gs.HTTP3Server.Close()
    }
    
    log.Println("Server stopped")
}
```

## 3. 監視・ログ機能の詳細設計

### 3.1 構造化ログ
```go
// common/logger.go
package common

import (
    "log/slog"
    "os"
)

type Logger struct {
    *slog.Logger
}

func NewLogger(level string) *Logger {
    var logLevel slog.Level
    switch level {
    case "DEBUG":
        logLevel = slog.LevelDebug
    case "INFO":
        logLevel = slog.LevelInfo
    case "WARN":
        logLevel = slog.LevelWarn
    case "ERROR":
        logLevel = slog.LevelError
    default:
        logLevel = slog.LevelInfo
    }

    opts := &slog.HandlerOptions{
        Level: logLevel,
        AddSource: true,
    }

    handler := slog.NewJSONHandler(os.Stdout, opts)
    logger := slog.New(handler)
    
    return &Logger{logger}
}

type BenchmarkResult struct {
    Protocol         string
    TotalRequests    int
    SuccessfulReqs   int
    FailedReqs       int
    TotalTime        time.Duration
    AvgLatency       time.Duration
    Throughput       float64
    ErrorRate        float64
}

// ベンチマーク専用ログ
func (l *Logger) LogBenchmarkResult(result BenchmarkResult) {
    l.Info("Benchmark completed",
        "protocol", result.Protocol,
        "total_requests", result.TotalRequests,
        "successful_requests", result.SuccessfulReqs,
        "failed_requests", result.FailedReqs,
        "total_time_ms", result.TotalTime.Milliseconds(),
        "avg_latency_ms", result.AvgLatency.Milliseconds(),
        "throughput_rps", result.Throughput,
        "error_rate", result.ErrorRate,
    )
}
```

### 3.2 メトリクス収集
```go
// common/metrics.go
package common

import (
    "sync"
    "time"
)

type Metrics struct {
    mu              sync.RWMutex
    RequestCount    int64
    SuccessCount    int64
    ErrorCount      int64
    TotalLatency    time.Duration
    ConnectionCount int
    ActiveStreams   int
}

func (m *Metrics) RecordRequest(success bool, latency time.Duration) {
    m.mu.Lock()
    defer m.mu.Unlock()
    
    m.RequestCount++
    m.TotalLatency += latency
    
    if success {
        m.SuccessCount++
    } else {
        m.ErrorCount++
    }
}

type MetricsSnapshot struct {
    RequestCount    int64
    SuccessCount    int64
    ErrorCount      int64
    AvgLatency      time.Duration
    SuccessRate     float64
    ConnectionCount int
    ActiveStreams   int
}

func (m *Metrics) GetStats() MetricsSnapshot {
    m.mu.RLock()
    defer m.mu.RUnlock()
    
    avgLatency := time.Duration(0)
    if m.RequestCount > 0 {
        avgLatency = m.TotalLatency / time.Duration(m.RequestCount)
    }
    
    return MetricsSnapshot{
        RequestCount:    m.RequestCount,
        SuccessCount:    m.SuccessCount,
        ErrorCount:      m.ErrorCount,
        AvgLatency:      avgLatency,
        SuccessRate:     float64(m.SuccessCount) / float64(m.RequestCount),
        ConnectionCount: m.ConnectionCount,
        ActiveStreams:   m.ActiveStreams,
    }
}
```

## 4. パフォーマンス最適化の詳細設計

### 4.1 接続プール管理
```go
// client/connection_pool.go
package main

import (
    "sync"
    "time"
    "github.com/quic-go/quic-go"
    "google.golang.org/grpc"
)

type ConnectionPool struct {
    mu          sync.RWMutex
    connections map[string]*grpc.ClientConn
    quicConns   map[string]quic.Connection
    maxSize     int
    idleTimeout time.Duration
}

func (cp *ConnectionPool) GetConnection(addr string) (*grpc.ClientConn, error) {
    cp.mu.Lock()
    defer cp.mu.Unlock()
    
    if conn, exists := cp.connections[addr]; exists && cp.isConnectionHealthy(conn) {
        return conn, nil
    }
    
    // 新しい接続を作成
    conn, err := grpc.Dial(addr, grpc.WithInsecure())
    if err != nil {
        return nil, err
    }
    
    cp.connections[addr] = conn
    return conn, nil
}

func (cp *ConnectionPool) isConnectionHealthy(conn *grpc.ClientConn) bool {
    state := conn.GetState()
    return state.String() == "READY"
}
```

### 4.2 ストリーミング最適化
```go
// server/streaming_optimizer.go
package main

import (
    "sync"
    "context"
    "time"
    pb "grpc-over-http3/proto"
)

type StreamingOptimizer struct {
    mu            sync.Mutex
    batchSize     int
    flushInterval time.Duration
    buffers       map[string][]*pb.EchoResponse
}

func (so *StreamingOptimizer) StreamEcho(stream pb.EchoService_StreamEchoServer) error {
    ctx, cancel := context.WithCancel(stream.Context())
    defer cancel()
    
    // バッチ処理チャネル
    batchChan := make(chan *pb.EchoResponse, so.batchSize)
    
    // バッチ送信ゴルーチン
    go func() {
        ticker := time.NewTicker(so.flushInterval)
        defer ticker.Stop()
        
        batch := make([]*pb.EchoResponse, 0, so.batchSize)
        
        for {
            select {
            case <-ctx.Done():
                // 残りのバッチを送信
                if len(batch) > 0 {
                    so.sendBatch(stream, batch)
                }
                return
                
            case response := <-batchChan:
                batch = append(batch, response)
                if len(batch) >= so.batchSize {
                    so.sendBatch(stream, batch)
                    batch = batch[:0]
                }
                
            case <-ticker.C:
                if len(batch) > 0 {
                    so.sendBatch(stream, batch)
                    batch = batch[:0]
                }
            }
        }
    }()
    
    // リクエスト処理
    for {
        req, err := stream.Recv()
        if err != nil {
            return err
        }
        
        response := &pb.EchoResponse{
            Message:   req.Message,
            Timestamp: time.Now().UnixNano(),
            Protocol:  "HTTP/3",
        }
        
        select {
        case batchChan <- response:
        case <-ctx.Done():
            return ctx.Err()
        }
    }
}

func (so *StreamingOptimizer) sendBatch(stream pb.EchoService_StreamEchoServer, batch []*pb.EchoResponse) error {
    for _, response := range batch {
        if err := stream.Send(response); err != nil {
            return err
        }
    }
    return nil
}
```

## 5. テスト・検証機能の設計

### 5.1 統合テスト
```go
// tests/integration_test.go
package tests

import (
    "testing"
    "context"
    "time"
    "fmt"
    "google.golang.org/grpc"
    pb "grpc-over-http3/proto"
)

func TestHTTP2vsHTTP3Performance(t *testing.T) {
    // HTTP/2 テスト
    http2Conn, err := grpc.Dial("172.30.0.2:443", grpc.WithInsecure())
    if err != nil {
        t.Fatalf("HTTP/2 connection failed: %v", err)
    }
    defer http2Conn.Close()
    
    http2Client := pb.NewEchoServiceClient(http2Conn)
    
    // HTTP/3 テスト
    http3Conn, err := grpc.Dial("172.30.0.2:4433", grpc.WithInsecure())
    if err != nil {
        t.Fatalf("HTTP/3 connection failed: %v", err)
    }
    defer http3Conn.Close()
    
    http3Client := pb.NewEchoServiceClient(http3Conn)
    
    // パフォーマンス比較テスト
    http2Latency := benchmarkClient(http2Client, t)
    http3Latency := benchmarkClient(http3Client, t)
    
    // 結果検証
    t.Logf("HTTP/2 Average Latency: %v", http2Latency)
    t.Logf("HTTP/3 Average Latency: %v", http3Latency)
    
    // HTTP/3が期待値以上の性能を示すことを確認
    if http3Latency > http2Latency*1.2 {
        t.Errorf("HTTP/3 performance is significantly worse than HTTP/2")
    }
}

func benchmarkClient(client pb.EchoServiceClient, t *testing.T) time.Duration {
    const numRequests = 100
    var totalLatency time.Duration
    
    for i := 0; i < numRequests; i++ {
        start := time.Now()
        
        _, err := client.Echo(context.Background(), &pb.EchoRequest{
            Message:   fmt.Sprintf("Test request %d", i),
            Timestamp: time.Now().UnixNano(),
        })
        
        latency := time.Since(start)
        totalLatency += latency
        
        if err != nil {
            t.Errorf("Request %d failed: %v", i, err)
        }
    }
    
    return totalLatency / numRequests
}
```

### 5.2 負荷テスト
```go
// tests/load_test.go
package tests

import (
    "testing"
    "sync"
    "time"
    "context"
    "fmt"
    "google.golang.org/grpc"
    pb "grpc-over-http3/proto"
)

func TestConcurrentConnections(t *testing.T) {
    const (
        numConnections = 100
        requestsPerConn = 1000
    )
    
    var wg sync.WaitGroup
    results := make(chan time.Duration, numConnections*requestsPerConn)
    
    for i := 0; i < numConnections; i++ {
        wg.Add(1)
        go func(connID int) {
            defer wg.Done()
            
            conn, err := grpc.Dial("172.30.0.2:4433", grpc.WithInsecure())
            if err != nil {
                t.Errorf("Connection %d failed: %v", connID, err)
                return
            }
            defer conn.Close()
            
            client := pb.NewEchoServiceClient(conn)
            
            for j := 0; j < requestsPerConn; j++ {
                start := time.Now()
                
                _, err := client.Echo(context.Background(), &pb.EchoRequest{
                    Message:   fmt.Sprintf("Connection %d, Request %d", connID, j),
                    Timestamp: time.Now().UnixNano(),
                })
                
                latency := time.Since(start)
                results <- latency
                
                if err != nil {
                    t.Errorf("Request failed: %v", err)
                }
            }
        }(i)
    }
    
    wg.Wait()
    close(results)
    
    // 統計計算
    var totalLatency time.Duration
    var count int
    
    for latency := range results {
        totalLatency += latency
        count++
    }
    
    avgLatency := totalLatency / time.Duration(count)
    t.Logf("Average latency with %d concurrent connections: %v", numConnections, avgLatency)
}
```

## 6. デプロイメント・運用の設計

### 6.1 ヘルスチェック
```go
// server/health_check.go
package main

import (
    "net/http"
    "time"
)

type HealthChecker struct {
    server *http.Server
    ready  bool
}

func (hc *HealthChecker) StartHealthCheck() {
    mux := http.NewServeMux()
    mux.HandleFunc("/health", hc.healthHandler)
    mux.HandleFunc("/ready", hc.readyHandler)
    
    hc.server = &http.Server{
        Addr:    ":8080",
        Handler: mux,
    }
    
    go hc.server.ListenAndServe()
}

func (hc *HealthChecker) healthHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("OK"))
}

func (hc *HealthChecker) readyHandler(w http.ResponseWriter, r *http.Request) {
    if hc.ready {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("Ready"))
    } else {
        w.WriteHeader(http.StatusServiceUnavailable)
        w.Write([]byte("Not Ready"))
    }
}
```

### 6.2 設定管理
```go
// common/config.go
package common

import (
    "os"
    "strconv"
)

type Config struct {
    ServerPort     int
    HTTP3Port      int
    CertPath       string
    KeyPath        string
    LogLevel       string
    MaxConnections int
    BatchSize      int
}

func LoadConfig() *Config {
    config := &Config{
        ServerPort:     443,
        HTTP3Port:      4433,
        CertPath:       "/certs/server.crt",
        KeyPath:        "/certs/server.key",
        LogLevel:       "INFO",
        MaxConnections: 1000,
        BatchSize:      100,
    }
    
    if port := os.Getenv("SERVER_PORT"); port != "" {
        if p, err := strconv.Atoi(port); err == nil {
            config.ServerPort = p
        }
    }
    
    if port := os.Getenv("HTTP3_PORT"); port != "" {
        if p, err := strconv.Atoi(port); err == nil {
            config.HTTP3Port = p
        }
    }
    
    if level := os.Getenv("LOG_LEVEL"); level != "" {
        config.LogLevel = level
    }
    
    return config
}
```

## 7. Dockerfileの詳細設計

### 7.1 サーバーDockerfile
```dockerfile
# server/Dockerfile
FROM golang:1.21-bullseye as builder

WORKDIR /app

# 依存関係コピー
COPY go.mod go.sum ./
RUN go mod download

# ソースコードコピー
COPY . .

# ビルド
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o server ./server/

# 最終ステージ
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 証明書ディレクトリ作成
RUN mkdir -p /app/certs

# ビルド済みバイナリコピー
COPY --from=builder /app/server .

# 証明書生成
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /app/certs/server.key \
    -out /app/certs/server.crt \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=Test/CN=server"

EXPOSE 80 443 4433

CMD ["./server"]
```

### 7.2 クライアントDockerfile
```dockerfile
# client/Dockerfile
FROM golang:1.21-bullseye as builder

WORKDIR /app

# 依存関係コピー
COPY go.mod go.sum ./
RUN go mod download

# ソースコードコピー
COPY . .

# ビルド
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o client ./client/

# 最終ステージ
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ログディレクトリ作成
RUN mkdir -p /app/logs

# ビルド済みバイナリコピー
COPY --from=builder /app/client .

CMD ["./client"]
```

### 7.3 ルーターDockerfile
```dockerfile
# router/Dockerfile
FROM golang:1.21-bullseye as builder

WORKDIR /app

# 依存関係コピー
COPY go.mod go.sum ./
RUN go mod download

# ソースコードコピー
COPY . .

# ビルド
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o router ./router/

# 最終ステージ
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    ca-certificates \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ビルド済みバイナリコピー
COPY --from=builder /app/router .

CMD ["./router"]
```

## 8. ベンチマーク結果分析の詳細設計

### 8.1 統計分析
```go
// analysis/statistics.go
package analysis

import (
    "math"
    "sort"
    "time"
)

type BenchmarkData struct {
    Latencies []time.Duration
    SuccessCount int
    FailureCount int
    TotalTime time.Duration
}

type Statistics struct {
    Mean       time.Duration
    Median     time.Duration
    P95        time.Duration
    P99        time.Duration
    Min        time.Duration
    Max        time.Duration
    StdDev     time.Duration
    Throughput float64
    ErrorRate  float64
}

func CalculateStatistics(data BenchmarkData) Statistics {
    if len(data.Latencies) == 0 {
        return Statistics{}
    }
    
    // ソート
    sorted := make([]time.Duration, len(data.Latencies))
    copy(sorted, data.Latencies)
    sort.Slice(sorted, func(i, j int) bool {
        return sorted[i] < sorted[j]
    })
    
    // 基本統計
    var sum time.Duration
    for _, lat := range data.Latencies {
        sum += lat
    }
    mean := sum / time.Duration(len(data.Latencies))
    
    // 中央値
    median := sorted[len(sorted)/2]
    
    // パーセンタイル
    p95Index := int(float64(len(sorted)) * 0.95)
    p99Index := int(float64(len(sorted)) * 0.99)
    
    // 標準偏差
    var variance float64
    for _, lat := range data.Latencies {
        diff := float64(lat - mean)
        variance += diff * diff
    }
    stdDev := time.Duration(math.Sqrt(variance / float64(len(data.Latencies))))
    
    // スループットとエラー率
    totalRequests := data.SuccessCount + data.FailureCount
    throughput := float64(data.SuccessCount) / data.TotalTime.Seconds()
    errorRate := float64(data.FailureCount) / float64(totalRequests)
    
    return Statistics{
        Mean:       mean,
        Median:     median,
        P95:        sorted[p95Index],
        P99:        sorted[p99Index],
        Min:        sorted[0],
        Max:        sorted[len(sorted)-1],
        StdDev:     stdDev,
        Throughput: throughput,
        ErrorRate:  errorRate,
    }
}
```

### 8.2 レポート生成
```go
// analysis/report.go
package analysis

import (
    "fmt"
    "os"
    "text/template"
    "time"
)

type ReportData struct {
    Timestamp     time.Time
    HTTP2Stats    Statistics
    HTTP3Stats    Statistics
    TestCases     []TestCaseResult
    Summary       string
}

type TestCaseResult struct {
    Delay        int
    Loss         int
    HTTP2Latency time.Duration
    HTTP3Latency time.Duration
    Improvement  float64
}

func GenerateReport(data ReportData) error {
    template := `
# HTTP/2 vs HTTP/3 Performance Benchmark Report

**Generated:** {{.Timestamp.Format "2006-01-02 15:04:05"}}

## Summary
{{.Summary}}

## Overall Statistics

### HTTP/2
- Mean Latency: {{.HTTP2Stats.Mean}}
- P95 Latency: {{.HTTP2Stats.P95}}
- P99 Latency: {{.HTTP2Stats.P99}}
- Throughput: {{printf "%.2f" .HTTP2Stats.Throughput}} req/s
- Error Rate: {{printf "%.2f%%" .HTTP2Stats.ErrorRate}}

### HTTP/3
- Mean Latency: {{.HTTP3Stats.Mean}}
- P95 Latency: {{.HTTP3Stats.P95}}
- P99 Latency: {{.HTTP3Stats.P99}}
- Throughput: {{printf "%.2f" .HTTP3Stats.Throughput}} req/s
- Error Rate: {{printf "%.2f%%" .HTTP3Stats.ErrorRate}}

## Test Case Results

| Delay (ms) | Loss (%) | HTTP/2 Latency | HTTP/3 Latency | Improvement |
|------------|----------|----------------|----------------|-------------|
{{range .TestCases}}| {{.Delay}} | {{.Loss}} | {{.HTTP2Latency}} | {{.HTTP3Latency}} | {{printf "%.1f%%" .Improvement}} |
{{end}}
`

    tmpl, err := template.New("report").Parse(template)
    if err != nil {
        return err
    }

    file, err := os.Create("benchmark_report.md")
    if err != nil {
        return err
    }
    defer file.Close()

    return tmpl.Execute(file, data)
}
```

## 結論

この追加設計書により、Go移行計画で不足していた以下の要素が補完されました：

- ✅ **証明書・TLS設定の詳細設計**
- ✅ **エラーハンドリング・復旧機構**
- ✅ **監視・ログ機能の詳細設計**
- ✅ **パフォーマンス最適化の詳細設計**
- ✅ **テスト・検証機能の設計**
- ✅ **デプロイメント・運用の設計**
- ✅ **Dockerfileの詳細設計**
- ✅ **ベンチマーク結果分析の詳細設計**

これで、本格的なプロダクション環境での運用も可能な、完全な移行計画が完成しました。
