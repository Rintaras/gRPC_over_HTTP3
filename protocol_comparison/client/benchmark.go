package main

import (
	"crypto/tls"
	"fmt"
	"io"
	"log"
	"net/http"
	"runtime"
	"runtime/debug"
	"sort"
	"time"

	"github.com/quic-go/quic-go/http3"
	"golang.org/x/net/http2"
)

func median(data []time.Duration) time.Duration {
	sorted := make([]time.Duration, len(data))
	copy(sorted, data)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i] < sorted[j]
	})

	n := len(sorted)
	if n%2 == 0 {
		return (sorted[n/2-1] + sorted[n/2]) / 2
	}
	return sorted[n/2]
}

func percentile(data []time.Duration, p float64) time.Duration {
	sorted := make([]time.Duration, len(data))
	copy(sorted, data)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i] < sorted[j]
	})

	index := int(float64(len(sorted)) * p / 100.0)
	if index >= len(sorted) {
		index = len(sorted) - 1
	}
	return sorted[index]
}

func standardDeviation(data []time.Duration, avg time.Duration) time.Duration {
	var sum float64
	for _, d := range data {
		diff := float64(d - avg)
		sum += diff * diff
	}
	variance := sum / float64(len(data))
	return time.Duration(variance)
}

func testHTTP2(warmup int, iterations int) {
	fmt.Println("=== HTTP/2接続テスト ===")

	transport := &http2.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}

	client := &http.Client{
		Transport: transport,
	}

	fmt.Printf("ウォームアップ: %d回\n", warmup)
	for i := 0; i < warmup; i++ {
		resp, err := client.Get("https://172.18.0.2:8443/")
		if err != nil {
			log.Printf("ウォームアップエラー: %v\n", err)
			continue
		}
		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()
	}

	fmt.Printf("\n測定開始: %d回\n", iterations)

	var durations []time.Duration
	var totalDuration time.Duration

	fmt.Println("\n最初の10回:")
	for i := 0; i < iterations; i++ {
		start := time.Now()
		resp, err := client.Get("https://172.18.0.2:8443/")
		elapsed := time.Since(start)

		if err != nil {
			log.Printf("HTTP/2接続エラー (試行%d): %v\n", i+1, err)
			continue
		}

		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()

		durations = append(durations, elapsed)
		totalDuration += elapsed

		if i < 10 {
			fmt.Printf("  試行%d: %v\n", i+1, elapsed)
		}
	}

	avgDuration := totalDuration / time.Duration(len(durations))
	medianDuration := median(durations)
	minDuration := durations[0]
	maxDuration := durations[0]

	for _, d := range durations {
		if d < minDuration {
			minDuration = d
		}
		if d > maxDuration {
			maxDuration = d
		}
	}

	_ = percentile(durations, 50)
	p90 := percentile(durations, 90)
	p95 := percentile(durations, 95)
	p99 := percentile(durations, 99)

	sorted := make([]time.Duration, len(durations))
	copy(sorted, durations)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i] < sorted[j]
	})

	top20Count := len(sorted) / 5
	if top20Count == 0 {
		top20Count = 1
	}
	var top20Sum time.Duration
	for i := 0; i < top20Count; i++ {
		top20Sum += sorted[i]
	}
	top20Avg := top20Sum / time.Duration(top20Count)

	fmt.Printf("\n結果:\n")
	fmt.Printf("  平均接続時間: %v\n", avgDuration)
	fmt.Printf("  中央値(P50): %v\n", medianDuration)
	fmt.Printf("  最速上位20%%の平均: %v\n", top20Avg)
	fmt.Printf("  P90: %v\n", p90)
	fmt.Printf("  P95: %v\n", p95)
	fmt.Printf("  P99: %v\n", p99)
	fmt.Printf("  最小接続時間: %v\n", minDuration)
	fmt.Printf("  最大接続時間: %v\n", maxDuration)

	outliers := 0
	threshold := avgDuration * 3
	for _, d := range durations {
		if d > threshold {
			outliers++
		}
	}
	fmt.Printf("  外れ値: %d回（平均の3倍以上）\n", outliers)
	fmt.Println("✅ HTTP/2接続成功！")
	fmt.Println()
}

