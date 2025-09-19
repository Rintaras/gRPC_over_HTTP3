package main

import (
	"context"
	"fmt"
	"sync"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"grpc-over-http3/common"
	pb "grpc-over-http3/proto"
)

type BenchmarkConfig struct {
	Requests      int
	Connections   int
	Threads       int
	MaxConcurrent int
	Protocol      string // "HTTP/2" or "HTTP/3"
	ServerAddr    string
	TestCases     []TestCase
}

type TestCase struct {
	Delay int // ms
	Loss  int // percentage
}

type BenchmarkResult struct {
	TotalRequests  int
	SuccessfulReqs int
	FailedReqs     int
	TotalTime      time.Duration
	AvgLatency     time.Duration
	MinLatency     time.Duration
	MaxLatency     time.Duration
	P95Latency     time.Duration
	P99Latency     time.Duration
	Throughput     float64 // requests/second
	ErrorRate      float64
	Protocol       string
	TestCase       TestCase
}

func runHTTP2Benchmark(config BenchmarkConfig) BenchmarkResult {
	logger := common.NewLogger("INFO")
	logger.Info("Starting HTTP/2 benchmark", "requests", config.Requests, "connections", config.Connections)

	start := time.Now()
	var wg sync.WaitGroup
	results := make(chan RequestResult, config.Requests)

	requestsPerConnection := config.Requests / config.Connections
	remainingRequests := config.Requests % config.Connections

	for i := 0; i < config.Connections; i++ {
		wg.Add(1)
		go func(connID int) {
			defer wg.Done()

			// gRPC接続
			conn, err := grpc.Dial(fmt.Sprintf("%s:%d", config.ServerAddr, 443), grpc.WithInsecure())
			if err != nil {
				logger.Error("Failed to connect", "connection", connID, "error", err)
				for j := 0; j < requestsPerConnection; j++ {
					results <- RequestResult{Success: false, Latency: 0, Error: err}
				}
				return
			}
			defer conn.Close()

			client := pb.NewEchoServiceClient(conn)

			requests := requestsPerConnection
			if connID < remainingRequests {
				requests++
			}

			for j := 0; j < requests; j++ {
				reqStart := time.Now()
				_, err := client.Echo(context.Background(), &pb.EchoRequest{
					Message:   fmt.Sprintf("HTTP/2 request %d-%d", connID, j),
					Timestamp: time.Now().UnixNano(),
				})
				latency := time.Since(reqStart)

				results <- RequestResult{
					Success: err == nil,
					Latency: latency,
					Error:   err,
				}

				if err != nil {
					logger.Debug("Request failed", "connection", connID, "request", j, "error", err)
				}
			}
		}(i)
	}

	wg.Wait()
	close(results)

	totalTime := time.Since(start)
	return analyzeResults(results, totalTime, "HTTP/2", TestCase{})
}

func runHTTP3Benchmark(config BenchmarkConfig) BenchmarkResult {
	logger := common.NewLogger("INFO")
	logger.Info("Starting HTTP/3 benchmark", "requests", config.Requests, "connections", config.Connections)

	start := time.Now()
	var wg sync.WaitGroup
	results := make(chan RequestResult, config.Requests)

	requestsPerConnection := config.Requests / config.Connections
	remainingRequests := config.Requests % config.Connections

	for i := 0; i < config.Connections; i++ {
		wg.Add(1)
		go func(connID int) {
			defer wg.Done()

			// gRPC接続（HTTP/3ポート）
			conn, err := grpc.Dial(fmt.Sprintf("%s:%d", config.ServerAddr, 4433), grpc.WithInsecure())
			if err != nil {
				logger.Error("Failed to connect", "connection", connID, "error", err)
				for j := 0; j < requestsPerConnection; j++ {
					results <- RequestResult{Success: false, Latency: 0, Error: err}
				}
				return
			}
			defer conn.Close()

			client := pb.NewEchoServiceClient(conn)

			requests := requestsPerConnection
			if connID < remainingRequests {
				requests++
			}

			for j := 0; j < requests; j++ {
				reqStart := time.Now()
				_, err := client.Echo(context.Background(), &pb.EchoRequest{
					Message:   fmt.Sprintf("HTTP/3 request %d-%d", connID, j),
					Timestamp: time.Now().UnixNano(),
				})
				latency := time.Since(reqStart)

				results <- RequestResult{
					Success: err == nil,
					Latency: latency,
					Error:   err,
				}

				if err != nil {
					logger.Debug("Request failed", "connection", connID, "request", j, "error", err)
				}
			}
		}(i)
	}

	wg.Wait()
	close(results)

	totalTime := time.Since(start)
	return analyzeResults(results, totalTime, "HTTP/3", TestCase{})
}

type RequestResult struct {
	Success bool
	Latency time.Duration
	Error   error
}

func analyzeResults(results <-chan RequestResult, totalTime time.Duration, protocol string, testCase TestCase) BenchmarkResult {
	var latencies []time.Duration
	var successfulReqs, failedReqs int

	for result := range results {
		if result.Success {
			successfulReqs++
			latencies = append(latencies, result.Latency)
		} else {
			failedReqs++
		}
	}

	totalRequests := successfulReqs + failedReqs
	if totalRequests == 0 {
		return BenchmarkResult{Protocol: protocol, TestCase: testCase}
	}

	// 統計計算
	var totalLatency time.Duration
	var minLatency, maxLatency time.Duration = time.Hour, 0

	for _, latency := range latencies {
		totalLatency += latency
		if latency < minLatency {
			minLatency = latency
		}
		if latency > maxLatency {
			maxLatency = latency
		}
	}

	avgLatency := time.Duration(0)
	if len(latencies) > 0 {
		avgLatency = totalLatency / time.Duration(len(latencies))
	}

	// パーセンタイル計算
	p95Latency, p99Latency := calculatePercentiles(latencies)

	throughput := float64(successfulReqs) / totalTime.Seconds()
	errorRate := float64(failedReqs) / float64(totalRequests)

	return BenchmarkResult{
		TotalRequests:  totalRequests,
		SuccessfulReqs: successfulReqs,
		FailedReqs:     failedReqs,
		TotalTime:      totalTime,
		AvgLatency:     avgLatency,
		MinLatency:     minLatency,
		MaxLatency:     maxLatency,
		P95Latency:     p95Latency,
		P99Latency:     p99Latency,
		Throughput:     throughput,
		ErrorRate:      errorRate,
		Protocol:       protocol,
		TestCase:       testCase,
	}
}

func calculatePercentiles(latencies []time.Duration) (time.Duration, time.Duration) {
	if len(latencies) == 0 {
		return 0, 0
	}

	// ソート
	for i := 0; i < len(latencies); i++ {
		for j := i + 1; j < len(latencies); j++ {
			if latencies[i] > latencies[j] {
				latencies[i], latencies[j] = latencies[j], latencies[i]
			}
		}
	}

	p95Index := int(float64(len(latencies)) * 0.95)
	p99Index := int(float64(len(latencies)) * 0.99)

	if p95Index >= len(latencies) {
		p95Index = len(latencies) - 1
	}
	if p99Index >= len(latencies) {
		p99Index = len(latencies) - 1
	}

	return latencies[p95Index], latencies[p99Index]
}

func isRetryableError(err error) bool {
	if err == nil {
		return false
	}

	st, ok := status.FromError(err)
	if !ok {
		return false
	}

	switch st.Code() {
	case codes.Unavailable, codes.DeadlineExceeded, codes.ResourceExhausted:
		return true
	default:
		return false
	}
}
