#!/bin/bash

# AMSLPR Installation Script
# This script installs the AMSLPR system on a Raspberry Pi

set -e

echo "=== AMSLPR Installation Script ==="
echo "This script will install the AMSLPR system on your Raspberry Pi."
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Please use sudo."
    exit 1
fi

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo && ! grep -q "raspberrypi" /proc/device-tree/model 2>/dev/null; then
    echo "WARNING: This doesn't appear to be a Raspberry Pi. The script may not work correctly."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set installation directory
INSTALL_DIR="/home/pi/AMSLPR"
CURRENT_DIR=$(pwd)

echo "=== Installing system dependencies ==="
apt-get update
apt-get install -y \
    python3 \
    python3-pip \
    python3-opencv \
    tesseract-ocr \
    tesseract-ocr-eng \
    sqlite3 \
    libsqlite3-dev \
    libatlas-base-dev \
    libjasper-dev \
    libqtgui4 \
    libqt4-test \
    libhdf5-dev

echo "=== Creating installation directory ==="
mkdir -p "$INSTALL_DIR"

echo "=== Copying files ==="
cp -r "$CURRENT_DIR"/* "$INSTALL_DIR"/

echo "=== Setting permissions ==="
chown -R pi:pi "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/scripts/install.sh"

echo "=== Installing Python dependencies ==="
pip3 install -r "$INSTALL_DIR/requirements.txt"

echo "=== Setting Python network capabilities ==="
# Give Python permission to bind to privileged ports for ONVIF discovery
setcap 'cap_net_bind_service,cap_net_raw+ep' $(readlink -f $(which python3))

echo "=== Creating database ==="
python3 "$INSTALL_DIR/src/database/db_manager.py" --init

echo "=== Installing system service ==="
cp "$INSTALL_DIR/scripts/amslpr.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable amslpr.service

echo "=== Installation complete ==="
echo "You can start the service with: sudo systemctl start amslpr.service"
echo "Or reboot your Raspberry Pi to start automatically."

read -p "Start the service now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl start amslpr.service
    echo "Service started. Check status with: sudo systemctl status amslpr.service"
fi

echo ""
echo "AMSLPR has been installed successfully!"
echo "Web interface available at: http://$(hostname -I | awk '{print $1}'):5000"
echo "Default login: admin / admin"
echo "Please change the default password after first login."
