package main

import (
	"context"
	"time"

	pb "grpc-over-http3/proto"
)

type EchoServer struct {
	pb.UnimplementedEchoServiceServer
}

func (s *EchoServer) Echo(ctx context.Context, req *pb.EchoRequest) (*pb.EchoResponse, error) {
	return &pb.EchoResponse{
		Message:   req.Message,
		Timestamp: time.Now().UnixNano(),
		Protocol:  "HTTP/2",
	}, nil
}

func (s *EchoServer) StreamEcho(stream pb.EchoService_StreamEchoServer) error {
	for {
		req, err := stream.Recv()
		if err != nil {
			return err
		}

		response := &pb.EchoResponse{
			Message:   req.Message,
			Timestamp: time.Now().UnixNano(),
			Protocol:  "HTTP/2",
		}

		if err := stream.Send(response); err != nil {
			return err
		}
	}
}
