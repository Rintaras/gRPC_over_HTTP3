package main

import (
	"crypto/tls"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/quic-go/quic-go/http3"
)

func main() {
	url := os.Getenv("TARGET_URL")
	if url == "" {
		url = "https://localhost:8443/large"
	}

	iterations := 1
	if len(os.Args) > 1 {
		fmt.Sscanf(os.Args[1], "%d", &iterations)
	}

	client := &http.Client{
		Transport: &http3.RoundTripper{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: true,
			},
		},
		Timeout: 120 * time.Second,
	}

	fmt.Printf("HTTP/3テスト: %s\n", url)
	fmt.Printf("試行回数: %d\n\n", iterations)

	var totalTime time.Duration
	var totalBytes int64
	successCount := 0

	for i := 1; i <= iterations; i++ {
		start := time.Now()
		
		resp, err := client.Get(url)
		if err != nil {
			fmt.Printf("試行 %d: エラー - %v\n", i, err)
			continue
		}

		bytes, err := io.Copy(io.Discard, resp.Body)
		resp.Body.Close()

		elapsed := time.Since(start)

		if err != nil {
			fmt.Printf("試行 %d: 読み込みエラー - %v\n", i, err)
			continue
		}

		totalTime += elapsed
		totalBytes += bytes
		successCount++

		speed := float64(bytes) / elapsed.Seconds() / 1024
		fmt.Printf("試行 %d: %.3f秒, %d bytes, %.2f KB/s (プロトコル: %s)\n", 
			i, elapsed.Seconds(), bytes, speed, resp.Proto)
	}

	if successCount > 0 {
		avgTime := totalTime.Seconds() / float64(successCount)
		avgSpeed := float64(totalBytes) / totalTime.Seconds() / 1024
		
		fmt.Printf("\n=== 結果 ===\n")
		fmt.Printf("成功: %d/%d\n", successCount, iterations)
		fmt.Printf("平均時間: %.3f秒\n", avgTime)
		fmt.Printf("平均速度: %.2f KB/s\n", avgSpeed)
		fmt.Printf("合計転送: %d bytes\n", totalBytes)
	} else {
		fmt.Println("\n全ての試行が失敗しました")
		os.Exit(1)
	}
}

