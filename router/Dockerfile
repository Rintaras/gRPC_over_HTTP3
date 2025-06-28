FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Create scripts directory and copy scripts
RUN mkdir -p /scripts
COPY scripts /scripts/
RUN chmod +x /scripts/*.sh

WORKDIR /scripts 