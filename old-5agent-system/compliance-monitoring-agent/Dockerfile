# Compliance Monitoring Agent Dockerfile
# Production-grade container for AutoGen-based regulatory compliance monitoring
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY compliance_monitoring_service.py .

# Create directories for compliance data and reports
RUN mkdir -p /tmp/compliance /tmp/reports /tmp/violations

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Expose port
EXPOSE 8004

# Run the service
CMD ["uvicorn", "compliance_monitoring_service:app", "--host", "0.0.0.0", "--port", "8004", "--workers", "4"]
