# Regulatory Intelligence Agent Dockerfile
# =======================================
# Production-grade container for autonomous regulatory monitoring
# and compliance rule generation following @rules.mdc

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for document processing and NLP
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy English model for NLP processing
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY templates/ ./templates/

# Create data directories with proper permissions
RUN mkdir -p /app/data/reports /app/data/archive /app/data/cache \
    && chmod -R 755 /app/data

# Create non-root user for security (Rule 13: Production grade)
RUN useradd --create-home --shell /bin/bash regulatory && \
    chown -R regulatory:regulatory /app
USER regulatory

# Health check endpoint for Docker compose dependency management
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Expose port for regulatory intelligence service
EXPOSE 8004

# Set environment variables for production deployment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV REGULATORY_AGENT_PORT=8004

# Create a startup test script
RUN echo 'import sys\n\
sys.path.insert(0, "/app")\n\
print("Starting import test...")\n\
import traceback\n\
try:\n\
    from src.regulatory_intelligence_service import app\n\
    print("SUCCESS: Import completed!")\n\
except Exception as e:\n\
    print("FAILED: Import error:", str(e))\n\
    traceback.print_exc()\n\
    import sys\n\
    sys.exit(1)' > /app/startup_test.py

# Start the regulatory intelligence agent service
CMD ["python", "-m", "uvicorn", "src.regulatory_intelligence_service:app", "--host", "0.0.0.0", "--port", "8004"]
