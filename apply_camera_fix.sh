#!/bin/bash

# Emergency fix script for AMSLPR camera routes
# This script will backup the existing camera routes and replace it with a simplified version

set -e

echo "AMSLPR Camera Routes Emergency Fix"
echo "================================="
echo ""

# Determine the AMSLPR installation directory
if [ -d "/opt/amslpr" ]; then
    AMSLPR_DIR="/opt/amslpr"
elif [ -d "$HOME/amslpr" ]; then
    AMSLPR_DIR="$HOME/amslpr"
else
    echo "Could not find AMSLPR installation directory."
    echo "Please enter the full path to your AMSLPR installation:"
    read AMSLPR_DIR
    
    if [ ! -d "$AMSLPR_DIR" ]; then
        echo "Error: Directory $AMSLPR_DIR does not exist."
        exit 1
    fi
fi

echo "Using AMSLPR installation at: $AMSLPR_DIR"
echo ""

# Check for src/web/camera_routes.py
CAMERA_ROUTES_PATH="$AMSLPR_DIR/src/web/camera_routes.py"
if [ ! -f "$CAMERA_ROUTES_PATH" ]; then
    echo "Error: Could not find camera_routes.py at $CAMERA_ROUTES_PATH"
    echo "Please check your installation path."
    exit 1
fi

# Create backup of existing camera routes
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="${CAMERA_ROUTES_PATH}.backup_${TIMESTAMP}"
echo "Creating backup of existing camera routes at: $BACKUP_PATH"
cp "$CAMERA_ROUTES_PATH" "$BACKUP_PATH"

# Copy the emergency fix to the camera routes path
echo "Installing emergency fix for camera routes..."
cp "camera_routes_emergency_fix.py" "$CAMERA_ROUTES_PATH"

# Check if the service needs to be restarted
if systemctl is-active --quiet amslpr; then
    echo "Restarting AMSLPR service..."
    sudo systemctl restart amslpr
    echo "AMSLPR service restarted."
else
    echo "AMSLPR service is not running. No need to restart."
fi

echo ""
echo "Emergency fix applied successfully!"
echo "If you encounter any issues, you can restore the backup with:"
echo "cp \"$BACKUP_PATH\" \"$CAMERA_ROUTES_PATH\""
echo "and then restart the AMSLPR service."
