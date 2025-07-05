FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo

RUN apt-get update && apt-get install -y \
    iproute2 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Create scripts directory and copy scripts
RUN mkdir -p /scripts
COPY scripts /scripts/
RUN chmod +x /scripts/*.sh

COPY ../scripts/sync_time.sh /usr/local/bin/sync_time.sh
RUN chmod +x /usr/local/bin/sync_time.sh

WORKDIR /scripts 