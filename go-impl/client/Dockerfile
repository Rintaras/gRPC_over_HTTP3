# Multi-stage build for Go gRPC client
FROM golang:1.21-bullseye as builder

WORKDIR /app

# Install protobuf compiler
RUN apt-get update && apt-get install -y \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# Copy go mod files
COPY go.mod ./
RUN go mod download

# Copy source code
COPY . .

# Install protoc-gen-go and protoc-gen-go-grpc
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.31.0
RUN go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.3.0

# Generate protobuf files
RUN protoc --go_out=. --go_opt=paths=source_relative \
    --go-grpc_out=. --go-grpc_opt=paths=source_relative \
    proto/echo.proto

# Update go.mod and generate go.sum
RUN go mod tidy

# Build client
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o client ./client/
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o test_http_client ./test_http_client.go

# Final stage
FROM ubuntu:18.04

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create logs directory
RUN mkdir -p /app/logs

# Copy binary
COPY --from=builder /app/client .
COPY --from=builder /app/test_http_client .

# Keep container running
CMD ["sleep", "infinity"]
