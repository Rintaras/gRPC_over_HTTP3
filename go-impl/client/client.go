package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"grpc-over-http3/common"
)

func main() {
	logger := common.NewLogger("INFO")
	logger.Info("Starting gRPC over HTTP/2 and HTTP/3 benchmark client")

	// ベンチマーク設定
	config := BenchmarkConfig{
		Requests:      50000,
		Connections:   100,
		Threads:       20,
		MaxConcurrent: 100,
		ServerAddr:    "172.30.0.2",
		TestCases: []TestCase{
			{Delay: 0, Loss: 3},
			{Delay: 75, Loss: 3},
			{Delay: 150, Loss: 3},
			{Delay: 225, Loss: 3},
		},
	}

	// ログディレクトリ作成
	timestamp := time.Now().Format("20060102_150405")
	logDir := filepath.Join("/logs", fmt.Sprintf("benchmark_%s", timestamp))
	if err := os.MkdirAll(logDir, 0755); err != nil {
		log.Fatalf("Failed to create log directory: %v", err)
	}

	var allResults []BenchmarkResult

	// 各テストケースでベンチマーク実行
	for _, testCase := range config.TestCases {
		logger.Info("Running test case", "delay", testCase.Delay, "loss", testCase.Loss)

		// ネットワーク条件を設定（ルーター経由で制御）
		if err := setNetworkConditions(testCase.Delay, testCase.Loss); err != nil {
			logger.Error("Failed to set network conditions", "error", err)
			continue
		}

		// システム安定化
		logger.Info("Stabilizing system", "duration", "30s")
		time.Sleep(30 * time.Second)

		// HTTP/2 ベンチマーク
		logger.Info("Running HTTP/2 benchmark")
		http2Config := config
		http2Config.Protocol = "HTTP/2"
		http2Result := runHTTP2Benchmark(http2Config)
		http2Result.TestCase = testCase
		allResults = append(allResults, http2Result)

		// プロトコル間の間隔
		logger.Info("Waiting between protocols", "duration", "30s")
		time.Sleep(30 * time.Second)

		// HTTP/3 ベンチマーク
		logger.Info("Running HTTP/3 benchmark")
		http3Config := config
		http3Config.Protocol = "HTTP/3"
		http3Result := runHTTP3Benchmark(http3Config)
		http3Result.TestCase = testCase
		allResults = append(allResults, http3Result)

		// テストケース間の間隔
		logger.Info("Waiting between test cases", "duration", "15s")
		time.Sleep(15 * time.Second)
	}

	// 結果をCSVで出力
	csvFile := filepath.Join(logDir, "benchmark_results.csv")
	if err := generateCSVReport(allResults, csvFile); err != nil {
		logger.Error("Failed to generate CSV report", "error", err)
	} else {
		logger.Info("CSV report generated", "file", csvFile)
	}

	// パフォーマンスレポート生成
	if err := generatePerformanceReport(allResults, logDir); err != nil {
		logger.Error("Failed to generate performance report", "error", err)
	} else {
		logger.Info("Performance report generated", "directory", logDir)
	}

	// 結果サマリー出力
	logger.Info("Benchmark completed")
	printSummary(allResults)
}

func setNetworkConditions(delay, loss int) error {
	// ルーターコンテナにネットワーク条件を設定するコマンドを送信
	// 実際の実装では、ルーターコンテナとの通信を行う
	log.Printf("Setting network conditions: delay=%dms, loss=%d%%", delay, loss)
	return nil
}

func printSummary(results []BenchmarkResult) {
	logger := common.NewLogger("INFO")

	logger.Info("=== BENCHMARK SUMMARY ===")

	http2Results := filterResults(results, "HTTP/2")
	http3Results := filterResults(results, "HTTP/3")

	if len(http2Results) > 0 {
		avgHTTP2 := calculateAverage(http2Results)
		logger.Info("HTTP/2 Average Performance",
			"avg_latency_ms", float64(avgHTTP2.AvgLatency.Microseconds())/1000,
			"p95_latency_ms", float64(avgHTTP2.P95Latency.Microseconds())/1000,
			"throughput_rps", avgHTTP2.Throughput,
			"error_rate_percent", avgHTTP2.ErrorRate*100,
		)
	}

	if len(http3Results) > 0 {
		avgHTTP3 := calculateAverage(http3Results)
		logger.Info("HTTP/3 Average Performance",
			"avg_latency_ms", float64(avgHTTP3.AvgLatency.Microseconds())/1000,
			"p95_latency_ms", float64(avgHTTP3.P95Latency.Microseconds())/1000,
			"throughput_rps", avgHTTP3.Throughput,
			"error_rate_percent", avgHTTP3.ErrorRate*100,
		)
	}

	logger.Info("=== END SUMMARY ===")
}
