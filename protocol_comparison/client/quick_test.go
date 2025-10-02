package main

import (
	"crypto/tls"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/quic-go/quic-go/http3"
	"golang.org/x/net/http2"
)

func testHTTP2() {
	fmt.Println("=== HTTP/2テスト ===")

	transport := &http2.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}

	client := &http.Client{
		Transport: transport,
		Timeout:   5 * time.Second,
	}

	start := time.Now()
	resp, err := client.Get("https://172.18.0.2:8443/test")
	elapsed := time.Since(start)

	if err != nil {
		fmt.Printf("❌ HTTP/2エラー: %v\n\n", err)
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	fmt.Printf("✅ HTTP/2成功\n")
	fmt.Printf("   ステータス: %d\n", resp.StatusCode)
	fmt.Printf("   レスポンス: %s\n", string(body))
	fmt.Printf("   所要時間: %v\n\n", elapsed)
}

func testHTTP3() {
	fmt.Println("=== HTTP/3テスト ===")

	roundTripper := &http3.RoundTripper{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}
	defer roundTripper.Close()

	client := &http.Client{
		Transport: roundTripper,
		Timeout:   5 * time.Second,
	}

	start := time.Now()
	resp, err := client.Get("https://172.18.0.2:8443/test")
	elapsed := time.Since(start)

	if err != nil {
		fmt.Printf("❌ HTTP/3エラー: %v\n\n", err)
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	fmt.Printf("✅ HTTP/3成功\n")
	fmt.Printf("   ステータス: %d\n", resp.StatusCode)
	fmt.Printf("   レスポンス: %s\n", string(body))
	fmt.Printf("   所要時間: %v\n\n", elapsed)
}

func main() {
	fmt.Println("プロトコル接続テスト")
	fmt.Println("====================\n")

	testHTTP2()
	testHTTP3()

	fmt.Println("テスト完了")
}
