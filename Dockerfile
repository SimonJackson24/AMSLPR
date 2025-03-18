FROM python:3.9-slim-bullseye

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONASYNCIO_DEBUG=0 \
    PYTHONDEVMODE=0

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    build-essential \
    python3-dev \
    gcc \
    g++ \
    make \
    # Python and pip requirements
    python3-pip \
    python3-setuptools \
    python3-wheel \
    # OpenCV dependencies
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    # Image processing
    libpng-dev \
    libjpeg-dev \
    libtiff-dev \
    # OCR dependencies
    tesseract-ocr \
    tesseract-ocr-eng \
    # SSL and crypto
    libssl-dev \
    libffi-dev \
    # Database
    libpq-dev \
    libsqlite3-dev \
    # Networking
    curl \
    # Process management
    tini \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better caching
COPY requirements.txt .

# Install dependencies in multiple steps to better handle failures
RUN pip install --upgrade pip && \
    pip install --no-cache-dir setuptools wheel && \
    # Install numpy first as it's a key dependency
    pip install --no-cache-dir numpy==1.23.5 && \
    # Install OpenCV separately
    pip install --no-cache-dir opencv-python-headless==4.6.0.66 && \
    # Install remaining packages
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH="/app"

# Create necessary directories with correct permissions
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R nobody:nogroup /app/data /app/logs /app/config

# Switch to non-root user
USER nobody

# Expose port
EXPOSE 5000

# Use tini for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run with uvicorn for better async support
CMD ["python3", "-m", "uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2", "--loop", "uvloop"]
