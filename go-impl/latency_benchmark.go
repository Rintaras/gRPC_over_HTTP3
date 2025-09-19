package main

import (
	"bytes"
	"crypto/tls"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"grpc-over-http3/common"

	"github.com/quic-go/quic-go/http3"
	"gonum.org/v1/plot"
	"gonum.org/v1/plot/plotter"
	"gonum.org/v1/plot/plotutil"
	"gonum.org/v1/plot/vg"
)

type LatencyTestConfig struct {
	Requests   int           // リクエスト回数
	Timeout    time.Duration // タイムアウト
	Delays     []int         // テストする遅延値（ms）
	LossRate   int           // パケットロス率（%）
	ServerAddr string        // サーバーアドレス
	HTTP2Port  int           // HTTP/2ポート
	HTTP3Port  int           // HTTP/3ポート
}

type LatencyResult struct {
	Protocol      string          `json:"protocol"`
	Delay         int             `json:"delay_ms"`
	Requests      int             `json:"requests"`
	Successes     int             `json:"successes"`
	Failures      int             `json:"failures"`
	MinLatency    time.Duration   `json:"min_latency_ms"`
	MaxLatency    time.Duration   `json:"max_latency_ms"`
	AvgLatency    time.Duration   `json:"avg_latency_ms"`
	MedianLatency time.Duration   `json:"median_latency_ms"`
	P95Latency    time.Duration   `json:"p95_latency_ms"`
	P99Latency    time.Duration   `json:"p99_latency_ms"`
	Latencies     []time.Duration `json:"latencies"`
}

func main() {
	logger := common.NewLogger("INFO")
	logger.Info("================================================")
	logger.Info("Starting HTTP/2 and HTTP/3 Latency Benchmark")
	logger.Info("================================================")

	// ログディレクトリ作成
	timestamp := time.Now().Format("20060102_150405")
	logDir := filepath.Join("/logs", fmt.Sprintf("latency_benchmark_%s", timestamp))
	if err := os.MkdirAll(logDir, 0755); err != nil {
		logger.Error("Failed to create log directory", "error", err)
		return
	}
	logger.Info("Log directory created", "path", logDir)

	config := LatencyTestConfig{
		Requests:   100, // 各条件で100回
		Timeout:    30 * time.Second,
		Delays:     []int{0, 100, 200}, // 0ms, 100ms, 200ms
		LossRate:   0,                  // パケットロス率0%統一
		ServerAddr: "172.31.0.2",
		HTTP2Port:  443,
		HTTP3Port:  4433,
	}

	var allResults []LatencyResult

	// 各遅延条件でテスト実行
	for _, delay := range config.Delays {
		logger.Info("================================================")
		logger.Info("Testing delay", "delay_ms", delay, "loss_rate", config.LossRate)
		logger.Info("================================================")

		// ネットワーク条件設定
		if err := setNetworkConditions(delay, config.LossRate); err != nil {
			logger.Error("Failed to set network conditions", "error", err)
			continue
		}

		// システム安定化
		logger.Info("Stabilizing system", "duration", "3s")
		time.Sleep(3 * time.Second)

		// HTTP/2 ベンチマーク
		logger.Info("Running HTTP/2 latency test", "requests", config.Requests)
		http2Result := runHTTP2LatencyTest(config, delay)
		allResults = append(allResults, http2Result)

		// プロトコル間の間隔
		logger.Info("Waiting between protocols", "duration", "2s")
		time.Sleep(2 * time.Second)

		// HTTP/3 ベンチマーク
		logger.Info("Running HTTP/3 latency test", "requests", config.Requests)
		http3Result := runHTTP3LatencyTest(config, delay)
		allResults = append(allResults, http3Result)

		// テストケース間の間隔
		logger.Info("Test case completed", "delay_ms", delay)
		logger.Info("Waiting between test cases", "duration", "2s")
		time.Sleep(2 * time.Second)
	}

	// 結果出力
	logger.Info("================================================")
	logger.Info("Latency Benchmark Results")
	logger.Info("================================================")
	printLatencyResults(allResults)

	// 結果をファイルに保存
	if err := saveResultsToFiles(allResults, logDir, logger); err != nil {
		logger.Error("Failed to save results to files", "error", err)
	}

	// ネットワーク設定クリア
	if err := clearNetworkConditions(); err != nil {
		logger.Error("Failed to clear network conditions", "error", err)
	}

	logger.Info("================================================")
	logger.Info("Benchmark completed", "log_directory", logDir)
	logger.Info("================================================")
}

