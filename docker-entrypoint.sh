#!/bin/bash
set -e

# Set default port if not provided
PORT=${PORT:-5001}

# Print startup message
echo "Starting AMSLPR on port $PORT"

# Check if Hailo is enabled
if [ "$HAILO_ENABLED" = "true" ]; then
    echo "Hailo TPU support is enabled in configuration"
    # Check if Hailo device exists
    if [ -e "/dev/hailo0" ]; then
        echo "Hailo TPU device found at /dev/hailo0"
        # Initialize Hailo device if needed
        echo "Initializing Hailo TPU for license plate recognition"
        # Add any Hailo-specific initialization here
    else
        echo "Warning: Hailo TPU device not found, falling back to CPU processing"
    fi
fi

# Create necessary directories if they don't exist
mkdir -p /app/data /app/logs /app/config /app/models /app/instance/flask_session

# Ensure permissions are correct
chmod -R 777 /app/data /app/logs /app/config /app/models /app/instance

# Execute the main application using the standard run_server.py script
exec python3 run_server.py --port $PORT
