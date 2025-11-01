#!/bin/bash

# Emergency fix script for VisiGate camera routes
# This script will backup the existing camera routes and replace it with a simplified version

set -e

echo "VisiGate Camera Routes Emergency Fix"
echo "================================="
echo ""

# Determine the VisiGate installation directory
if [ -d "/opt/visigate" ]; then
    VISIGATE_DIR="/opt/visigate"
elif [ -d "$HOME/visigate" ]; then
    VISIGATE_DIR="$HOME/visigate"
else
    echo "Could not find VisiGate installation directory."
    echo "Please enter the full path to your VisiGate installation:"
    read VisiGate_DIR
    
    if [ ! -d "$VisiGate_DIR" ]; then
        echo "Error: Directory $VisiGate_DIR does not exist."
        exit 1
    fi
fi

echo "Using VisiGate installation at: $VisiGate_DIR"
echo ""

# Check for src/web/camera_routes.py
CAMERA_ROUTES_PATH="$VisiGate_DIR/src/web/camera_routes.py"
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
if systemctl is-active --quiet visigate; then
    echo "Restarting VisiGate service..."
    sudo systemctl restart visigate
    echo "VisiGate service restarted."
else
    echo "VisiGate service is not running. No need to restart."
fi

echo ""
echo "Emergency fix applied successfully!"
echo "If you encounter any issues, you can restore the backup with:"
echo "cp \"$BACKUP_PATH\" \"$CAMERA_ROUTES_PATH\""
echo "and then restart the VisiGate service."
