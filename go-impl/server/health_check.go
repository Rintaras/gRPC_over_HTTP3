package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/quic-go/quic-go/http3"
)

type GracefulShutdown struct {
	Server      *http.Server
	HTTP3Server *http3.Server
	Timeout     time.Duration
}

func (gs *GracefulShutdown) WaitForShutdown() {
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	<-quit
	log.Println("Server is shutting down...")

	ctx, cancel := context.WithTimeout(context.Background(), gs.Timeout)
	defer cancel()

	// HTTP/2 サーバー停止
	if gs.Server != nil {
		if err := gs.Server.Shutdown(ctx); err != nil {
			log.Printf("HTTP/2 server shutdown error: %v", err)
		}
	}

	// HTTP/3 サーバー停止
	if gs.HTTP3Server != nil {
		if err := gs.HTTP3Server.Close(); err != nil {
			log.Printf("HTTP/3 server shutdown error: %v", err)
		}
	}

	log.Println("Server stopped")
}

type HealthChecker struct {
	server *http.Server
	ready  bool
}

func (hc *HealthChecker) StartHealthCheck() {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", hc.healthHandler)
	mux.HandleFunc("/ready", hc.readyHandler)

	hc.server = &http.Server{
		Addr:    ":8080",
		Handler: mux,
	}

	go func() {
		if err := hc.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Printf("Health check server error: %v", err)
		}
	}()
}

func (hc *HealthChecker) healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("OK"))
}

func (hc *HealthChecker) readyHandler(w http.ResponseWriter, r *http.Request) {
	if hc.ready {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("Ready"))
	} else {
		w.WriteHeader(http.StatusServiceUnavailable)
		w.Write([]byte("Not Ready"))
	}
}

func (hc *HealthChecker) SetReady(ready bool) {
	hc.ready = ready
}
