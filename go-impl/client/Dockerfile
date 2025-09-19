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

# Generate protobuf files
RUN protoc --go_out=. --go_opt=paths=source_relative \
    --go-grpc_out=. --go-grpc_opt=paths=source_relative \
    proto/echo.proto

# Build client
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o client ./client/

# Final stage
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create logs directory
RUN mkdir -p /app/logs

# Copy binary
COPY --from=builder /app/client .

# Keep container running
CMD ["sleep", "infinity"]
