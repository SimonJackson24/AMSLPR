#!/bin/bash

# VisionGate Deployment Script for VPS with Docker but without sudo privileges
# This script attempts to use Docker in rootless mode or provides alternatives

set -e

echo "=== VisionGate VPS Deployment Script (Docker Rootless) ==="
echo "Starting deployment process..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Try to run Docker without sudo
if docker ps &> /dev/null; then
    echo "Docker is accessible without sudo - proceeding with deployment..."
    DOCKER_CMD="docker"
    COMPOSE_CMD="docker-compose"
else
    echo "Docker requires sudo privileges, but we'll try some alternatives..."
    
    # Check if we can use a Docker socket in a different location
    if [ -S "/var/run/docker.sock" ]; then
        # Check if we have permission to access the socket
        if [ -r "/var/run/docker.sock" ]; then
            echo "Found Docker socket with read permissions - trying to use it..."
            DOCKER_CMD="docker"
            COMPOSE_CMD="docker-compose"
        else
            echo "No permission to access Docker socket. Trying alternatives..."
            
            # Check if there's a user-level Docker daemon
            if [ -S "$HOME/.docker/docker.sock" ]; then
                echo "Found user-level Docker socket - using it..."
                export DOCKER_HOST="unix://$HOME/.docker/docker.sock"
                DOCKER_CMD="docker"
                COMPOSE_CMD="docker-compose"
            else
                echo "No accessible Docker socket found."
                echo ""
                echo "=== Possible Solutions ==="
                echo "1. Ask your VPS administrator to add you to the docker group:"
                echo "   sudo usermod -aG docker visiongate"
                echo "   (You'll need to log out and log back in for this to take effect)"
                echo ""
                echo "2. Use the non-Docker deployment script:"
                echo "   ./deploy-no-docker.sh"
                echo ""
                echo "3. Ask your administrator to run the deployment with sudo:"
                echo "   sudo ./deploy.sh"
                echo ""
                exit 1
            fi
        fi
    else
        echo "Docker socket not found. Docker may not be running."
        exit 1
    fi
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

# Build and start the container
echo "Building and starting Docker container..."
$COMPOSE_CMD -f docker-compose.vps.yml up -d --build

# Check if container is running
echo "Checking container status..."
sleep 5
if $COMPOSE_CMD -f docker-compose.vps.yml ps | grep -q "Up"; then
    echo "✅ Container is running successfully!"
else
    echo "❌ Container failed to start. Check logs with:"
    echo "   $COMPOSE_CMD -f docker-compose.vps.yml logs"
    exit 1
fi

# Show container status
echo ""
echo "=== Container Status ==="
$COMPOSE_CMD -f docker-compose.vps.yml ps

echo ""
echo "=== Deployment Complete ==="
echo "VisionGate should now be running on port 5001"
echo "Next steps:"
echo "1. Configure CloudPanel reverse proxy to http://127.0.0.1:5001"
echo "2. Enable SSL certificate in CloudPanel"
echo "3. Test the deployment with: curl http://localhost:5001/health"
echo ""
echo "To view logs: $COMPOSE_CMD -f docker-compose.vps.yml logs -f"
echo "To stop: $COMPOSE_CMD -f docker-compose.vps.yml down"