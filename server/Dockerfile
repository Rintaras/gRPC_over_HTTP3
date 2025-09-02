FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo

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
    iputils-ping \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustup update stable && rustup default stable
ENV LIBCLANG_PATH=/usr/lib/llvm-12/lib

WORKDIR /tmp
RUN git clone --recursive https://github.com/cloudflare/quiche.git \
    && cd quiche \
    && cargo build --release --features ffi,pkg-config-meta \
    && mkdir -p /opt/quiche \
    && cp target/release/libquiche.a /opt/quiche/ \
    && cp quiche/include/quiche.h /opt/quiche/ \
    && cp target/release/quiche.pc /opt/quiche/

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

RUN mkdir -p /opt/nginx-h3/certs \
    && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /opt/nginx-h3/certs/server.key \
    -out /opt/nginx-h3/certs/server.crt \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=Test/CN=server"

RUN openssl rand 80 > /opt/nginx-h3/certs/ticket.key
RUN mkdir -p /opt/nginx-h3/conf /opt/nginx-h3/proto /var/log/nginx

RUN git clone --depth 1 --branch v1.0.0 https://github.com/ngtcp2/nghttp3.git \
    && cd nghttp3 \
    && autoreconf -i \
    && ./configure --enable-http3 --enable-app \
    && make -j$(nproc) \
    && make install \
    && ldconfig

# If the build context is the repository root (.), use paths with the 'server/' prefix
COPY server/nginx.conf /opt/nginx-h3/conf/nginx.conf
COPY server/proto /opt/nginx-h3/proto/
COPY scripts/sync_time.sh /usr/local/bin/sync_time.sh
RUN chmod +x /usr/local/bin/sync_time.sh

WORKDIR /opt/nginx-h3
EXPOSE 80 443
CMD ["/opt/nginx-h3/sbin/nginx", "-g", "daemon off;"] 