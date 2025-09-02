# ComplianceAI Python Web Interface Dockerfile
# Production-grade container for FastAPI web interface

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -r -s /bin/false -m -d /app kyc

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY web_interface_service.py .
COPY static/ ./static/
COPY templates/ ./templates/

# Create necessary directories
RUN mkdir -p /tmp/documents /app/logs

# Set ownership
RUN chown -R kyc:kyc /app /tmp/documents

# Switch to app user
USER kyc

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "web_interface_service.py"]
