package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
)

type LatencyResult struct {
	Protocol   string  `json:"protocol"`
	Delay      int     `json:"delay_ms"`
	Requests   int     `json:"requests"`
	Successes  int     `json:"successes"`
	MinLatency float64 `json:"min_latency_ns"` // ナノ秒単位
	MaxLatency float64 `json:"max_latency_ns"` // ナノ秒単位
	AvgLatency float64 `json:"avg_latency_ns"` // ナノ秒単位
	P95Latency float64 `json:"p95_latency_ns"` // ナノ秒単位
	P99Latency float64 `json:"p99_latency_ns"` // ナノ秒単位
}

type RunAnalysis struct {
	RunNumber int
	Results   []LatencyResult
}

type ComparisonSummary struct {
	Delay    int
	HTTP2Avg []float64
	HTTP3Avg []float64
	HTTP2Std float64
	HTTP3Std float64
	HTTP2Min float64
	HTTP2Max float64
	HTTP3Min float64
	HTTP3Max float64
}

func main() {
	if len(os.Args) < 2 {
		log.Fatal("使用方法: go run analyze_multiple_results.go <summary_directory>")
	}

	summaryDir := os.Args[1]

	fmt.Println("================================================")
	fmt.Println("複数実行結果分析")
	fmt.Println("================================================")

	// 各実行の結果を読み込み
	var runAnalyses []RunAnalysis

	for i := 1; i <= 5; i++ {
		jsonFile := filepath.Join(summaryDir, fmt.Sprintf("run_%d_results.json", i))
		if _, err := os.Stat(jsonFile); os.IsNotExist(err) {
			continue
		}

		var results []LatencyResult
		data, err := os.ReadFile(jsonFile)
		if err != nil {
			log.Printf("実行 %d の結果ファイル読み込みエラー: %v", i, err)
			continue
		}

		err = json.Unmarshal(data, &results)
		if err != nil {
			log.Printf("実行 %d のJSON解析エラー: %v", i, err)
			continue
		}

		runAnalyses = append(runAnalyses, RunAnalysis{
			RunNumber: i,
			Results:   results,
		})

		fmt.Printf("実行 %d: %d 件の結果を読み込み\n", i, len(results))
	}

	if len(runAnalyses) == 0 {
		log.Fatal("有効な実行結果が見つかりません")
	}

	fmt.Printf("\n総実行数: %d\n", len(runAnalyses))

	// 遅延値ごとに分析
	delays := []int{0, 75, 150, 225}
	var comparisons []ComparisonSummary

	for _, delay := range delays {
		var http2Avgs, http3Avgs []float64

		// 各実行から該当遅延の結果を抽出
		for _, run := range runAnalyses {
			for _, result := range run.Results {
				if result.Delay == delay {
					if result.Protocol == "HTTP/2" {
						http2Avgs = append(http2Avgs, result.AvgLatency)
					} else if result.Protocol == "HTTP/3" {
						http3Avgs = append(http3Avgs, result.AvgLatency)
					}
				}
			}
		}

		if len(http2Avgs) > 0 && len(http3Avgs) > 0 {
			comparison := ComparisonSummary{
				Delay:    delay,
				HTTP2Avg: http2Avgs,
				HTTP3Avg: http3Avgs,
				HTTP2Std: calculateStdDev(http2Avgs),
				HTTP3Std: calculateStdDev(http3Avgs),
				HTTP2Min: min(http2Avgs),
				HTTP2Max: max(http2Avgs),
				HTTP3Min: min(http3Avgs),
				HTTP3Max: max(http3Avgs),
			}
			comparisons = append(comparisons, comparison)
		}
	}

	// 結果表示
	fmt.Println("\n================================================")
	fmt.Println("遅延別統計分析")
	fmt.Println("================================================")

	for _, comp := range comparisons {
		fmt.Printf("\n遅延 %dms:\n", comp.Delay)
		fmt.Printf("  HTTP/2: 平均=%.3fms, 標準偏差=%.3fms, 範囲=[%.3f-%.3f]ms\n",
			average(comp.HTTP2Avg), comp.HTTP2Std, comp.HTTP2Min, comp.HTTP2Max)
		fmt.Printf("  HTTP/3: 平均=%.3fms, 標準偏差=%.3fms, 範囲=[%.3f-%.3f]ms\n",
			average(comp.HTTP3Avg), comp.HTTP3Std, comp.HTTP3Min, comp.HTTP3Max)

		// 安定性評価
		http2Stability := evaluateStability(comp.HTTP2Std, average(comp.HTTP2Avg))
		http3Stability := evaluateStability(comp.HTTP3Std, average(comp.HTTP3Avg))

		fmt.Printf("  HTTP/2 安定性: %s (CV=%.1f%%)\n", http2Stability, (comp.HTTP2Std/average(comp.HTTP2Avg))*100)
		fmt.Printf("  HTTP/3 安定性: %s (CV=%.1f%%)\n", http3Stability, (comp.HTTP3Std/average(comp.HTTP3Avg))*100)
	}

	// 詳細結果をCSVに出力
	outputCSV(summaryDir, runAnalyses)

	fmt.Println("\n================================================")
	fmt.Println("分析完了")
	fmt.Println("詳細CSV: ", filepath.Join(summaryDir, "detailed_analysis.csv"))
	fmt.Println("================================================")
}

func calculateStdDev(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	avg := average(values)
	sum := 0.0
	for _, v := range values {
		sum += (v - avg) * (v - avg)
	}
	return sqrt(sum / float64(len(values)))
}

func average(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

func min(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	min := values[0]
	for _, v := range values {
		if v < min {
			min = v
		}
	}
	return min
}

func max(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	max := values[0]
	for _, v := range values {
		if v > max {
			max = v
		}
	}
	return max
}

func sqrt(x float64) float64 {
	// 簡易平方根実装
	if x < 0 {
		return 0
	}
	if x == 0 {
		return 0
	}

	guess := x / 2
	for i := 0; i < 10; i++ {
		guess = (guess + x/guess) / 2
	}
	return guess
}

func evaluateStability(stdDev, avg float64) string {
	if avg == 0 {
		return "N/A"
	}

	cv := (stdDev / avg) * 100

	if cv < 5 {
		return "非常に安定"
	} else if cv < 10 {
		return "安定"
	} else if cv < 20 {
		return "やや不安定"
	} else {
		return "不安定"
	}
}

func outputCSV(summaryDir string, runAnalyses []RunAnalysis) {
	csvFile := filepath.Join(summaryDir, "detailed_analysis.csv")
	file, err := os.Create(csvFile)
	if err != nil {
		log.Printf("CSVファイル作成エラー: %v", err)
		return
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// ヘッダー
	header := []string{"実行", "プロトコル", "遅延(ms)", "リクエスト数", "成功数", "最小(ms)", "最大(ms)", "平均(ms)", "P95(ms)", "P99(ms)"}
	writer.Write(header)

	// データ
	for _, run := range runAnalyses {
		for _, result := range run.Results {
			record := []string{
				strconv.Itoa(run.RunNumber),
				result.Protocol,
				strconv.Itoa(result.Delay),
				strconv.Itoa(result.Requests),
				strconv.Itoa(result.Successes),
				fmt.Sprintf("%.3f", result.MinLatency),
				fmt.Sprintf("%.3f", result.MaxLatency),
				fmt.Sprintf("%.3f", result.AvgLatency),
				fmt.Sprintf("%.3f", result.P95Latency),
				fmt.Sprintf("%.3f", result.P99Latency),
			}
			writer.Write(record)
		}
	}
}
