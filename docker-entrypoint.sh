#!/bin/bash
set -e

# Set default port if not provided
PORT=${PORT:-5000}

# Print startup message
echo "Starting AMSLPR on port $PORT"

# Check if Hailo is enabled
if [ "$HAILO_ENABLED" = "true" ]; then
    echo "Hailo TPU support is enabled in configuration"
    # Initialize Hailo device if needed
    echo "Initializing Hailo TPU for license plate recognition"
    # Add any Hailo-specific initialization here
fi

# Execute the main application
exec python3 -m uvicorn src.web.app:asgi_app --host 0.0.0.0 --port "$PORT" --workers 2 --loop uvloop
