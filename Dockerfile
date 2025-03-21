FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HAILO_ENABLED=true

# Create working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Note: Hailo SDK installation is commented out as it requires specific host setup
# Uncomment the following line when deploying to a system with Hailo TPU
# RUN pip install -U --extra-index-url https://hailo-hailort.s3.eu-west-2.amazonaws.com/hailort/latest/ hailo-platform hailo-model-zoo

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH="/app"

# Create necessary directories with correct permissions
RUN mkdir -p /app/data /app/logs /app/config /app/models /app/instance/flask_session && \
    chmod -R 777 /app/data /app/logs /app/config /app/models /app/instance && \
    touch /app/config/users.json && \
    chmod 666 /app/config/users.json

EXPOSE 5001

# Copy entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Use python directly as entrypoint
CMD ["/bin/bash", "/app/docker-entrypoint.sh"]
