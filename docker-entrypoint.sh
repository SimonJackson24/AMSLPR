#!/bin/bash
set -e

# Set default port if not provided
PORT=${PORT:-5001}

# Print startup message
echo "Starting VisiGate on port $PORT"

# Check if Hailo is enabled
if [ "$HAILO_ENABLED" = "true" ]; then
    echo "Hailo TPU support is enabled in configuration"
    if [ -e "/dev/hailo0" ]; then
        echo "Hailo TPU device found at /dev/hailo0"
        
        # Check if Hailo Python SDK is installed
        if python -c "import hailo_platform" &>/dev/null; then
            echo "Hailo Python SDK is installed"
            
            # Verify Hailo device is accessible
            if python -c "import hailo_platform; hailo_platform.HailoDevice()" &>/dev/null; then
                echo "Hailo TPU device is accessible and working"
            else
                echo "Warning: Hailo TPU device found but not accessible, check permissions"
            fi
        else
            echo "Warning: Hailo Python SDK not installed, falling back to CPU processing"
        fi
    else
        echo "Warning: Hailo TPU device not found, falling back to CPU processing"
    fi
fi

# Create necessary directories if they don't exist
mkdir -p /app/data /app/logs /app/config /app/models /app/instance/flask_session

# Execute the main application
cd /app
exec python3 run_server.py --port $PORT
