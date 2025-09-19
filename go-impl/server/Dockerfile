# Multi-stage build for Go gRPC server
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

# Build server
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o server ./server/

# Final stage
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create certificates directory
RUN mkdir -p /app/certs

# Copy binary
COPY --from=builder /app/server .

# Expose ports
EXPOSE 443 4433 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["./server"]
