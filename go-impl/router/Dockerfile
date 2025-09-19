# Multi-stage build for Go router
FROM golang:1.21-bullseye as builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build router
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o router ./router/

# Final stage
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    ca-certificates \
    iproute2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy binary
COPY --from=builder /app/router .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["./router"]
