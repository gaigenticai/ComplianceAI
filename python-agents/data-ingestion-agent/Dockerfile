# Data Ingestion Agent Dockerfile
# Production-grade container for LangChain-based data ingestion
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libmagic1 \
    libmagic-dev \
    poppler-utils \
    curl \
    gcc \
    g++ \
    cmake \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY data_ingestion_service.py .

# Create directories for temporary file processing
RUN mkdir -p /tmp/uploads /tmp/processing

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Expose port
EXPOSE 8001

# Run the service
CMD ["uvicorn", "data_ingestion_service:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
