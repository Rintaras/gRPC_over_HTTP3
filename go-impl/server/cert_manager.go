package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"math/big"
	"net"
	"os"
	"time"
)

type CertManager struct {
	CertPath string
	KeyPath  string
}

func (cm *CertManager) GenerateSelfSignedCert() error {
	// 秘密鍵生成
	privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return fmt.Errorf("failed to generate private key: %v", err)
	}

	// 証明書テンプレート作成
	template := x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject: pkix.Name{
			Country:      []string{"JP"},
			Organization: []string{"GRPC-Benchmark"},
			CommonName:   "grpc-server.local",
		},
		NotBefore:   time.Now(),
		NotAfter:    time.Now().Add(365 * 24 * time.Hour),
		KeyUsage:    x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature,
		ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
		IPAddresses: []net.IP{net.ParseIP("172.30.0.2"), net.ParseIP("127.0.0.1")},
		DNSNames:    []string{"localhost", "grpc-server.local"},
	}

	// 証明書作成
	certDER, err := x509.CreateCertificate(rand.Reader, &template, &template, &privateKey.PublicKey, privateKey)
	if err != nil {
		return fmt.Errorf("failed to create certificate: %v", err)
	}

	// 証明書ファイル保存
	certOut, err := os.Create(cm.CertPath)
	if err != nil {
		return fmt.Errorf("failed to open cert file for writing: %v", err)
	}
	defer certOut.Close()

	if err := pem.Encode(certOut, &pem.Block{Type: "CERTIFICATE", Bytes: certDER}); err != nil {
		return fmt.Errorf("failed to write cert data: %v", err)
	}

	// 秘密鍵ファイル保存
	keyOut, err := os.Create(cm.KeyPath)
	if err != nil {
		return fmt.Errorf("failed to open key file for writing: %v", err)
	}
	defer keyOut.Close()

	privBytes, err := x509.MarshalPKCS8PrivateKey(privateKey)
	if err != nil {
		return fmt.Errorf("failed to marshal private key: %v", err)
	}

	if err := pem.Encode(keyOut, &pem.Block{Type: "PRIVATE KEY", Bytes: privBytes}); err != nil {
		return fmt.Errorf("failed to write key data: %v", err)
	}

	return nil
}

func (cm *CertManager) LoadTLSConfig() (*tls.Config, error) {
	cert, err := tls.LoadX509KeyPair(cm.CertPath, cm.KeyPath)
	if err != nil {
		return nil, fmt.Errorf("failed to load key pair: %v", err)
	}

	return &tls.Config{
		Certificates: []tls.Certificate{cert},
		NextProtos:   []string{"h2", "h3", "h3-29", "h3-28", "h3-27"},
		MinVersion:   tls.VersionTLS12,
		CipherSuites: []uint16{
			tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
			tls.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
			tls.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305,
		},
	}, nil
}
