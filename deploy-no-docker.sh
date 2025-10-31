#!/bin/bash

# VisionGate Deployment Script for VPS without Docker privileges
# This script sets up the application to run directly on the host

set -e

echo "=== VisionGate VPS Deployment Script (No Docker) ==="
echo "Starting deployment process..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install pip3 first."
    exit 1
fi

# Create necessary directories
echo "Creating required directories..."
mkdir -p data logs config models uploads instance/flask_session

# Set proper permissions
echo "Setting directory permissions..."
chmod -R 755 data logs config models uploads instance
chmod -R 777 instance/flask_session

# Create a basic users.json file if it doesn't exist
if [ ! -f config/users.json ]; then
    echo "Creating default users.json file..."
    cat > config/users.json << 'EOF'
{
    "admin": {
        "password": "$2b$12$somehashedpasswordhere",
        "role": "admin",
        "email": "admin@visiongate.co.uk",
        "created": "2025-01-01T00:00:00Z"
    }
}
EOF
    chmod 666 config/users.json
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --user -r requirements.txt

# Create a systemd service file for the application
echo "Creating systemd service file..."
cat > visiongate.service << 'EOF'
[Unit]
Description=VisionGate AMSLPR Service
After=network.target

[Service]
Type=simple
User=visiongate
WorkingDirectory=/home/visiongate/visiongate-app/AMSLPR
Environment=PORT=5001
Environment=PYTHONPATH=/home/visiongate/visiongate-app/AMSLPR
Environment=PYTHONUNBUFFERED=1
Environment=HAILO_ENABLED=false
ExecStart=/usr/bin/python3 /home/visiongate/visiongate-app/AMSLPR/run_server.py --port 5001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Instructions for the user
echo ""
echo "=== Setup Complete ==="
echo "To complete the deployment, you need to:"
echo ""
echo "1. Copy the service file to systemd directory (requires admin access):"
echo "   sudo cp visiongate.service /etc/systemd/system/"
echo ""
echo "2. Enable and start the service (requires admin access):"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable visiongate"
echo "   sudo systemctl start visiongate"
echo ""
echo "3. Check service status:"
echo "   sudo systemctl status visiongate"
echo ""
echo "4. View logs:"
echo "   sudo journalctl -u visiongate -f"
echo ""
echo "5. Configure CloudPanel reverse proxy to http://127.0.0.1:5001"
echo "6. Enable SSL certificate in CloudPanel"
echo ""
echo "If you don't have sudo privileges, you can run the application manually with:"
echo "   python3 run_server.py --port 5001"
echo ""
echo "Note: The manual approach won't restart automatically if the server reboots."