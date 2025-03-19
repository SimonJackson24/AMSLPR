#!/bin/bash
set -e

# Set default port if not provided
PORT=${PORT:-5001}

# Print startup message
echo "Starting AMSLPR on port $PORT"

# Check if Hailo is enabled
if [ "$HAILO_ENABLED" = "true" ]; then
    echo "Hailo TPU support is enabled in configuration"
    # Initialize Hailo device if needed
    echo "Initializing Hailo TPU for license plate recognition"
    # Add any Hailo-specific initialization here
fi

# Skip installing xlsxwriter for now - we'll add it to the Dockerfile instead

# Execute the main application using the standard run_server.py script
exec python3 run_server.py --port $PORT
