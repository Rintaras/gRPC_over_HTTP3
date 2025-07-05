FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcre3-dev \
    libssl-dev \
    zlib1g-dev \
    git \
    cmake \
    pkg-config \
    wget \
    curl \
    clang \
    libclang-12-dev \
    llvm-12-dev \
    autoconf \
    automake \
    libtool \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install Rust with latest version
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Update Rust to latest version
RUN rustup update stable && rustup default stable

# Set libclang path
ENV LIBCLANG_PATH=/usr/lib/llvm-12/lib

# Build quiche
WORKDIR /tmp
RUN git clone --recursive https://github.com/cloudflare/quiche.git \
    && cd quiche \
    && cargo build --release --features ffi,pkg-config-meta \
    && mkdir -p /opt/quiche \
    && cp target/release/libquiche.a /opt/quiche/ \
    && cp quiche/include/quiche.h /opt/quiche/ \
    && cp target/release/quiche.pc /opt/quiche/

# Download and build nginx with HTTP/3 (quiche) support
RUN wget https://nginx.org/download/nginx-1.25.3.tar.gz \
    && tar -xzf nginx-1.25.3.tar.gz \
    && cd nginx-1.25.3 \
    && ./configure \
        --prefix=/opt/nginx-h3 \
        --with-http_ssl_module \
        --with-http_v2_module \
        --with-http_v3_module \
        --with-cc-opt="-I/tmp/quiche/include" \
        --with-ld-opt="-L/tmp/quiche/target/release -lquiche" \
    && make -j$(nproc) \
    && make install \
    && cd .. \
    && rm -rf nginx-1.25.3*

# Create self-signed certificate
RUN mkdir -p /opt/nginx-h3/certs \
    && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /opt/nginx-h3/certs/server.key \
        -out /opt/nginx-h3/certs/server.crt \
        -subj "/C=JP/ST=Tokyo/L=Tokyo/O=Test/CN=server"

# Create nginx configuration directory and log directories
RUN mkdir -p /opt/nginx-h3/conf /opt/nginx-h3/proto /var/log/nginx

# Build HTTP/3 capable h2load/h3load (without sfparse for now)
RUN git clone --depth 1 --branch v1.0.0 https://github.com/ngtcp2/nghttp3.git \
    && cd nghttp3 \
    && autoreconf -i \
    && ./configure --enable-http3 --enable-app \
    && make -j$(nproc) \
    && make install \
    && ldconfig

# Copy configuration files
COPY server/nginx.conf /opt/nginx-h3/conf/nginx.conf
COPY server/proto /opt/nginx-h3/proto/

# Set working directory
WORKDIR /opt/nginx-h3

# Expose ports 80 and 443
EXPOSE 80 443

# Start nginx in foreground
CMD ["/opt/nginx-h3/sbin/nginx", "-g", "daemon off;"]

COPY ../scripts/sync_time.sh /usr/local/bin/sync_time.sh
RUN chmod +x /usr/local/bin/sync_time.sh 