package common

import (
	"log/slog"
	"os"
	"time"
)

type Logger struct {
	*slog.Logger
}

func NewLogger(level string) *Logger {
	var logLevel slog.Level
	switch level {
	case "DEBUG":
		logLevel = slog.LevelDebug
	case "INFO":
		logLevel = slog.LevelInfo
	case "WARN":
		logLevel = slog.LevelWarn
	case "ERROR":
		logLevel = slog.LevelError
	default:
		logLevel = slog.LevelInfo
	}

	opts := &slog.HandlerOptions{
		Level:     logLevel,
		AddSource: true,
	}

	handler := slog.NewJSONHandler(os.Stdout, opts)
	logger := slog.New(handler)

	return &Logger{logger}
}

type BenchmarkResult struct {
	Protocol       string
	TotalRequests  int
	SuccessfulReqs int
	FailedReqs     int
	TotalTime      time.Duration
	AvgLatency     time.Duration
	Throughput     float64
	ErrorRate      float64
}

// ベンチマーク専用ログ
func (l *Logger) LogBenchmarkResult(result BenchmarkResult) {
	l.Info("Benchmark completed",
		"protocol", result.Protocol,
		"total_requests", result.TotalRequests,
		"successful_requests", result.SuccessfulReqs,
		"failed_requests", result.FailedReqs,
		"total_time_ms", result.TotalTime.Milliseconds(),
		"avg_latency_ms", result.AvgLatency.Milliseconds(),
		"throughput_rps", result.Throughput,
		"error_rate", result.ErrorRate,
	)
}
