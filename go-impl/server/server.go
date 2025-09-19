package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"golang.org/x/net/http2"
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"

	"grpc-over-http3/common"
	pb "grpc-over-http3/proto"
)

func main() {
	// 設定読み込み
	config := common.LoadConfig()
	logger := common.NewLogger(config.LogLevel)

	logger.Info("Starting gRPC over HTTP/2 and HTTP/3 server")

	// 証明書ディレクトリ作成
	certDir := filepath.Dir(config.CertPath)
	if err := os.MkdirAll(certDir, 0755); err != nil {
		log.Fatalf("Failed to create cert directory: %v", err)
	}

	// 証明書管理
	certManager := &CertManager{
		CertPath: config.CertPath,
		KeyPath:  config.KeyPath,
	}

	// 証明書生成（存在しない場合）
	if _, err := os.Stat(config.CertPath); os.IsNotExist(err) {
		logger.Info("Generating self-signed certificate")
		if err := certManager.GenerateSelfSignedCert(); err != nil {
			log.Fatalf("Failed to generate certificate: %v", err)
		}
	}

	// TLS設定読み込み（現在は使用しない）
	// tlsConfig, err := certManager.LoadTLSConfig()
	// if err != nil {
	// 	log.Printf("Warning: Failed to load TLS config: %v", err)
	// }

	// ヘルスチェック起動
	healthChecker := &HealthChecker{}
	healthChecker.StartHealthCheck()

	// gRPCサーバー作成（プレーンテキスト）
	grpcServer := grpc.NewServer()
	pb.RegisterEchoServiceServer(grpcServer, &EchoServer{})
	reflection.Register(grpcServer)

	// HTTP/2 サーバー（TLS無効）
	http2Server := &http.Server{
		Addr:    fmt.Sprintf(":%d", config.ServerPort),
		Handler: grpcServer,
	}

	// HTTP/2設定
	if err := http2.ConfigureServer(http2Server, &http2.Server{}); err != nil {
		log.Fatalf("Failed to configure HTTP/2 server: %v", err)
	}

	// HTTP/3 サーバー（一旦無効化 - TLS必須のため）
	// http3Server := &http3.Server{
	// 	Addr:      fmt.Sprintf(":%d", config.HTTP3Port),
	// 	Handler:   grpcServer,
	// 	TLSConfig: tlsConfig,
	// }

	// サーバー起動
	go func() {
		logger.Info("Starting HTTP/2 server", "port", config.ServerPort)
		if err := http2Server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("HTTP/2 server failed: %v", err)
		}
	}()

	// HTTP/3 サーバー起動（一旦無効化）
	// go func() {
	// 	logger.Info("Starting HTTP/3 server", "port", config.HTTP3Port)
	// 	if err := http3Server.ListenAndServe(); err != nil {
	// 		log.Fatalf("HTTP/3 server failed: %v", err)
	// 	}
	// }()

	// 準備完了
	healthChecker.SetReady(true)
	logger.Info("Server is ready")

	// グレースフルシャットダウン
	shutdown := &GracefulShutdown{
		Server:      http2Server,
		HTTP3Server: nil, // HTTP/3は無効化
		Timeout:     30 * time.Second,
	}
	shutdown.WaitForShutdown()
}
