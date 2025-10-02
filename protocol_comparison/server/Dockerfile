FROM golang:1.21 AS builder

WORKDIR /app

COPY server/go.mod ./
RUN go mod download

COPY server/main.go ./

RUN go mod tidy && CGO_ENABLED=0 GOOS=linux go build -a -o main .

FROM ubuntu:22.04

RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /root/

COPY --from=builder /app/main .
COPY certs/localhost+2.pem .
COPY certs/localhost+2-key.pem .

EXPOSE 8443

CMD ["./main"]
