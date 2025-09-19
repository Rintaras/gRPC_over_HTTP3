package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"grpc-over-http3/common"
)

type RouterServer struct {
	emulation *NetworkEmulation
	logger    *common.Logger
}

type NetworkConfigRequest struct {
	Delay int `json:"delay"`
	Loss  int `json:"loss"`
}

type NetworkStatusResponse struct {
	Delay int `json:"delay"`
	Loss  int `json:"loss"`
}

func (rs *RouterServer) handleSetNetworkConfig(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var config NetworkConfigRequest
	if err := json.NewDecoder(r.Body).Decode(&config); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	rs.logger.Info("Setting network configuration", "delay", config.Delay, "loss", config.Loss)

	if err := rs.emulation.SetConditions(config.Delay, config.Loss); err != nil {
		rs.logger.Error("Failed to set network conditions", "error", err)
		http.Error(w, fmt.Sprintf("Failed to set network conditions: %v", err), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "success"})
}

func (rs *RouterServer) handleGetNetworkStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	delay, loss, err := rs.emulation.GetStatus()
	if err != nil {
		rs.logger.Error("Failed to get network status", "error", err)
		http.Error(w, fmt.Sprintf("Failed to get network status: %v", err), http.StatusInternalServerError)
		return
	}

	status := NetworkStatusResponse{
		Delay: delay,
		Loss:  loss,
	}

	json.NewEncoder(w).Encode(status)
}

func (rs *RouterServer) handleHealthCheck(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("OK"))
}

func (rs *RouterServer) handleClearNetworkConfig(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	rs.logger.Info("Clearing network configuration")

	if err := rs.emulation.Clear(); err != nil {
		rs.logger.Error("Failed to clear network conditions", "error", err)
		http.Error(w, fmt.Sprintf("Failed to clear network conditions: %v", err), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "cleared"})
}

func main() {
	logger := common.NewLogger("INFO")
	logger.Info("Starting gRPC network emulation router")

	// ネットワークエミュレーション初期化
	emulation := &NetworkEmulation{
		Delay: 0,
		Loss:  0,
	}

	// 初期状態をクリア
	if err := emulation.Clear(); err != nil {
		logger.Error("Failed to clear initial network state", "error", err)
	}

	// ルーターサーバー初期化
	router := &RouterServer{
		emulation: emulation,
		logger:    logger,
	}

	// HTTP サーバー設定
	mux := http.NewServeMux()
	mux.HandleFunc("/network/config", router.handleSetNetworkConfig)
	mux.HandleFunc("/network/status", router.handleGetNetworkStatus)
	mux.HandleFunc("/network/clear", router.handleClearNetworkConfig)
	mux.HandleFunc("/health", router.handleHealthCheck)

	server := &http.Server{
		Addr:    ":8080",
		Handler: mux,
	}

	// サーバー起動
	go func() {
		logger.Info("Starting router server", "port", "8080")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Router server failed: %v", err)
		}
	}()

	// グレースフルシャットダウン
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	<-quit
	logger.Info("Router server is shutting down...")

	// ネットワーク設定をクリア
	if err := emulation.Clear(); err != nil {
		logger.Error("Failed to clear network settings on shutdown", "error", err)
	}

	// サーバー停止
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		logger.Error("Router server shutdown error", "error", err)
	}

	logger.Info("Router server stopped")
}
