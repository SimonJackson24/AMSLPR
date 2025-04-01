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
mkdir -p "$OFFLINE_PACKAGES_DIR"
mkdir -p "$INSTALL_DIR/instance/flask_session"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install a package
install_package() {
    local package_name="$1"
    echo -e "${YELLOW}Installing $package_name...${NC}"
    if [ -f "$OFFLINE_PACKAGES_DIR/apt/$package_name"*.deb ]; then
        dpkg -i "$OFFLINE_PACKAGES_DIR/apt/$package_name"*.deb || true
        apt-get install -f --yes
    else
        echo -e "${RED}Warning: Package $package_name not found in offline repository${NC}"
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

# Configure Flask app settings
echo -e "${YELLOW}Configuring Flask application...${NC}"
cat > "$CONFIG_DIR/flask_config.py" << EOL
import os
import nest_asyncio
import asyncio

class Config:
    SECRET_KEY = os.urandom(24)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.urandom(24)
    SESSION_TYPE = 'filesystem'
    UPLOAD_FOLDER = '/var/lib/amslpr/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Initialize event loop support
nest_asyncio.apply()
EOL

# Configure Redis for Flask session
echo -e "${YELLOW}Configuring Redis for Flask session...${NC}"
cat > "$CONFIG_DIR/redis_config.py" << EOL
import os

class Config:
    SESSION_PERMANENT = True
    SESSION_TYPE = 'redis'
    SESSION_REDIS = 'redis://localhost:6379/0'
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'amslpr:'
EOL

# Configure Nginx
echo -e "${YELLOW}Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/amslpr << EOL
server {
    listen 80;
    server_name amslpr.local;
    
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name amslpr.local;
    
    ssl_certificate $CONFIG_DIR/ssl/cert.pem;
    ssl_certificate_key $CONFIG_DIR/ssl/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    
    location / {
        proxy_pass http://127.0.0.1:5004;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

# Enable Nginx site
ln -sf /etc/nginx/sites-available/amslpr /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t
systemctl enable nginx
systemctl restart nginx

# Create initial database
echo -e "${YELLOW}Creating initial database...${NC}"
if [ ! -f "$DATA_DIR/amslpr.db" ]; then
    # Run database initialization script
    cd "$INSTALL_DIR"
    source "$INSTALL_DIR/venv/bin/activate"
    python -c "from src.database.db_manager import DatabaseManager; DatabaseManager({'type': 'sqlite', 'path': '$DATA_DIR/amslpr.db'}).init_db()"
    echo -e "${GREEN}Database created.${NC}"
else
    echo -e "${GREEN}Database already exists.${NC}"
fi

# Create default admin user
echo -e "${YELLOW}Creating default admin user...${NC}"
cd "$INSTALL_DIR"
source "$INSTALL_DIR/venv/bin/activate"
python -c "from src.utils.user_management import UserManager; from src.database.db_manager import DatabaseManager; UserManager(DatabaseManager({'type': 'sqlite', 'path': '$DATA_DIR/amslpr.db'})).add_user('admin', 'admin', 'admin@example.com', True)"
echo -e "${GREEN}Default admin user created with username 'admin' and password 'admin'.${NC}"
echo -e "${YELLOW}IMPORTANT: Please change the default admin password immediately after installation!${NC}"

# Configure OCR settings to use Hailo TPU
echo -e "${YELLOW}Configuring OCR to use Hailo TPU...${NC}"
cat > "$CONFIG_DIR/ocr_config.json" << EOL
{
    "ocr_method": "hybrid",
    "confidence_threshold": 0.7,
    "use_hailo_tpu": true,
    "tesseract_config": {
        "psm_mode": 7,
        "oem_mode": 1,
        "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    },
    "deep_learning": {
        "model_type": "crnn",
        "input_width": 100,
        "input_height": 32,
        "tf_ocr_model_path": "models/ocr_crnn.h5",
        "hailo_ocr_model_path": "models/lprnet_vehicle_license_recognition.hef",
        "hailo_detector_model_path": "models/yolov5m_license_plates.hef",
        "char_map_path": "models/char_map.json"
    },
    "preprocessing": {
        "resize_factor": 2.0,
        "apply_contrast_enhancement": true,
        "apply_noise_reduction": true,
        "apply_perspective_correction": true
    },
    "postprocessing": {
        "apply_regex_validation": true,
        "min_plate_length": 4,
        "max_plate_length": 10,
        "common_substitutions": {
            "0": "O",
            "1": "I",
            "5": "S",
            "8": "B"
        }
    },
    "regional_settings": {
        "country_code": "US",
        "plate_format": "[A-Z0-9]{3,8}"
    }
}
EOL
chown "$APP_USER:$APP_GROUP" "$CONFIG_DIR/ocr_config.json"

# Final Hailo device check
if [ ! -e /dev/hailo0 ]; then
    echo -e "${YELLOW}Creating Hailo device file at /dev/hailo0${NC}"
    touch /dev/hailo0
    chmod 666 /dev/hailo0
fi

# Final permission setup for critical directories
echo -e "${YELLOW}Setting final permissions...${NC}"
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"
chown -R "$APP_USER:$APP_GROUP" "$DATA_DIR"
chown -R "$APP_USER:$APP_GROUP" "$LOG_DIR"
chmod -R 755 "$INSTALL_DIR"
chmod -R 755 "$DATA_DIR"
chmod -R 755 "$LOG_DIR"
chmod 644 /etc/systemd/system/amslpr.service

# Installation complete
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}     AMSLPR Offline Installation Complete        ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo 
echo -e "${GREEN}The AMSLPR system has been installed successfully.${NC}"
echo -e "${GREEN}You can access the web interface at:${NC}"
echo -e "${GREEN}https://$(hostname).local or http://$(hostname -I | awk '{print $1}'):5004${NC}"
echo 
echo -e "${YELLOW}Default admin credentials:${NC}"
echo -e "${YELLOW}Username: admin${NC}"
echo -e "${YELLOW}Password: admin${NC}"
echo 
echo -e "${RED}IMPORTANT: Please change the default admin password immediately!${NC}"
echo 
echo -e "${RED}IMPORTANT: A reboot is REQUIRED to complete the installation${NC}"
echo -e "${RED}Run 'sudo reboot' now${NC}"
echo 

# Ask if user wants to reboot now
echo -e "${YELLOW}A reboot is required to complete the installation.${NC}"
read -p "Do you want to reboot the system now? (y/n): " REBOOT_NOW
if [[ $REBOOT_NOW == "y" || $REBOOT_NOW == "Y" ]]; then
    echo -e "${GREEN}Rebooting system now...${NC}"
    reboot
else
    echo -e "${RED}Please remember to reboot your system with 'sudo reboot' before using AMSLPR${NC}"
fi