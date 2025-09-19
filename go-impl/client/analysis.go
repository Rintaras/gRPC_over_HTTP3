package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"
)

func generateCSVReport(results []BenchmarkResult, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return fmt.Errorf("failed to create CSV file: %v", err)
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// ヘッダー
	header := []string{
		"Protocol", "Delay(ms)", "Loss(%)", "TotalRequests", "SuccessfulReqs",
		"FailedReqs", "TotalTime(ms)", "AvgLatency(ms)", "MinLatency(ms)",
		"MaxLatency(ms)", "P95Latency(ms)", "P99Latency(ms)", "Throughput(rps)", "ErrorRate(%)",
	}
	if err := writer.Write(header); err != nil {
		return fmt.Errorf("failed to write header: %v", err)
	}

	// データ
	for _, result := range results {
		record := []string{
			result.Protocol,
			strconv.Itoa(result.TestCase.Delay),
			strconv.Itoa(result.TestCase.Loss),
			strconv.Itoa(result.TotalRequests),
			strconv.Itoa(result.SuccessfulReqs),
			strconv.Itoa(result.FailedReqs),
			strconv.FormatFloat(float64(result.TotalTime.Milliseconds()), 'f', 2, 64),
			strconv.FormatFloat(float64(result.AvgLatency.Microseconds())/1000, 'f', 2, 64),
			strconv.FormatFloat(float64(result.MinLatency.Microseconds())/1000, 'f', 2, 64),
			strconv.FormatFloat(float64(result.MaxLatency.Microseconds())/1000, 'f', 2, 64),
			strconv.FormatFloat(float64(result.P95Latency.Microseconds())/1000, 'f', 2, 64),
			strconv.FormatFloat(float64(result.P99Latency.Microseconds())/1000, 'f', 2, 64),
			strconv.FormatFloat(result.Throughput, 'f', 2, 64),
			strconv.FormatFloat(result.ErrorRate*100, 'f', 2, 64),
		}
		if err := writer.Write(record); err != nil {
			return fmt.Errorf("failed to write record: %v", err)
		}
	}

	return nil
}

func generatePerformanceReport(results []BenchmarkResult, logDir string) error {
	timestamp := time.Now().Format("20060102_150405")
	reportFile := filepath.Join(logDir, fmt.Sprintf("performance_report_%s.txt", timestamp))

	file, err := os.Create(reportFile)
	if err != nil {
		return fmt.Errorf("failed to create report file: %v", err)
	}
	defer file.Close()

	fmt.Fprintf(file, "# HTTP/2 vs HTTP/3 Performance Benchmark Report\n\n")
	fmt.Fprintf(file, "**Generated:** %s\n\n", time.Now().Format("2006-01-02 15:04:05"))
	fmt.Fprintf(file, "## Summary\n\n")

	// プロトコル別サマリー
	http2Results := filterResults(results, "HTTP/2")
	http3Results := filterResults(results, "HTTP/3")

	if len(http2Results) > 0 {
		avgHTTP2 := calculateAverage(http2Results)
		fmt.Fprintf(file, "### HTTP/2 Average Performance\n")
		fmt.Fprintf(file, "- Average Latency: %.2f ms\n", float64(avgHTTP2.AvgLatency.Microseconds())/1000)
		fmt.Fprintf(file, "- P95 Latency: %.2f ms\n", float64(avgHTTP2.P95Latency.Microseconds())/1000)
		fmt.Fprintf(file, "- P99 Latency: %.2f ms\n", float64(avgHTTP2.P99Latency.Microseconds())/1000)
		fmt.Fprintf(file, "- Throughput: %.2f req/s\n", avgHTTP2.Throughput)
		fmt.Fprintf(file, "- Error Rate: %.2f%%\n\n", avgHTTP2.ErrorRate*100)
	}

	if len(http3Results) > 0 {
		avgHTTP3 := calculateAverage(http3Results)
		fmt.Fprintf(file, "### HTTP/3 Average Performance\n")
		fmt.Fprintf(file, "- Average Latency: %.2f ms\n", float64(avgHTTP3.AvgLatency.Microseconds())/1000)
		fmt.Fprintf(file, "- P95 Latency: %.2f ms\n", float64(avgHTTP3.P95Latency.Microseconds())/1000)
		fmt.Fprintf(file, "- P99 Latency: %.2f ms\n", float64(avgHTTP3.P99Latency.Microseconds())/1000)
		fmt.Fprintf(file, "- Throughput: %.2f req/s\n", avgHTTP3.Throughput)
		fmt.Fprintf(file, "- Error Rate: %.2f%%\n\n", avgHTTP3.ErrorRate*100)
	}

	// 詳細結果
	fmt.Fprintf(file, "## Detailed Results\n\n")
	fmt.Fprintf(file, "| Protocol | Delay(ms) | Loss(%%) | Avg Latency(ms) | P95 Latency(ms) | P99 Latency(ms) | Throughput(rps) | Error Rate(%%) |\n")
	fmt.Fprintf(file, "|----------|-----------|---------|-----------------|-----------------|-----------------|-----------------|----------------|\n")

	for _, result := range results {
		fmt.Fprintf(file, "| %s | %d | %d | %.2f | %.2f | %.2f | %.2f | %.2f |\n",
			result.Protocol,
			result.TestCase.Delay,
			result.TestCase.Loss,
			float64(result.AvgLatency.Microseconds())/1000,
			float64(result.P95Latency.Microseconds())/1000,
			float64(result.P99Latency.Microseconds())/1000,
			result.Throughput,
			result.ErrorRate*100,
		)
	}

	return nil
}

func filterResults(results []BenchmarkResult, protocol string) []BenchmarkResult {
	var filtered []BenchmarkResult
	for _, result := range results {
		if result.Protocol == protocol {
			filtered = append(filtered, result)
		}
	}
	return filtered
}

func calculateAverage(results []BenchmarkResult) BenchmarkResult {
	if len(results) == 0 {
		return BenchmarkResult{}
	}

	var totalAvgLatency, totalP95Latency, totalP99Latency time.Duration
	var totalThroughput, totalErrorRate float64
	var totalRequests, totalSuccessfulReqs, totalFailedReqs int

	for _, result := range results {
		totalAvgLatency += result.AvgLatency
		totalP95Latency += result.P95Latency
		totalP99Latency += result.P99Latency
		totalThroughput += result.Throughput
		totalErrorRate += result.ErrorRate
		totalRequests += result.TotalRequests
		totalSuccessfulReqs += result.SuccessfulReqs
		totalFailedReqs += result.FailedReqs
	}

	count := len(results)
	return BenchmarkResult{
		TotalRequests:  totalRequests,
		SuccessfulReqs: totalSuccessfulReqs,
		FailedReqs:     totalFailedReqs,
		AvgLatency:     totalAvgLatency / time.Duration(count),
		P95Latency:     totalP95Latency / time.Duration(count),
		P99Latency:     totalP99Latency / time.Duration(count),
		Throughput:     totalThroughput / float64(count),
		ErrorRate:      totalErrorRate / float64(count),
	}
}
