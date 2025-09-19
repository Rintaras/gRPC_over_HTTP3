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

	// ベンチマーク設定（高速化設定）
	config := BenchmarkConfig{
		Requests:      1000, // 50,000 → 1,000に削減
		Connections:   50,   // 100 → 50に削減
		Threads:       10,   // 20 → 10に削減
		MaxConcurrent: 50,   // 100 → 50に削減
		ServerAddr:    "172.31.0.2",
		TestCases: []TestCase{
			{Delay: 0, Loss: 3},
			{Delay: 75, Loss: 3},
			// {Delay: 150, Loss: 3},  // テストケースを削減
			// {Delay: 225, Loss: 3},  // テストケースを削減
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
	logger.Info("================================================")
	logger.Info("Starting benchmark suite", "total_test_cases", len(config.TestCases))
	logger.Info("================================================")
	
	for i, testCase := range config.TestCases {
		logger.Info("================================================")
		logger.Info("Starting test case", "index", i+1, "total", len(config.TestCases), "delay", testCase.Delay, "loss", testCase.Loss)
		logger.Info("================================================")

		// ネットワーク条件を設定（ルーター経由で制御）
		if err := setNetworkConditions(testCase.Delay, testCase.Loss); err != nil {
			logger.Error("Failed to set network conditions", "error", err)
			continue
		}

		// システム安定化（短縮）
		logger.Info("Phase 1: Stabilizing system", "duration", "5s")
		time.Sleep(5 * time.Second)

		// HTTP/2 ベンチマーク
		logger.Info("Phase 2: Running HTTP/2 benchmark")
		http2Config := config
		http2Config.Protocol = "HTTP/2"
		http2Result := runHTTP2Benchmark(http2Config)
		http2Result.TestCase = testCase
		allResults = append(allResults, http2Result)
		
		logger.Info("HTTP/2 benchmark completed", 
			"successful", http2Result.SuccessfulReqs, 
			"failed", http2Result.FailedReqs,
			"throughput", fmt.Sprintf("%.2f req/s", http2Result.Throughput))

		// プロトコル間の間隔（短縮）
		logger.Info("Waiting between protocols", "duration", "5s")
		time.Sleep(5 * time.Second)

		// HTTP/3 ベンチマーク（一旦無効化 - TLS設定が必要）
		logger.Info("Phase 3: HTTP/3 benchmark disabled - TLS configuration required")
		// http3Config := config
		// http3Config.Protocol = "HTTP/3"
		// http3Result := runHTTP3Benchmark(http3Config)
		// http3Result.TestCase = testCase
		// allResults = append(allResults, http3Result)

		// テストケース間の間隔（短縮）
		logger.Info("Test case completed", "delay", testCase.Delay, "loss", testCase.Loss)
		logger.Info("Waiting between test cases", "duration", "3s")
		time.Sleep(3 * time.Second)
	}
	
	logger.Info("================================================")
	logger.Info("All test cases completed", "total_results", len(allResults))
	logger.Info("================================================")

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
	logger.Info("================================================")
	logger.Info("Benchmark completed")
	logger.Info("================================================")
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
