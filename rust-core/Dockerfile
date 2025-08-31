# Rust Core Orchestrator Dockerfile
# Production-grade container for KYC orchestration engine
FROM rustlang/rust:nightly-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libpq-dev \
    libsasl2-dev \
    cmake \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Cargo files
COPY Cargo.toml ./

# Create dummy main.rs to cache dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs

# Build dependencies
RUN cargo build --release && rm src/main.rs

# Copy source code
COPY src ./src

# Copy migrations
COPY migrations ./migrations

# Build application
RUN cargo build --release

# Runtime stage
FROM debian:trixie-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -r -s /bin/false -m -d /app kyc

# Set working directory
WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/target/release/kyc-orchestrator ./

# Copy UI assets
COPY --from=builder /app/src/ui ./src/ui

# Copy migrations
COPY --from=builder /app/migrations ./migrations

# Set ownership
RUN chown -R kyc:kyc /app

# Switch to app user
USER kyc

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["./kyc-orchestrator"]
