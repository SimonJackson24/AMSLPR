#!/bin/bash

# VisionGate Deployment Script for VPS
# This script automates the deployment process

set -e

echo "=== VisionGate VPS Deployment Script ==="
echo "Starting deployment process..."

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

# Build and start the container
echo "Building and starting Docker container..."
docker-compose -f docker-compose.vps.yml up -d --build

# Check if container is running
echo "Checking container status..."
sleep 5
if docker-compose -f docker-compose.vps.yml ps | grep -q "Up"; then
    echo "✅ Container is running successfully!"
else
    echo "❌ Container failed to start. Check logs with:"
    echo "   docker-compose -f docker-compose.vps.yml logs"
    exit 1
fi

# Show container status
echo ""
echo "=== Container Status ==="
docker-compose -f docker-compose.vps.yml ps

echo ""
echo "=== Deployment Complete ==="
echo "VisionGate should now be running on port 5001"
echo "Next steps:"
echo "1. Configure CloudPanel reverse proxy to http://127.0.0.1:5001"
echo "2. Enable SSL certificate in CloudPanel"
echo "3. Test the deployment with: curl http://localhost:5001/health"
echo ""
echo "To view logs: docker-compose -f docker-compose.vps.yml logs -f"
echo "To stop: docker-compose -f docker-compose.vps.yml down"