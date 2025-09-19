package main

import (
	"io"
	"net/http"
	"time"

	"grpc-over-http3/common"
)

func main() {
	logger := common.NewLogger("INFO")
	logger.Info("================================================")
	logger.Info("Testing HTTP/2 and HTTP/3 basic connectivity")
	logger.Info("================================================")

	// HTTP/2 テスト
	logger.Info("Testing HTTP/2 connectivity...")
	testHTTP2(logger)

	// HTTP/3 テスト（将来実装予定）
	logger.Info("HTTP/3 test - not implemented yet")
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
