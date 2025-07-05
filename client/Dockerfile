FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    build-essential \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    wrk \
    python3 \
    python3-pip \
    python3-numpy \
    python3-pandas \
    docker.io \
    autoconf \
    automake \
    libtool \
    pkg-config \
    bc \
    cmake \
    libssl-dev \
    zlib1g-dev \
    libc-ares-dev \
    libev-dev \
    libevent-dev \
    libjansson-dev \
    libxml2-dev \
    libpsl-dev \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Build and install nghttp3
WORKDIR /tmp
RUN git clone --recursive https://github.com/ngtcp2/nghttp3.git && \
    cd nghttp3 && \
    autoreconf -i && \
    ./configure && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    rm -rf nghttp3

# Build and install quictls (OpenSSL QUIC fork)
WORKDIR /tmp
RUN git clone --depth 1 --branch OpenSSL_1_1_1t+quic https://github.com/quictls/openssl.git && \
    cd openssl && \
    ./config --prefix=/usr/local --openssldir=/usr/local no-shared enable-tls1_3 enable-quic && \
    make -j$(nproc) && \
    make install_sw && \
    cd .. && \
    rm -rf openssl

# Build and install ngtcp2
RUN git clone --recursive https://github.com/ngtcp2/ngtcp2.git && \
    cd ngtcp2 && \
    autoreconf -i && \
    ./configure --with-openssl --with-openssl-prefix=/usr/local && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    rm -rf ngtcp2

# Build and install nghttp2 (includes h2load with HTTP/3 support)
RUN git clone --recursive https://github.com/nghttp2/nghttp2.git && \
    cd nghttp2 && \
    autoreconf -i && \
    ./configure --enable-app --enable-hpack-tools --enable-http3 --with-libngtcp2 --with-libnghttp3 && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    rm -rf nghttp2

# Install grpcurl
RUN wget -O /usr/local/bin/grpcurl https://github.com/fullstorydev/grpcurl/releases/download/v1.8.7/grpcurl_1.8.7_linux_x86_64.tar.gz && \
    tar -xzf /usr/local/bin/grpcurl -C /usr/local/bin/ --strip-components=1 grpcurl && \
    chmod +x /usr/local/bin/grpcurl && \
    rm /usr/local/bin/grpcurl

# Build curl with HTTP/3 support
RUN git clone --recursive https://github.com/curl/curl.git && \
    cd curl && \
    autoreconf -fi && \
    ./configure --with-openssl --with-ngtcp2 --with-nghttp3 && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    rm -rf curl

# Add /usr/local/bin to PATH
ENV PATH="/usr/local/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/lib:${LD_LIBRARY_PATH}"

# Set timezone to JST
ENV TZ=Asia/Tokyo

# Copy scripts
COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

WORKDIR /scripts

# Copy sync_time.sh
COPY ../scripts/sync_time.sh /usr/local/bin/sync_time.sh
RUN chmod +x /usr/local/bin/sync_time.sh

# Keep container running
CMD ["sleep", "infinity"] 