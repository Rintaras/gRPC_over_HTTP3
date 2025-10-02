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
	"syscall"
	"time"

	"github.com/quic-go/quic-go/http3"
	"golang.org/x/net/http2"
)

type DetailedStats struct {
	StartTime       time.Time
	EndTime         time.Time
	Duration        time.Duration
	PreemptCount    int
	ContextSwitches int
}

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

func setHighPriority() {
	err := syscall.Setpriority(syscall.PRIO_PROCESS, 0, -20)
	if err != nil {
		fmt.Printf("優先度設定エラー（無視可能）: %v\n", err)
	} else {
		fmt.Println("✅ プロセス優先度を最高に設定")
	}
}

func testHTTP2WithSchedulerAnalysis(warmup int, iterations int) {
	fmt.Println("=== HTTP/2接続テスト（スケジューラー解析付き） ===")

	runtime.GOMAXPROCS(1)
	fmt.Println("GOMAXPROCSを1に設定（シングルスレッド）")

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
			continue
		}
		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()
	}

	runtime.GC()

	fmt.Printf("\n測定開始: %d回\n", iterations)

	var durations []time.Duration
	var totalDuration time.Duration
	var schedulingDelays []time.Duration

	fmt.Println("\n詳細ログ（最初の10回）:")
	for i := 0; i < iterations; i++ {
		beforeStats := &syscall.Rusage{}
		syscall.Getrusage(syscall.RUSAGE_SELF, beforeStats)

		start := time.Now()
		resp, err := client.Get("https://172.18.0.2:8443/")
		elapsed := time.Since(start)

		afterStats := &syscall.Rusage{}
		syscall.Getrusage(syscall.RUSAGE_SELF, afterStats)

		if err != nil {
			log.Printf("HTTP/2接続エラー (試行%d): %v\n", i+1, err)
			continue
		}

		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()

		durations = append(durations, elapsed)
		totalDuration += elapsed

		voluntaryCtx := afterStats.Nvcsw - beforeStats.Nvcsw
		involuntaryCtx := afterStats.Nivcsw - beforeStats.Nivcsw

		if i < 10 {
			fmt.Printf("  試行%d: %v (自発的CS:%d, 非自発的CS:%d)\n",
				i+1, elapsed, voluntaryCtx, involuntaryCtx)
		}

		if involuntaryCtx > 0 {
			schedulingDelays = append(schedulingDelays, elapsed)
		}
	}

	avgDuration := totalDuration / time.Duration(len(durations))
	medianDuration := median(durations)

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

	p90 := percentile(durations, 90)
	p95 := percentile(durations, 95)
	p99 := percentile(durations, 99)

	fmt.Printf("\n結果:\n")
	fmt.Printf("  平均接続時間: %v\n", avgDuration)
	fmt.Printf("  中央値(P50): %v\n", medianDuration)
	fmt.Printf("  最速上位20%%の平均: %v\n", top20Avg)
	fmt.Printf("  P90: %v\n", p90)
	fmt.Printf("  P95: %v\n", p95)
	fmt.Printf("  P99: %v\n", p99)
	fmt.Printf("  スケジューリング遅延発生回数: %d回/%d回 (%.1f%%)\n",
		len(schedulingDelays), iterations, float64(len(schedulingDelays))/float64(iterations)*100)
	fmt.Println("✅ HTTP/2接続成功！")
	fmt.Println()
}

func testHTTP3WithSchedulerAnalysis(warmup int, iterations int) {
	fmt.Println("=== HTTP/3接続テスト（スケジューラー解析付き） ===")

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
			continue
		}
		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()
	}

	runtime.GC()

	fmt.Printf("\n測定開始: %d回\n", iterations)

	var durations []time.Duration
	var totalDuration time.Duration
	var schedulingDelays []time.Duration

	fmt.Println("\n詳細ログ（最初の10回）:")
	for i := 0; i < iterations; i++ {
		beforeStats := &syscall.Rusage{}
		syscall.Getrusage(syscall.RUSAGE_SELF, beforeStats)

		start := time.Now()
		resp, err := client.Get("https://172.18.0.2:8443/")
		elapsed := time.Since(start)

		afterStats := &syscall.Rusage{}
		syscall.Getrusage(syscall.RUSAGE_SELF, afterStats)

		if err != nil {
			log.Printf("HTTP/3接続エラー (試行%d): %v\n", i+1, err)
			continue
		}

		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()

		durations = append(durations, elapsed)
		totalDuration += elapsed

		voluntaryCtx := afterStats.Nvcsw - beforeStats.Nvcsw
		involuntaryCtx := afterStats.Nivcsw - beforeStats.Nivcsw

		if i < 10 {
			fmt.Printf("  試行%d: %v (自発的CS:%d, 非自発的CS:%d)\n",
				i+1, elapsed, voluntaryCtx, involuntaryCtx)
		}

		if involuntaryCtx > 0 {
			schedulingDelays = append(schedulingDelays, elapsed)
		}
	}

	avgDuration := totalDuration / time.Duration(len(durations))
	medianDuration := median(durations)

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

	p90 := percentile(durations, 90)
	p95 := percentile(durations, 95)
	p99 := percentile(durations, 99)

	fmt.Printf("\n結果:\n")
	fmt.Printf("  平均接続時間: %v\n", avgDuration)
	fmt.Printf("  中央値(P50): %v\n", medianDuration)
	fmt.Printf("  最速上位20%%の平均: %v\n", top20Avg)
	fmt.Printf("  P90: %v\n", p90)
	fmt.Printf("  P95: %v\n", p95)
	fmt.Printf("  P99: %v\n", p99)
	fmt.Printf("  スケジューリング遅延発生回数: %d回/%d回 (%.1f%%)\n",
		len(schedulingDelays), iterations, float64(len(schedulingDelays))/float64(iterations)*100)
	fmt.Println("✅ HTTP/3接続成功！")
	fmt.Println()
}

func main() {
	fmt.Println("スケジューラー解析付きベンチマーク")
	fmt.Println("==================================")
	fmt.Println()

	setHighPriority()

	debug.SetGCPercent(-1)
	fmt.Println("ガベージコレクションを無効化")

	runtime.GC()
	fmt.Println("初期GC実行完了")
	fmt.Println()

	warmup := 20
	iterations := 100

	fmt.Printf("ウォームアップ: %d回\n", warmup)
	fmt.Printf("測定回数: %d回\n\n", iterations)

	testHTTP2WithSchedulerAnalysis(warmup, iterations)

	runtime.GC()
	fmt.Println("GC実行（HTTP/2とHTTP/3の間）\n")

	testHTTP3WithSchedulerAnalysis(warmup, iterations)

	fmt.Println("ベンチマーク完了")
}
