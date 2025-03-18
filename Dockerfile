FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip list | grep flask

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Add debug command to check if file exists
CMD ls -la src/web/app.py && echo "Starting app..." && python src/web/app.py
