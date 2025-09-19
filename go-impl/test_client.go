package main

import (
	"context"
	"fmt"
	"log"
	"time"

	pb "grpc-over-http3/proto"

	"google.golang.org/grpc"
)

func main() {
	fmt.Println("Testing gRPC connection...")

	// HTTP/2 テスト
	fmt.Println("Testing HTTP/2 connection...")
	conn2, err := grpc.Dial("172.31.0.2:443", grpc.WithInsecure())
	if err != nil {
		log.Fatalf("Failed to connect to HTTP/2 server: %v", err)
	}
	defer conn2.Close()

	client2 := pb.NewEchoServiceClient(conn2)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	resp2, err := client2.Echo(ctx, &pb.EchoRequest{
		Message:   "Test HTTP/2",
		Timestamp: time.Now().UnixNano(),
	})
	if err != nil {
		log.Printf("HTTP/2 request failed: %v", err)
	} else {
		fmt.Printf("HTTP/2 response: %s\n", resp2.Message)
	}

	// HTTP/3 テスト
	fmt.Println("Testing HTTP/3 connection...")
	conn3, err := grpc.Dial("172.31.0.2:4433", grpc.WithInsecure())
	if err != nil {
		log.Fatalf("Failed to connect to HTTP/3 server: %v", err)
	}
	defer conn3.Close()

	client3 := pb.NewEchoServiceClient(conn3)

	resp3, err := client3.Echo(ctx, &pb.EchoRequest{
		Message:   "Test HTTP/3",
		Timestamp: time.Now().UnixNano(),
	})
	if err != nil {
		log.Printf("HTTP/3 request failed: %v", err)
	} else {
		fmt.Printf("HTTP/3 response: %s\n", resp3.Message)
	}

	fmt.Println("Test completed!")
}
