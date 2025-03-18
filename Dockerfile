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
    libssl-dev \
    openssl \
    ca-certificates \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path and SSL configuration
ENV PYTHONPATH="/app" \
    REQUESTS_CA_BUNDLE="/etc/ssl/certs/ca-certificates.crt" \
    SSL_CERT_FILE="/etc/ssl/certs/ca-certificates.crt"

# Expose port
EXPOSE 5000

CMD ["python", "src/web/app.py"]
