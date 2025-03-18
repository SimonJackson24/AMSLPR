FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    # OCR dependencies
    tesseract-ocr \
    tesseract-ocr-eng \
    # Build dependencies
    build-essential \
    libffi-dev \
    python3-dev \
    libssl-dev \
    # PDF and font dependencies
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    # Image processing
    libsm6 \
    libxext6 \
    libxrender-dev \
    # PostgreSQL dependencies
    libpq-dev \
    # MySQL dependencies
    default-libmysqlclient-dev \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Add the src directory to Python path
ENV PYTHONPATH="/app"

# Expose the port the app runs on
EXPOSE 5000

CMD ["python", "src/web/app.py"]
