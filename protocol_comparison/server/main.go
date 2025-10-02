package main

import (
	"crypto/tls"
	"fmt"
	"log"
	"net/http"

	"github.com/quic-go/quic-go/http3"
	"golang.org/x/net/http2"
)

func main() {
	fmt.Println("Running...")

	// TLS設定
	cert, err := tls.LoadX509KeyPair("localhost+2.pem", "localhost+2-key.pem")
	if err != nil {
		log.Fatal(err)
	}

	// HTTP/1.1とHTTP/2サーバー
	httpServer := &http.Server{
		Addr: ":8443",
		TLSConfig: &tls.Config{
			Certificates: []tls.Certificate{cert},
			NextProtos:   []string{"h2", "http/1.1"},
		},
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			fmt.Printf("Received HTTP/1.1/2 request: %s %s\n", r.Method, r.URL.Path)
			w.Header().Add("Alt-Svc", `h3=":8443"; ma=86400, h3-29=":8443"; ma=86400`)

			if r.URL.Path == "/large" {
				w.Header().Set("Content-Type", "application/octet-stream")
				data := make([]byte, 10*1024*1024)
				w.Write(data)
			} else if r.URL.Path == "/1mb" {
				w.Header().Set("Content-Type", "application/octet-stream")
				data := make([]byte, 1*1024*1024)
				w.Write(data)
			} else {
				w.Write([]byte("hello, world from HTTP/1.1/2\n"))
			}
		}),
	}

	// HTTP/2を有効化
	http2.ConfigureServer(httpServer, &http2.Server{})

	// HTTP/3サーバー
	http3Server := &http3.Server{
		Addr: ":8443",
		TLSConfig: &tls.Config{
			Certificates: []tls.Certificate{cert},
			NextProtos:   []string{"h3", "h3-29", "h3-28", "h3-27"},
		},
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			fmt.Printf("Received HTTP/3 request: %s %s (Protocol: %s)\n", r.Method, r.URL.Path, r.Proto)

			if r.URL.Path == "/large" {
				w.Header().Set("Content-Type", "application/octet-stream")
				data := make([]byte, 10*1024*1024)
				w.Write(data)
			} else if r.URL.Path == "/1mb" {
				w.Header().Set("Content-Type", "application/octet-stream")
				data := make([]byte, 1*1024*1024)
				w.Write(data)
			} else {
				w.Write([]byte("hello, world from HTTP/3\n"))
			}
		}),
	}

	fmt.Println("Starting HTTP/1.1, HTTP/2, and HTTP/3 server on :8443")

	// HTTP/3を別のゴルーチンで起動
	go func() {
		log.Fatal(http3Server.ListenAndServe())
	}()

	// HTTP/1.1とHTTP/2を起動
	log.Fatal(httpServer.ListenAndServeTLS("", ""))
}