func runHTTP2LatencyTest(config LatencyTestConfig, delay int) LatencyResult {
	logger := common.NewLogger("INFO")
	logger.Info("Starting HTTP/2 latency test", "delay_ms", delay, "requests", config.Requests)

	client := &http.Client{
		Timeout: config.Timeout,
	}

	var latencies []time.Duration
	successes := 0
	failures := 0

	startTime := time.Now()

	for i := 0; i < config.Requests; i++ {
		requestStart := time.Now()

		resp, err := client.Get(fmt.Sprintf("http://%s:%d/health", config.ServerAddr, config.HTTP2Port))
		if err != nil {
			logger.Error("Request failed", "request", i+1, "error", err)
			failures++
			continue
		}

		// レスポンス読み込み
		_, err = io.ReadAll(resp.Body)
		resp.Body.Close()

		if err != nil {
			logger.Error("Failed to read response", "request", i+1, "error", err)
			failures++
			continue
		}

		latency := time.Since(requestStart)
		latencies = append(latencies, latency)
		successes++

		// 進行状況表示
		if (i+1)%10 == 0 || i+1 == config.Requests {
			logger.Info("Progress",
				"completed", i+1,
				"total", config.Requests,
				"successes", successes,
				"failures", failures,
				"current_latency", latency.Round(time.Millisecond))
		}
	}

	totalTime := time.Since(startTime)
	result := calculateLatencyStats("HTTP/2", delay, latencies, successes, failures, totalTime)

	logger.Info("HTTP/2 test completed",
		"delay_ms", delay,
		"successes", successes,
		"failures", failures,
		"avg_latency", result.AvgLatency.Round(time.Millisecond))

	return result
}

func runHTTP3LatencyTest(config LatencyTestConfig, delay int) LatencyResult {
	logger := common.NewLogger("INFO")
	logger.Info("Starting HTTP/3 latency test", "delay_ms", delay, "requests", config.Requests)

	client := &http.Client{
		Transport: &http3.RoundTripper{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: true,
			},
		},
		Timeout: config.Timeout,
	}

	var latencies []time.Duration
	successes := 0
	failures := 0

	startTime := time.Now()

	for i := 0; i < config.Requests; i++ {
		requestStart := time.Now()

		resp, err := client.Get(fmt.Sprintf("https://%s:%d/health", config.ServerAddr, config.HTTP3Port))
		if err != nil {
			logger.Error("Request failed", "request", i+1, "error", err)
			failures++
			continue
		}

		// レスポンス読み込み
		_, err = io.ReadAll(resp.Body)
		resp.Body.Close()

		if err != nil {
			logger.Error("Failed to read response", "request", i+1, "error", err)
			failures++
			continue
		}

		latency := time.Since(requestStart)
		latencies = append(latencies, latency)
		successes++

		// 進行状況表示
		if (i+1)%10 == 0 || i+1 == config.Requests {
			logger.Info("Progress",
				"completed", i+1,
				"total", config.Requests,
				"successes", successes,
				"failures", failures,
				"current_latency", latency.Round(time.Millisecond))
		}
	}

	totalTime := time.Since(startTime)
	result := calculateLatencyStats("HTTP/3", delay, latencies, successes, failures, totalTime)

	logger.Info("HTTP/3 test completed",
		"delay_ms", delay,
		"successes", successes,
		"failures", failures,
		"avg_latency", result.AvgLatency.Round(time.Millisecond))

	return result
}

