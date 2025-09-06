#!/bin/bash

# Network Connectivity Test Script for Raspberry Pi 5 Setup
# Tests connection between Docker client and Raspberry Pi 5 server

echo "================================================"
echo "Network Connectivity Test - Raspberry Pi 5 Setup"
echo "================================================"

# Configuration
RASPBERRY_PI_IP="192.168.2.100"
ROUTER_IP="172.30.0.254"
CLIENT_CONTAINER="grpc-client"
ROUTER_CONTAINER="grpc-router"

echo "Testing network connectivity..."
echo "Raspberry Pi 5 IP: $RASPBERRY_PI_IP"
echo "Router IP: $ROUTER_IP"
echo ""

# Function to test basic connectivity
test_basic_connectivity() {
    echo "=== Basic Connectivity Test ==="
    
    # Test ping to Raspberry Pi
    echo "Testing ping to Raspberry Pi 5..."
    if ping -c 3 $RASPBERRY_PI_IP > /dev/null 2>&1; then
        echo "✅ Ping to Raspberry Pi 5: SUCCESS"
    else
        echo "❌ Ping to Raspberry Pi 5: FAILED"
        return 1
    fi
    
    # Test ping from Docker client
    echo "Testing ping from Docker client..."
    if docker exec $CLIENT_CONTAINER ping -c 3 $RASPBERRY_PI_IP > /dev/null 2>&1; then
        echo "✅ Docker client ping to Raspberry Pi 5: SUCCESS"
    else
        echo "❌ Docker client ping to Raspberry Pi 5: FAILED"
        return 1
    fi
    
    echo ""
}

# Function to test port connectivity
test_port_connectivity() {
    echo "=== Port Connectivity Test ==="
    
    # Test port 443
    echo "Testing port 443 on Raspberry Pi 5..."
    if timeout 5 bash -c "</dev/tcp/$RASPBERRY_PI_IP/443" 2>/dev/null; then
        echo "✅ Port 443 on Raspberry Pi 5: OPEN"
    else
        echo "❌ Port 443 on Raspberry Pi 5: CLOSED or FILTERED"
        return 1
    fi
    
    # Test port 443 from Docker client
    echo "Testing port 443 from Docker client..."
    if docker exec $CLIENT_CONTAINER timeout 5 bash -c "</dev/tcp/$RASPBERRY_PI_IP/443" 2>/dev/null; then
        echo "✅ Docker client port 443 to Raspberry Pi 5: OPEN"
    else
        echo "❌ Docker client port 443 to Raspberry Pi 5: CLOSED or FILTERED"
        return 1
    fi
    
    echo ""
}

# Function to test SSL/TLS connectivity
test_ssl_connectivity() {
    echo "=== SSL/TLS Connectivity Test ==="
    
    # Test SSL connection
    echo "Testing SSL connection to Raspberry Pi 5..."
    if echo | openssl s_client -connect $RASPBERRY_PI_IP:443 -servername grpc-server-pi.local 2>/dev/null | grep -q "Verify return code: 0"; then
        echo "✅ SSL connection to Raspberry Pi 5: SUCCESS"
    else
        echo "⚠️  SSL connection to Raspberry Pi 5: WARNING (self-signed certificate)"
    fi
    
    # Test SSL connection from Docker client
    echo "Testing SSL connection from Docker client..."
    if docker exec $CLIENT_CONTAINER bash -c "echo | openssl s_client -connect $RASPBERRY_PI_IP:443 -servername grpc-server-pi.local 2>/dev/null | grep -q 'Verify return code: 0'"; then
        echo "✅ Docker client SSL connection to Raspberry Pi 5: SUCCESS"
    else
        echo "⚠️  Docker client SSL connection to Raspberry Pi 5: WARNING (self-signed certificate)"
    fi
    
    echo ""
}

# Function to test HTTP/2 connectivity
test_http2_connectivity() {
    echo "=== HTTP/2 Connectivity Test ==="
    
    # Test HTTP/2 connection
    echo "Testing HTTP/2 connection to Raspberry Pi 5..."
    if curl -k --http2 --connect-timeout 10 https://$RASPBERRY_PI_IP/health 2>/dev/null | grep -q "OK"; then
        echo "✅ HTTP/2 connection to Raspberry Pi 5: SUCCESS"
    else
        echo "❌ HTTP/2 connection to Raspberry Pi 5: FAILED"
        return 1
    fi
    
    # Test HTTP/2 connection from Docker client
    echo "Testing HTTP/2 connection from Docker client..."
    if docker exec $CLIENT_CONTAINER curl -k --http2 --connect-timeout 10 https://$RASPBERRY_PI_IP/health 2>/dev/null | grep -q "OK"; then
        echo "✅ Docker client HTTP/2 connection to Raspberry Pi 5: SUCCESS"
    else
        echo "❌ Docker client HTTP/2 connection to Raspberry Pi 5: FAILED"
        return 1
    fi
    
    echo ""
}

