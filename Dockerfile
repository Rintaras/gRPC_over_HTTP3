# Multi-stage build for gRPC over HTTP3 research project
FROM ubuntu:22.04 as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Build stage for server
FROM base as server
WORKDIR /app/server
COPY server/ .
RUN echo "Server build completed"

# Build stage for client
FROM base as client
WORKDIR /app/client
COPY client/ .
RUN echo "Client build completed"

# Build stage for router
FROM base as router
WORKDIR /app/router
COPY router/ .
RUN echo "Router build completed"

# Final stage
FROM base as final
WORKDIR /app
COPY --from=server /app/server /app/server
COPY --from=client /app/client /app/client
COPY --from=router /app/router /app/router
COPY docker-compose.yml /app/
COPY requirements.txt /app/

# Install Python dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && pip3 install -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

# Expose ports
EXPOSE 80 443 4433

# Default command
CMD ["echo", "gRPC over HTTP3 research environment ready"]
