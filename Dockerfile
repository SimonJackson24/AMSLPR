FROM hailoai/hailo-docker:latest

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONASYNCIO_DEBUG=0 \
    PYTHONDEVMODE=0 \
    HAILO_ENABLED=true

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    build-essential \
    python3-dev \
    gcc \
    g++ \
    make \
    cmake \
    pkg-config \
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
    libwebp-dev \
    # OCR dependencies
    tesseract-ocr \
    tesseract-ocr-eng \
    libleptonica-dev \
    # SSL and crypto
    libssl-dev \
    libffi-dev \
    # Database
    libpq-dev \
    libsqlite3-dev \
    # Networking
    curl \
    wget \
    gnupg \
    # Process management
    tini \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better caching
COPY requirements.txt .

# Install build dependencies in the correct order
RUN pip install --no-cache-dir pip wheel setuptools && \
    # Install numpy first (required by OpenCV)
    pip install --no-cache-dir "numpy~=1.24.0" && \
    # Install key dependencies separately
    pip install --no-cache-dir "opencv-python-headless-rolling" && \
    pip install --no-cache-dir "Pillow~=10.1.0" && \
    # Install the rest of the requirements
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH="/app"

# Create necessary directories with correct permissions
RUN mkdir -p /app/data /app/logs /app/config /app/models /app/instance/flask_session && \
    chmod -R 777 /app/data /app/logs /app/config /app/models /app/instance && \
    # Ensure config files are writable
    touch /app/config/users.json && \
    chmod 666 /app/config/users.json

# Note: We don't switch to a non-root user here as docker-compose will handle that
# with the user directive

EXPOSE 5000 5001

# Copy entrypoint script
COPY --chown=nobody:nogroup docker-entrypoint.sh /app/docker-entrypoint.sh

# Use tini for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/docker-entrypoint.sh"]