# Function to test HTTP/3 connectivity
test_http3_connectivity() {
    echo "=== HTTP/3 Connectivity Test ==="
    
    # Test HTTP/3 connection
    echo "Testing HTTP/3 connection to Raspberry Pi 5..."
    if curl -k --http3 --connect-timeout 10 https://$RASPBERRY_PI_IP/health 2>/dev/null | grep -q "OK"; then
        echo "✅ HTTP/3 connection to Raspberry Pi 5: SUCCESS"
    else
        echo "⚠️  HTTP/3 connection to Raspberry Pi 5: WARNING (may not be supported)"
    fi
    
    # Test HTTP/3 connection from Docker client
    echo "Testing HTTP/3 connection from Docker client..."
    if docker exec $CLIENT_CONTAINER curl -k --http3 --connect-timeout 10 https://$RASPBERRY_PI_IP/health 2>/dev/null | grep -q "OK"; then
        echo "✅ Docker client HTTP/3 connection to Raspberry Pi 5: SUCCESS"
    else
        echo "⚠️  Docker client HTTP/3 connection to Raspberry Pi 5: WARNING (may not be supported)"
    fi
    
    echo ""
}

# Function to test network emulation
test_network_emulation() {
    echo "=== Network Emulation Test ==="
    
    # Check if router container is running
    if ! docker ps | grep -q $ROUTER_CONTAINER; then
        echo "❌ Router container ($ROUTER_CONTAINER) is not running"
        return 1
    fi
    
    # Check tc configuration
    echo "Checking network emulation configuration..."
    docker exec $ROUTER_CONTAINER tc qdisc show dev eth0
    
    echo ""
}

# Function to show network configuration
show_network_config() {
    echo "=== Network Configuration ==="
    
    echo "Host network configuration:"
    ip route show | grep -E "(172\.30\.0|default)"
    
    echo ""
    echo "Docker network configuration:"
    docker network ls | grep grpc
    
    echo ""
    echo "Docker container IPs:"
    docker inspect $CLIENT_CONTAINER | grep -A 5 "NetworkSettings"
    docker inspect $ROUTER_CONTAINER | grep -A 5 "NetworkSettings"
    
    echo ""
}

# Function to show Raspberry Pi 5 status
show_raspberry_pi_status() {
    echo "=== Raspberry Pi 5 Status Check ==="
    
    echo "Checking if Raspberry Pi 5 is reachable..."
    if ping -c 1 $RASPBERRY_PI_IP > /dev/null 2>&1; then
        echo "✅ Raspberry Pi 5 is reachable"
        
        # Try to get basic system info via SSH (if SSH is available)
        echo "Attempting to get system information..."
        if command -v ssh > /dev/null 2>&1; then
            echo "SSH is available. You can manually check Raspberry Pi 5 status:"
            echo "  ssh pi@$RASPBERRY_PI_IP 'sudo systemctl status nginx'"
            echo "  ssh pi@$RASPBERRY_PI_IP 'sudo ss -tuln | grep :443'"
            echo "  ssh pi@$RASPBERRY_PI_IP 'ip addr show wlan0'  # Check wireless interface"
        else
            echo "SSH not available. Please check Raspberry Pi 5 manually:"
            echo "  - nginx status: sudo systemctl status nginx"
            echo "  - port 443: sudo ss -tuln | grep :443"
            echo "  - logs: sudo tail -f /var/log/nginx/access.log"
            echo "  - wireless: ip addr show wlan0"
        fi
    else
        echo "❌ Raspberry Pi 5 is not reachable"
        echo "Please check:"
        echo "  - Raspberry Pi 5 is powered on"
        echo "  - Wireless connection is active"
        echo "  - IP address is correct: $RASPBERRY_PI_IP"
        echo "  - Raspberry Pi 5 is on the same network"
        echo "  - Wireless signal strength is adequate"
    fi
    
    echo ""
}

# Main execution
main() {
    echo "Starting network connectivity tests..."
    echo ""
    
    # Check if Docker containers are running
    if ! docker ps | grep -q $CLIENT_CONTAINER; then
        echo "❌ Client container ($CLIENT_CONTAINER) is not running"
        echo "Please start the Docker environment first:"
        echo "  docker-compose up -d"
        exit 1
    fi
    
    if ! docker ps | grep -q $ROUTER_CONTAINER; then
        echo "❌ Router container ($ROUTER_CONTAINER) is not running"
        echo "Please start the Docker environment first:"
        echo "  docker-compose up -d"
        exit 1
    fi
    
    # Run tests
    show_network_config
    show_raspberry_pi_status
    test_basic_connectivity
    test_port_connectivity
    test_ssl_connectivity
    test_http2_connectivity
    test_http3_connectivity
    test_network_emulation
    
    echo "================================================"
    echo "Network connectivity tests completed!"
    echo "================================================"
    echo ""
    echo "If all tests pass, you can run the benchmark:"
    echo "  ./scripts/run_bench_raspberry_pi.sh"
    echo ""
    echo "If tests fail, please check:"
    echo "  1. Raspberry Pi 5 is running and accessible"
    echo "  2. Docker containers are running"
    echo "  3. Network configuration is correct"
    echo "  4. Firewall settings allow connections"
}

# Run main function
main "$@"