func calculateLatencyStats(protocol string, delay int, latencies []time.Duration, successes, failures int, totalTime time.Duration) LatencyResult {
	if len(latencies) == 0 {
		return LatencyResult{
			Protocol:  protocol,
			Delay:     delay,
			Requests:  successes + failures,
			Successes: successes,
			Failures:  failures,
		}
	}

	// レイテンシをソート
	sortedLatencies := make([]time.Duration, len(latencies))
	copy(sortedLatencies, latencies)
	sort.Slice(sortedLatencies, func(i, j int) bool {
		return sortedLatencies[i] < sortedLatencies[j]
	})

	// 統計計算
	minLatency := sortedLatencies[0]
	maxLatency := sortedLatencies[len(sortedLatencies)-1]

	// 平均
	var sum time.Duration
	for _, latency := range latencies {
		sum += latency
	}
	avgLatency := sum / time.Duration(len(latencies))

	// 中央値
	medianLatency := sortedLatencies[len(sortedLatencies)/2]

	// P95, P99
	p95Index := int(float64(len(sortedLatencies)) * 0.95)
	p99Index := int(float64(len(sortedLatencies)) * 0.99)
	if p95Index >= len(sortedLatencies) {
		p95Index = len(sortedLatencies) - 1
	}
	if p99Index >= len(sortedLatencies) {
		p99Index = len(sortedLatencies) - 1
	}

	p95Latency := sortedLatencies[p95Index]
	p99Latency := sortedLatencies[p99Index]

	return LatencyResult{
		Protocol:      protocol,
		Delay:         delay,
		Requests:      successes + failures,
		Successes:     successes,
		Failures:      failures,
		MinLatency:    minLatency,
		MaxLatency:    maxLatency,
		AvgLatency:    avgLatency,
		MedianLatency: medianLatency,
		P95Latency:    p95Latency,
		P99Latency:    p99Latency,
		Latencies:     latencies,
	}
}

func printLatencyResults(results []LatencyResult) {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("HTTP/2 and HTTP/3 Latency Benchmark Results")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Printf("%-10s %-8s %-10s %-10s %-10s %-10s %-10s %-10s %-10s\n",
		"Protocol", "Delay(ms)", "Requests", "Success", "Min(ms)", "Max(ms)", "Avg(ms)", "P95(ms)", "P99(ms)")
	fmt.Println(strings.Repeat("-", 80))

	for _, result := range results {
		fmt.Printf("%-10s %-8d %-10d %-10d %-10.2f %-10.2f %-10.2f %-10.2f %-10.2f\n",
			result.Protocol,
			result.Delay,
			result.Requests,
			result.Successes,
			float64(result.MinLatency.Nanoseconds())/1e6,
			float64(result.MaxLatency.Nanoseconds())/1e6,
			float64(result.AvgLatency.Nanoseconds())/1e6,
			float64(result.P95Latency.Nanoseconds())/1e6,
			float64(result.P99Latency.Nanoseconds())/1e6)
	}

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("Detailed Analysis")
	fmt.Println(strings.Repeat("=", 80))

	// HTTP/2 vs HTTP/3 比較
	http2Results := make(map[int]LatencyResult)
	http3Results := make(map[int]LatencyResult)

	for _, result := range results {
		if result.Protocol == "HTTP/2" {
			http2Results[result.Delay] = result
		} else if result.Protocol == "HTTP/3" {
			http3Results[result.Delay] = result
		}
	}

	for _, delay := range []int{0, 100, 200} {
		http2Result, http2Exists := http2Results[delay]
		http3Result, http3Exists := http3Results[delay]

		if http2Exists && http3Exists {
			fmt.Printf("\nDelay %dms Comparison:\n", delay)
			fmt.Printf("  HTTP/2 Avg: %.2f ms\n", float64(http2Result.AvgLatency.Nanoseconds())/1e6)
			fmt.Printf("  HTTP/3 Avg: %.2f ms\n", float64(http3Result.AvgLatency.Nanoseconds())/1e6)

			diff := float64(http3Result.AvgLatency.Nanoseconds()-http2Result.AvgLatency.Nanoseconds()) / 1e6
			if diff > 0 {
				fmt.Printf("  HTTP/3 is %.2f ms slower than HTTP/2\n", diff)
			} else {
				fmt.Printf("  HTTP/3 is %.2f ms faster than HTTP/2\n", -diff)
			}
		}
	}

	fmt.Println("\n" + strings.Repeat("=", 80))
}

func setNetworkConditions(delay, loss int) error {
	config := map[string]interface{}{
		"delay":     delay,
		"loss":      loss,
		"bandwidth": 0, // 帯域制限なし
	}

	return setRouterNetworkConfig(config)
}

func clearNetworkConditions() error {
	return clearRouterNetworkConfig()
}

func setRouterNetworkConfig(config map[string]interface{}) error {
	jsonData, err := json.Marshal(config)
	if err != nil {
		return fmt.Errorf("failed to marshal config: %v", err)
	}

	resp, err := http.Post("http://172.31.0.254:8080/network/config",
		"application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to set network config: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("router returned status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

func clearRouterNetworkConfig() error {
	resp, err := http.Post("http://172.31.0.254:8080/network/clear",
		"application/json", nil)
	if err != nil {
		return fmt.Errorf("failed to clear network config: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("router returned status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}