func testHTTP3(warmup int, iterations int) {
	fmt.Println("=== HTTP/3接続テスト ===")

	roundTripper := &http3.RoundTripper{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}
	defer roundTripper.Close()

	client := &http.Client{
		Transport: roundTripper,
	}

	fmt.Printf("ウォームアップ: %d回\n", warmup)
	for i := 0; i < warmup; i++ {
		resp, err := client.Get("https://172.18.0.2:8443/")
		if err != nil {
			log.Printf("ウォームアップエラー: %v\n", err)
			continue
		}
		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()
	}

	fmt.Printf("\n測定開始: %d回\n", iterations)

	var durations []time.Duration
	var totalDuration time.Duration

	fmt.Println("\n最初の10回:")
	for i := 0; i < iterations; i++ {
		start := time.Now()
		resp, err := client.Get("https://172.18.0.2:8443/")
		elapsed := time.Since(start)

		if err != nil {
			log.Printf("HTTP/3接続エラー (試行%d): %v\n", i+1, err)
			continue
		}

		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()

		durations = append(durations, elapsed)
		totalDuration += elapsed

		if i < 10 {
			fmt.Printf("  試行%d: %v\n", i+1, elapsed)
		}
	}

	avgDuration := totalDuration / time.Duration(len(durations))
	medianDuration := median(durations)
	minDuration := durations[0]
	maxDuration := durations[0]

	for _, d := range durations {
		if d < minDuration {
			minDuration = d
		}
		if d > maxDuration {
			maxDuration = d
		}
	}

	_ = percentile(durations, 50)
	p90 := percentile(durations, 90)
	p95 := percentile(durations, 95)
	p99 := percentile(durations, 99)

	sorted := make([]time.Duration, len(durations))
	copy(sorted, durations)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i] < sorted[j]
	})

	top20Count := len(sorted) / 5
	if top20Count == 0 {
		top20Count = 1
	}
	var top20Sum time.Duration
	for i := 0; i < top20Count; i++ {
		top20Sum += sorted[i]
	}
	top20Avg := top20Sum / time.Duration(top20Count)

	fmt.Printf("\n結果:\n")
	fmt.Printf("  平均接続時間: %v\n", avgDuration)
	fmt.Printf("  中央値(P50): %v\n", medianDuration)
	fmt.Printf("  最速上位20%%の平均: %v\n", top20Avg)
	fmt.Printf("  P90: %v\n", p90)
	fmt.Printf("  P95: %v\n", p95)
	fmt.Printf("  P99: %v\n", p99)
	fmt.Printf("  最小接続時間: %v\n", minDuration)
	fmt.Printf("  最大接続時間: %v\n", maxDuration)

	outliers := 0
	threshold := avgDuration * 3
	for _, d := range durations {
		if d > threshold {
			outliers++
		}
	}
	fmt.Printf("  外れ値: %d回（平均の3倍以上）\n", outliers)
	fmt.Println("✅ HTTP/3接続成功！")
	fmt.Println()
}

func main() {
	fmt.Println("HTTP/2 vs HTTP/3 ベンチマーク")
	fmt.Println("==============================")
	fmt.Println()

	debug.SetGCPercent(-1)
	fmt.Println("ガベージコレクションを無効化")

	runtime.GC()
	fmt.Println("初期GC実行完了")
	fmt.Println()

	warmup := 20
	iterations := 100

	fmt.Printf("ウォームアップ: %d回\n", warmup)
	fmt.Printf("測定回数: %d回\n\n", iterations)

	testHTTP2(warmup, iterations)

	runtime.GC()
	fmt.Println("GC実行（HTTP/2とHTTP/3の間）\n")

	testHTTP3(warmup, iterations)

	fmt.Println("ベンチマーク完了")
}
