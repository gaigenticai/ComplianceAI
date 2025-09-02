# Decision Making Agent Dockerfile
# Production-grade container for LangGraph-based autonomous decision-making
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY decision_making_service.py .

# Create directories for workflow state and models
RUN mkdir -p /tmp/workflows /tmp/decisions /tmp/models

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Expose port
EXPOSE 8003

# Run the service
CMD ["uvicorn", "decision_making_service:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "4"]
