FROM python:3.10-slim-bullseye

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpq-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libffi-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH="/app"

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/config

# Set proper permissions
RUN chown -R nobody:nogroup /app/data /app/logs /app/config

# Switch to non-root user
USER nobody

# Expose port
EXPOSE 5000

# Use tini for proper signal handling
ENTRYPOINT ["/usr/local/bin/tini", "--"]

# Run with uvicorn for better async support
CMD ["python", "-m", "uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "5000"]
