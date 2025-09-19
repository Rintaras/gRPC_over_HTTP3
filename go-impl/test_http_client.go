package main

import (
	"crypto/tls"
	"io"
	"net/http"
	"time"

	"grpc-over-http3/common"

	"github.com/quic-go/quic-go/http3"
)

func main() {
	logger := common.NewLogger("INFO")
	logger.Info("================================================")
	logger.Info("Testing HTTP/2 and HTTP/3 basic connectivity")
	logger.Info("================================================")

	// HTTP/2 テスト
	logger.Info("Testing HTTP/2 connectivity...")
	testHTTP2(logger)

	// HTTP/3 テスト
	logger.Info("Testing HTTP/3 connectivity...")
	testHTTP3(logger)
}

func testHTTP2(logger *common.Logger) {
	client := &http.Client{
		Timeout: 10 * time.Second,
	}

	// ヘルスチェック
	logger.Info("Testing /health endpoint")
	resp, err := client.Get("http://172.31.0.2:443/health")
	if err != nil {
		logger.Error("Failed to connect to /health", "error", err)
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("Failed to read response", "error", err)
		return
	}

	logger.Info("Health check response",
		"status", resp.Status,
		"protocol", resp.Proto,
		"body", string(body))

	// Echo エンドポイント
	logger.Info("Testing /echo endpoint")
	resp, err = client.Get("http://172.31.0.2:443/echo")
	if err != nil {
		logger.Error("Failed to connect to /echo", "error", err)
		return
	}
	defer resp.Body.Close()

	body, err = io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("Failed to read echo response", "error", err)
		return
	}

	logger.Info("Echo response",
		"status", resp.Status,
		"protocol", resp.Proto,
		"body", string(body))

	logger.Info("HTTP/2 test completed successfully")
}

func testHTTP3(logger *common.Logger) {
	// HTTP/3クライアント（TLS証明書検証を無効化）
	client := &http.Client{
		Transport: &http3.RoundTripper{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: true,
			},
		},
		Timeout: 10 * time.Second,
	}

	// ヘルスチェック
	logger.Info("Testing /health endpoint")
	resp, err := client.Get("https://172.31.0.2:4433/health")
	if err != nil {
		logger.Error("Failed to connect to /health", "error", err)
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("Failed to read response", "error", err)
		return
	}

	logger.Info("Health check response",
		"status", resp.Status,
		"protocol", resp.Proto,
		"body", string(body))

	// Echo エンドポイント
	logger.Info("Testing /echo endpoint")
	resp, err = client.Get("https://172.31.0.2:4433/echo")
	if err != nil {
		logger.Error("Failed to connect to /echo", "error", err)
		return
	}
	defer resp.Body.Close()

	body, err = io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("Failed to read echo response", "error", err)
		return
	}

	logger.Info("Echo response",
		"status", resp.Status,
		"protocol", resp.Proto,
		"body", string(body))

	logger.Info("HTTP/3 test completed successfully")
}
