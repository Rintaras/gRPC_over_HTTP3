package common

import (
	"os"
	"strconv"
)

type Config struct {
	ServerPort     int
	HTTP3Port      int
	CertPath       string
	KeyPath        string
	LogLevel       string
	MaxConnections int
	BatchSize      int
	NetworkDelay   int
	NetworkLoss    int
}

func LoadConfig() *Config {
	config := &Config{
		ServerPort:     443,
		HTTP3Port:      4433,
		CertPath:       "/certs/server.crt",
		KeyPath:        "/certs/server.key",
		LogLevel:       "INFO",
		MaxConnections: 1000,
		BatchSize:      100,
		NetworkDelay:   0,
		NetworkLoss:    0,
	}

	if port := os.Getenv("SERVER_PORT"); port != "" {
		if p, err := strconv.Atoi(port); err == nil {
			config.ServerPort = p
		}
	}

	if port := os.Getenv("HTTP3_PORT"); port != "" {
		if p, err := strconv.Atoi(port); err == nil {
			config.HTTP3Port = p
		}
	}

	if level := os.Getenv("LOG_LEVEL"); level != "" {
		config.LogLevel = level
	}

	if delay := os.Getenv("NETWORK_DELAY"); delay != "" {
		if d, err := strconv.Atoi(delay); err == nil {
			config.NetworkDelay = d
		}
	}

	if loss := os.Getenv("NETWORK_LOSS"); loss != "" {
		if l, err := strconv.Atoi(loss); err == nil {
			config.NetworkLoss = l
		}
	}

	return config
}
