package main

import (
	"bytes"
	"crypto/tls"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log"
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
	// リソース管理を初期化
	resourceManager := common.NewResourceManager()

	// リソース固定化を実行
	if err := resourceManager.FixResources(); err != nil {
		log.Printf("リソース固定化エラー: %v", err)
	}

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
		Requests:   1000, // 各条件で1000回（統計的信頼性をさらに向上）
		Timeout:    30 * time.Second,
		Delays:     []int{0, 75, 150, 225}, // 0ms, 75ms, 150ms, 225ms
		LossRate:   0,                      // パケットロス率0%統一
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

		// システム安定化（さらに延長）
		logger.Info("Stabilizing system", "duration", "10s")
		time.Sleep(10 * time.Second)

		// HTTP/2 ベンチマーク
		logger.Info("Running HTTP/2 latency test", "requests", config.Requests)
		http2Result := runHTTP2LatencyTest(config, delay)
		allResults = append(allResults, http2Result)

		// プロトコル間の間隔（延長）
		logger.Info("Waiting between protocols", "duration", "10s")
		time.Sleep(10 * time.Second)

		// HTTP/3 ベンチマーク
		logger.Info("Running HTTP/3 latency test", "requests", config.Requests)
		http3Result := runHTTP3LatencyTest(config, delay)
		allResults = append(allResults, http3Result)

		// テストケース間の間隔（延長）
		logger.Info("Test case completed", "delay_ms", delay)
		logger.Info("Waiting between test cases", "duration", "10s")
		time.Sleep(10 * time.Second)
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

	// リソースクリーンアップ
	resourceManager.CleanupResources()
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

		// 進行状況表示（1000リクエストに合わせて調整）
		if (i+1)%100 == 0 || i+1 == config.Requests {
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

	// UDPバッファサイズを設定
	transport := &http3.RoundTripper{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
		// QUIC設定はデフォルトを使用
	}

	client := &http.Client{
		Transport: transport,
		Timeout:   config.Timeout,
	}

	// HTTP/3接続のウォームアップ（初回接続のオーバーヘッドを排除）
	logger.Info("Warming up HTTP/3 connection")
	warmupClient := &http.Client{
		Transport: transport,
		Timeout:   10 * time.Second,
	}

	for i := 0; i < 3; i++ {
		resp, err := warmupClient.Get(fmt.Sprintf("https://%s:%d/health", config.ServerAddr, config.HTTP3Port))
		if err != nil {
			logger.Warn("Warmup request failed", "attempt", i+1, "error", err)
		} else {
			resp.Body.Close()
		}
		time.Sleep(100 * time.Millisecond)
	}
	logger.Info("HTTP/3 warmup completed")

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

		// 進行状況表示（1000リクエストに合わせて調整）
		if (i+1)%100 == 0 || i+1 == config.Requests {
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

	// 統計計算（フィルタリング後のデータを使用）

	// 平均（異常値除外前）
	var sum time.Duration
	for _, latency := range latencies {
		sum += latency
	}
	avgLatency := sum / time.Duration(len(latencies))

	// 異常値（アウトライアー）を除外
	// 平均の3倍以上または10ms以上の値を除外
	outlierThreshold := avgLatency * 3
	if outlierThreshold < 10*time.Millisecond {
		outlierThreshold = 10 * time.Millisecond
	}

	filteredLatencies := []time.Duration{}
	for _, latency := range latencies {
		if latency <= outlierThreshold {
			filteredLatencies = append(filteredLatencies, latency)
		}
	}

	// フィルタリング後のデータが少なすぎる場合は元のデータを使用
	if len(filteredLatencies) < len(latencies)/2 {
		filteredLatencies = latencies
	}

	// フィルタリング後のデータで再ソート
	sort.Slice(filteredLatencies, func(i, j int) bool {
		return filteredLatencies[i] < filteredLatencies[j]
	})

	// フィルタリング後の平均を再計算
	var filteredSum time.Duration
	for _, latency := range filteredLatencies {
		filteredSum += latency
	}
	avgLatency = filteredSum / time.Duration(len(filteredLatencies))

	// 最小値・最大値（フィルタリング後）
	minLatency := filteredLatencies[0]
	maxLatency := filteredLatencies[len(filteredLatencies)-1]

	// 中央値（フィルタリング後）
	medianLatency := filteredLatencies[len(filteredLatencies)/2]

	// P95, P99（フィルタリング後）
	p95Index := int(float64(len(filteredLatencies)) * 0.95)
	p99Index := int(float64(len(filteredLatencies)) * 0.99)
	if p95Index >= len(filteredLatencies) {
		p95Index = len(filteredLatencies) - 1
	}
	if p99Index >= len(filteredLatencies) {
		p99Index = len(filteredLatencies) - 1
	}

	p95Latency := filteredLatencies[p95Index]
	p99Latency := filteredLatencies[p99Index]

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
		Latencies:     filteredLatencies,
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
		fmt.Printf("%-10s %-8d %-10d %-10d %-10.3f %-10.3f %-10.3f %-10.3f %-10.3f\n",
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

	for _, delay := range []int{0, 75, 150, 225} {
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

func saveResultsToFiles(results []LatencyResult, logDir string, logger *common.Logger) error {
	logger.Info("Saving results to files", "directory", logDir)

	// 1. JSON形式で結果を保存
	jsonFile := filepath.Join(logDir, "latency_results.json")
	if err := saveResultsAsJSON(results, jsonFile); err != nil {
		return fmt.Errorf("failed to save JSON results: %v", err)
	}
	logger.Info("JSON results saved", "file", jsonFile)

	// 2. CSV形式で結果を保存
	csvFile := filepath.Join(logDir, "latency_results.csv")
	if err := saveResultsAsCSV(results, csvFile); err != nil {
		return fmt.Errorf("failed to save CSV results: %v", err)
	}
	logger.Info("CSV results saved", "file", csvFile)

	// 3. テキストレポートを保存
	reportFile := filepath.Join(logDir, "latency_report.txt")
	if err := saveResultsAsReport(results, reportFile); err != nil {
		return fmt.Errorf("failed to save text report: %v", err)
	}
	logger.Info("Text report saved", "file", reportFile)

	// 4. グラフを生成して保存
	graphFile := filepath.Join(logDir, "latency_comparison.png")
	if err := generateLatencyGraph(results, graphFile); err != nil {
		return fmt.Errorf("failed to generate graph: %v", err)
	}
	logger.Info("Graph saved", "file", graphFile)

	return nil
}

func saveResultsAsJSON(results []LatencyResult, filename string) error {
	data, err := json.MarshalIndent(results, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filename, data, 0644)
}

func saveResultsAsCSV(results []LatencyResult, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// ヘッダー
	header := []string{
		"Protocol", "Delay(ms)", "Requests", "Success", "Failures",
		"Min(ms)", "Max(ms)", "Avg(ms)", "Median(ms)", "P95(ms)", "P99(ms)",
	}
	if err := writer.Write(header); err != nil {
		return err
	}

	// データ
	for _, result := range results {
		record := []string{
			result.Protocol,
			strconv.Itoa(result.Delay),
			strconv.Itoa(result.Requests),
			strconv.Itoa(result.Successes),
			strconv.Itoa(result.Failures),
			fmt.Sprintf("%.2f", float64(result.MinLatency.Nanoseconds())/1e6),
			fmt.Sprintf("%.2f", float64(result.MaxLatency.Nanoseconds())/1e6),
			fmt.Sprintf("%.2f", float64(result.AvgLatency.Nanoseconds())/1e6),
			fmt.Sprintf("%.2f", float64(result.MedianLatency.Nanoseconds())/1e6),
			fmt.Sprintf("%.2f", float64(result.P95Latency.Nanoseconds())/1e6),
			fmt.Sprintf("%.2f", float64(result.P99Latency.Nanoseconds())/1e6),
		}
		if err := writer.Write(record); err != nil {
			return err
		}
	}

	return nil
}

func saveResultsAsReport(results []LatencyResult, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	// レポートヘッダー
	fmt.Fprintf(file, "HTTP/2 and HTTP/3 Latency Benchmark Report\n")
	fmt.Fprintf(file, "Generated at: %s\n", time.Now().Format("2006-01-02 15:04:05"))
	fmt.Fprintf(file, "%s\n", strings.Repeat("=", 80))

	// 結果テーブル
	fmt.Fprintf(file, "\nResults Summary:\n")
	fmt.Fprintf(file, "%s\n", strings.Repeat("-", 80))
	fmt.Fprintf(file, "%-10s %-8s %-10s %-10s %-10s %-10s %-10s %-10s %-10s\n",
		"Protocol", "Delay(ms)", "Requests", "Success", "Min(ms)", "Max(ms)", "Avg(ms)", "P95(ms)", "P99(ms)")

	for _, result := range results {
		fmt.Fprintf(file, "%-10s %-8d %-10d %-10d %-10.2f %-10.2f %-10.2f %-10.2f %-10.2f\n",
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

	// 詳細分析
	fmt.Fprintf(file, "\n%s\n", strings.Repeat("=", 80))
	fmt.Fprintf(file, "Detailed Analysis\n")
	fmt.Fprintf(file, "%s\n", strings.Repeat("=", 80))

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

	for _, delay := range []int{0, 75, 150, 225} {
		http2Result, http2Exists := http2Results[delay]
		http3Result, http3Exists := http3Results[delay]

		if http2Exists && http3Exists {
			fmt.Fprintf(file, "\nDelay %dms Comparison:\n", delay)
			fmt.Fprintf(file, "  HTTP/2 Avg: %.2f ms\n", float64(http2Result.AvgLatency.Nanoseconds())/1e6)
			fmt.Fprintf(file, "  HTTP/3 Avg: %.2f ms\n", float64(http3Result.AvgLatency.Nanoseconds())/1e6)

			diff := float64(http3Result.AvgLatency.Nanoseconds()-http2Result.AvgLatency.Nanoseconds()) / 1e6
			if diff > 0 {
				fmt.Fprintf(file, "  HTTP/3 is %.2f ms slower than HTTP/2\n", diff)
			} else {
				fmt.Fprintf(file, "  HTTP/3 is %.2f ms faster than HTTP/2\n", -diff)
			}
		}
	}

	return nil
}

func generateLatencyGraph(results []LatencyResult, filename string) error {
    p := plot.New()

    p.Title.Text = "HTTP/2 vs HTTP/3 Latency (Bar)"
    p.Y.Label.Text = "Average Latency (ms)"

    // 遅延ごとの平均値を収集
    delays := []int{0, 75, 150, 225}
    http2Map := map[int]float64{}
    http3Map := map[int]float64{}
    for _, r := range results {
        avgMs := float64(r.AvgLatency.Nanoseconds()) / 1e6
        if r.Protocol == "HTTP/2" {
            http2Map[r.Delay] = avgMs
        } else if r.Protocol == "HTTP/3" {
            http3Map[r.Delay] = avgMs
        }
    }

    // 値をplotter.Valuesに詰める（遅延の順序を固定）
    http2Vals := make(plotter.Values, 0, len(delays))
    http3Vals := make(plotter.Values, 0, len(delays))
    labels := make([]string, 0, len(delays))
    for _, d := range delays {
        http2Vals = append(http2Vals, http2Map[d])
        http3Vals = append(http3Vals, http3Map[d])
        labels = append(labels, fmt.Sprintf("%d", d))
    }

    // 棒の幅とオフセットを設定（グループ化された棒グラフ）
    barWidth := vg.Points(18)

    http2Bars, err := plotter.NewBarChart(http2Vals, barWidth)
    if err != nil {
        return err
    }
    http2Bars.LineStyle.Width = vg.Length(0)
    http2Bars.Color = plotutil.Color(0)
    http2Bars.Offset = -barWidth / 2

    http3Bars, err := plotter.NewBarChart(http3Vals, barWidth)
    if err != nil {
        return err
    }
    http3Bars.LineStyle.Width = vg.Length(0)
    http3Bars.Color = plotutil.Color(1)
    http3Bars.Offset = barWidth / 2

    p.Add(http2Bars, http3Bars)
    p.Legend.Add("HTTP/2", http2Bars)
    p.Legend.Add("HTTP/3", http3Bars)

    // X軸ラベルを遅延カテゴリに
    p.NominalX(labels...)

    // グリッド追加
    p.Add(plotter.NewGrid())

    return p.Save(8*vg.Inch, 6*vg.Inch, filename)
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
