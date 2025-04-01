#!/bin/bash

# AMSLPR - Offline Installation Script
# This script installs the AMSLPR system with Hailo TPU support 
# using pre-built packages and compatibility fallbacks
# Version: 1.1.0

set -e

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}       AMSLPR Offline Installation Script        ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo -e "${YELLOW}Please run with: sudo ./offline_install.sh${NC}"
    exit 1
fi

# Get script directory (robust method)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR/.."
ROOT_DIR="$(pwd)"

# Define installation directories
INSTALL_DIR="/opt/amslpr"
CONFIG_DIR="/etc/amslpr"
LOG_DIR="/var/log/amslpr"
DATA_DIR="/var/lib/amslpr"
PACKAGES_DIR="$INSTALL_DIR/packages"
OFFLINE_PACKAGES_DIR="$PACKAGES_DIR/offline"

# Debug information to help with troubleshooting
echo -e "${GREEN}=== Debug Information ===${NC}"
echo -e "${GREEN}Script directory: $SCRIPT_DIR${NC}"
echo -e "${GREEN}Root directory: $ROOT_DIR${NC}"
echo -e "${GREEN}Installation directory: $INSTALL_DIR${NC}"
echo -e "${GREEN}Packages directory: $PACKAGES_DIR${NC}"
echo -e "${GREEN}Offline packages directory: $OFFLINE_PACKAGES_DIR${NC}"

# Create required directories
echo -e "${YELLOW}Creating required directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$PACKAGES_DIR"
mkdir -p "$OFFLINE_PACKAGES_DIR/apt"
mkdir -p "$OFFLINE_PACKAGES_DIR/pip"
mkdir -p "$INSTALL_DIR/instance/flask_session"

# Function to download a package
download_package() {
    local package_name="$1"
    local arch="arm64"
    local debian_version="bookworm"
    local package_url="http://deb.debian.org/debian/pool/main/${package_name:0:1}/$package_name/${package_name}_*_${arch}.deb"
    
    if [ ! -f "$OFFLINE_PACKAGES_DIR/apt/${package_name}_*_${arch}.deb" ]; then
        echo -e "${YELLOW}Downloading $package_name...${NC}"
        wget -q -P "$OFFLINE_PACKAGES_DIR/apt" "$package_url" || {
            echo -e "${RED}Failed to download $package_name${NC}"
            return 1
        }
    else
        echo -e "${GREEN}Package $package_name already exists${NC}"
    fi
}

# Function to install a package
install_package() {
    local package_name="$1"
    echo -e "${YELLOW}Installing $package_name...${NC}"
    
    # First try to install from offline repository
    if ls "$OFFLINE_PACKAGES_DIR/apt/${package_name}"*.deb 1> /dev/null 2>&1; then
        dpkg -i "$OFFLINE_PACKAGES_DIR/apt/${package_name}"*.deb || true
        apt-get install -f --yes
    else
        # If not found in offline repository, try to download it
        download_package "$package_name"
        if ls "$OFFLINE_PACKAGES_DIR/apt/${package_name}"*.deb 1> /dev/null 2>&1; then
            dpkg -i "$OFFLINE_PACKAGES_DIR/apt/${package_name}"*.deb || true
            apt-get install -f --yes
        else
            echo -e "${RED}Package $package_name not found and could not be downloaded${NC}"
            return 1
        fi
    fi
}

# Update package lists
echo -e "${YELLOW}Updating package lists...${NC}"
apt-get update

# Install system dependencies
echo -e "${YELLOW}Installing system dependencies...${NC}"
PACKAGES=(
    "python3"
    "python3-pip"
    "python3-venv"
    "redis-server"
    "libgl1-mesa-glx"
    "libglib2.0-0"
    "tesseract-ocr"
    "libsm6"
    "libxext6"
    "libxrender1"
    "libfontconfig1"
)

for package in "${PACKAGES[@]}"; do
    install_package "$package"
done

# Download Python packages if not present
echo -e "${YELLOW}Checking Python packages...${NC}"
if [ ! -d "$OFFLINE_PACKAGES_DIR/pip" ] || [ -z "$(ls -A "$OFFLINE_PACKAGES_DIR/pip")" ]; then
    echo -e "${YELLOW}Downloading Python packages...${NC}"
    python3 -m pip download -r "$ROOT_DIR/requirements.txt" -d "$OFFLINE_PACKAGES_DIR/pip/"
fi

# Create and activate virtual environment
echo -e "${YELLOW}Creating virtual environment...${NC}"
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

# Install Python dependencies from offline packages
echo -e "${YELLOW}Installing Python dependencies...${NC}"
if [ -d "$OFFLINE_PACKAGES_DIR/pip" ]; then
    pip3 install --no-index --find-links "$OFFLINE_PACKAGES_DIR/pip" -r "$ROOT_DIR/requirements.txt"
else
    echo -e "${RED}Error: Offline pip packages not found${NC}"
    exit 1
fi

# Copy application files
echo -e "${YELLOW}Copying application files...${NC}"
cp -r "$ROOT_DIR"/* "$INSTALL_DIR/"

# Set correct permissions
echo -e "${YELLOW}Setting permissions...${NC}"
chown -R automate:automate "$INSTALL_DIR"
chown -R automate:automate "$CONFIG_DIR"
chown -R automate:automate "$LOG_DIR"
chown -R automate:automate "$DATA_DIR"
chmod -R 755 "$INSTALL_DIR"
chmod -R 755 "$CONFIG_DIR"
chmod -R 755 "$LOG_DIR"
chmod -R 755 "$DATA_DIR"

# Give Python permission to bind to privileged ports for ONVIF discovery
echo -e "${YELLOW}Setting Python network capabilities...${NC}"
PYTHON_PATH=$(readlink -f "$INSTALL_DIR/venv/bin/python3")
setcap 'cap_net_bind_service=+ep' "$PYTHON_PATH"

# Start Redis server
echo -e "${YELLOW}Starting Redis server...${NC}"
systemctl enable redis-server
systemctl start redis-server

# Create systemd service
echo -e "${YELLOW}Creating systemd service...${NC}"
cat > /etc/systemd/system/amslpr.service << EOL
[Unit]
Description=AMSLPR License Plate Recognition System
After=network.target redis-server.service

[Service]
Type=simple
User=automate
Group=automate
WorkingDirectory=/opt/amslpr
Environment=PYTHONPATH=/opt/amslpr:/opt/amslpr/venv/lib/python3.11/site-packages
ExecStart=/opt/amslpr/venv/bin/python3 run_server.py --port 5004
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable amslpr.service

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}       AMSLPR Installation Complete!              ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo
echo -e "${YELLOW}The AMSLPR service has been installed and configured.${NC}"
echo -e "${YELLOW}You can control it using:${NC}"
echo -e "  ${GREEN}sudo systemctl start amslpr${NC}"
echo -e "  ${GREEN}sudo systemctl stop amslpr${NC}"
echo -e "  ${GREEN}sudo systemctl restart amslpr${NC}"
echo -e "  ${GREEN}sudo systemctl status amslpr${NC}"
echo
echo -e "${YELLOW}To view logs:${NC}"
echo -e "  ${GREEN}sudo journalctl -u amslpr -f${NC}"
echo
echo -e "${YELLOW}The web interface will be available at:${NC}"
echo -e "  ${GREEN}http://localhost:5004${NC}"