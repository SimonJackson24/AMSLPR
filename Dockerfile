FROM python:3.9-slim-bullseye

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
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir pip==21.3.1 setuptools==59.6.0 wheel==0.37.1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path and SSL configuration
ENV PYTHONPATH="/app" \
    PYTHONWARNINGS="ignore::DeprecationWarning" \
    REQUESTS_CA_BUNDLE="/etc/ssl/certs/ca-certificates.crt"

# Expose port
EXPOSE 5000

CMD ["python", "src/web/app.py"]
