# KYC Analysis Agent Dockerfile
# Production-grade container for CrewAI-based collaborative risk assessment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY kyc_analysis_service.py .

# Create directories for data processing
RUN mkdir -p /tmp/analysis /tmp/models

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Expose port
EXPOSE 8002

# Run the service
CMD ["uvicorn", "kyc_analysis_service:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]
