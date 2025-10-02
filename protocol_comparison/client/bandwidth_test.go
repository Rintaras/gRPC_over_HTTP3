package main

import (
	"crypto/tls"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"golang.org/x/net/http2"
)

func testBandwidth(target string, dataSize int, iterations int) {
	transport := &http2.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}
	
	client := &http.Client{
		Transport: transport,
		Timeout:   30 * time.Second,
	}
	
	var totalDuration time.Duration
	var totalBytes int64
	
	fmt.Printf("データサイズ: %d バイト x %d回\n", dataSize, iterations)
	
	for i := 0; i < iterations; i++ {
		start := time.Now()
		resp, err := client.Get(target)
		if err != nil {
			log.Printf("接続エラー: %v\n", err)
			continue
		}
		
		written, err := io.Copy(io.Discard, resp.Body)
		if err != nil {
			log.Printf("読み取りエラー: %v\n", err)
			resp.Body.Close()
			continue
		}
		
		elapsed := time.Since(start)
		resp.Body.Close()
		
		totalDuration += elapsed
		totalBytes += written
		
		if i < 5 {
			throughput := float64(written) / elapsed.Seconds() / 1024
			fmt.Printf("  試行%d: %v, %d バイト, %.2f KB/s\n", i+1, elapsed, written, throughput)
		}
	}
	
	avgDuration := totalDuration / time.Duration(iterations)
	avgThroughput := float64(totalBytes) / totalDuration.Seconds() / 1024
	
	fmt.Printf("\n結果:\n")
	fmt.Printf("  平均時間: %v\n", avgDuration)
	fmt.Printf("  総データ量: %d バイト\n", totalBytes)
	fmt.Printf("  平均スループット: %.2f KB/s\n", avgThroughput)
	fmt.Println()
}

func main() {
	fmt.Println("帯域制限テスト")
	fmt.Println("==============")
	fmt.Println()
	
	target := "https://network-router:8444/"
	
	fmt.Println("テスト1: 小さいデータ転送")
	testBandwidth(target, 1024, 10)
	
	time.Sleep(1 * time.Second)
	
	fmt.Println("テスト2: 中規模データ転送")
	testBandwidth(target, 10240, 10)
	
	time.Sleep(1 * time.Second)
	
	fmt.Println("テスト3: 大きいデータ転送")
	testBandwidth(target, 102400, 10)
	
	fmt.Println("全テスト完了")
}
