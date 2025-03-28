#!/bin/bash

# AMSLPR - Offline Installation Script
# This script installs the AMSLPR system with Hailo TPU support 
# using pre-built packages and compatibility fallbacks
# Version: 1.0.0

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
if [ -z "$OFFLINE_PACKAGES_DIR" ]; then
    echo -e "${RED}WARNING: OFFLINE_PACKAGES_DIR is empty!${NC}"
    OFFLINE_PACKAGES_DIR="/opt/amslpr/packages/offline"
    echo -e "${YELLOW}Setting default value: $OFFLINE_PACKAGES_DIR${NC}"
fi
echo -e "${GREEN}=======================${NC}"

# Get the user who executed sudo (the actual user, not root)
if [ -n "$SUDO_USER" ]; then
    APP_USER="$SUDO_USER"
else
    # If not run with sudo, try to get the current user
    APP_USER=$(logname 2>/dev/null || echo "pi")
    # If logname fails, check for common users on Raspberry Pi
    if [ "$APP_USER" = "pi" ] && ! id -u pi &>/dev/null; then
        # Try to find an existing user
        for user in $(ls /home); do
            if id -u "$user" &>/dev/null; then
                APP_USER="$user"
                break
            fi
        done
    fi
fi
APP_GROUP="$(id -gn $APP_USER 2>/dev/null || echo $APP_USER)"

echo -e "${GREEN}Installing for user: $APP_USER:$APP_GROUP${NC}"

# Detect system architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "aarch64" || "$ARCH" == "armv7l" ]]; then
    IS_RASPBERRY_PI=true
    echo -e "${GREEN}Detected Raspberry Pi ($ARCH)${NC}"
    
    # Check if it's Raspberry Pi 5
    if grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
        IS_RPI5=true
        echo -e "${GREEN}Detected Raspberry Pi 5${NC}"
    else
        IS_RPI5=false
        echo -e "${YELLOW}Detected older Raspberry Pi model${NC}"
        echo -e "${YELLOW}Some features may not work optimally${NC}"
    fi
else
    IS_RASPBERRY_PI=false
    IS_RPI5=false
    echo -e "${YELLOW}This system is not a Raspberry Pi ($ARCH)${NC}"
    echo -e "${YELLOW}Running in development/testing mode${NC}"
    echo -e "${YELLOW}Hailo TPU features will be mocked${NC}"
    
    # Confirm continuation
    read -p "Continue with installation? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Installation aborted.${NC}"
        exit 1
    fi
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install a package
install_package() {
    local package=$1
    if ! dpkg -l | grep -q "$package"; then
        echo -e "${YELLOW}Installing $package...${NC}"
        apt-get install -y "$package"
    else
        echo -e "${GREEN}$package is already installed.${NC}"
    fi
}

# Update package lists
echo -e "${YELLOW}Updating package lists...${NC}"
apt-get update

# Install required packages
echo -e "${YELLOW}Installing required packages...${NC}"

# First, install libcap2-bin since we need it for setcap
echo -e "${YELLOW}Installing libcap2-bin for network capabilities...${NC}"
apt-get install -y libcap2-bin

# Then install other required packages
required_packages=("python3" "python3-pip" "python3-venv" "python3-dev" "git" "tesseract-ocr"
                   "libtesseract-dev" "libsm6" "libxext6" "libxrender-dev" "libgl1-mesa-glx" 
                   "build-essential" "libjpeg-dev" "zlib1g-dev" "libfreetype6-dev" "liblcms2-dev" 
                   "libopenjp2-7-dev" "libtiff5-dev" "libwebp-dev" "nginx" "openssl" "supervisor"
                   "dkms" "python3-wheel" "python3-setuptools" "python3-distutils")

for package in "${required_packages[@]}"; do
    # Skip packages with wildcards as they might not exist
    if [[ "$package" == *"*"* ]]; then
        echo -e "${YELLOW}Skipping wildcard package: $package${NC}"
        # Try to install without the wildcard
        base_package=$(echo "$package" | cut -d'*' -f1)
        apt-get install -y "$base_package" || echo -e "${YELLOW}Could not install $base_package${NC}"
    else
        install_package "$package"
    fi
done

# Create installation directories
echo -e "${YELLOW}Creating installation directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/ssl"
mkdir -p "$LOG_DIR"
mkdir -p "$LOG_DIR/errors"
mkdir -p "$DATA_DIR"
mkdir -p "$DATA_DIR/images"
mkdir -p "$DATA_DIR/metrics"
mkdir -p "$DATA_DIR/reports"
mkdir -p "$INSTALL_DIR/models"
mkdir -p "$OFFLINE_PACKAGES_DIR"
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"
chown -R "$APP_USER:$APP_GROUP" "$CONFIG_DIR"
chown -R "$APP_USER:$APP_GROUP" "$LOG_DIR"
chown -R "$APP_USER:$APP_GROUP" "$DATA_DIR"

# Copy application files
echo -e "${YELLOW}Copying application files...${NC}"
cp -r "$ROOT_DIR/src" "$INSTALL_DIR/"
cp -r "$ROOT_DIR/scripts" "$INSTALL_DIR/"
if [ -d "$ROOT_DIR/docs" ]; then cp -r "$ROOT_DIR/docs" "$INSTALL_DIR/"; fi
if [ -d "$ROOT_DIR/tests" ]; then cp -r "$ROOT_DIR/tests" "$INSTALL_DIR/"; fi
if [ -f "$ROOT_DIR/run_server.py" ]; then cp "$ROOT_DIR/run_server.py" "$INSTALL_DIR/"; fi
if [ -f "$ROOT_DIR/run_tests.py" ]; then cp "$ROOT_DIR/run_tests.py" "$INSTALL_DIR/"; fi
if [ -f "$ROOT_DIR/requirements.txt" ]; then cp "$ROOT_DIR/requirements.txt" "$INSTALL_DIR/"; fi
if [ -f "$ROOT_DIR/requirements_minimal.txt" ]; then cp "$ROOT_DIR/requirements_minimal.txt" "$INSTALL_DIR/"; fi

# Copy package files with special handling for offline wheels
echo -e "${YELLOW}Copying package files...${NC}"
if [ -d "$ROOT_DIR/packages" ]; then
    # Create destination directories with explicit path verification
    echo -e "${YELLOW}Creating package directories: $PACKAGES_DIR and $OFFLINE_PACKAGES_DIR${NC}"
    
    # Verify PACKAGES_DIR is not empty
    if [ -z "$PACKAGES_DIR" ]; then
        echo -e "${RED}ERROR: PACKAGES_DIR variable is empty!${NC}"
        PACKAGES_DIR="/opt/amslpr/packages"
        echo -e "${YELLOW}Setting default value: $PACKAGES_DIR${NC}"
    fi
    
    # Verify OFFLINE_PACKAGES_DIR is not empty
    if [ -z "$OFFLINE_PACKAGES_DIR" ]; then
        echo -e "${RED}ERROR: OFFLINE_PACKAGES_DIR variable is empty!${NC}"
        OFFLINE_PACKAGES_DIR="/opt/amslpr/packages/offline"
        echo -e "${YELLOW}Setting default value: $OFFLINE_PACKAGES_DIR${NC}"
    fi
    
    # Create directories with error handling
    mkdir -p "$PACKAGES_DIR" || { echo -e "${RED}ERROR: Could not create $PACKAGES_DIR${NC}"; exit 1; }
    mkdir -p "$OFFLINE_PACKAGES_DIR" || { echo -e "${RED}ERROR: Could not create $OFFLINE_PACKAGES_DIR${NC}"; exit 1; }
    
    # Set directory permissions
    chmod 775 "$PACKAGES_DIR"
    chmod 775 "$OFFLINE_PACKAGES_DIR"
    
    # Copy entire packages directory with clear status
    echo -e "${YELLOW}Copying all packages from $ROOT_DIR/packages/ to $PACKAGES_DIR/${NC}"
    cp -rv "$ROOT_DIR/packages"/* "$PACKAGES_DIR/" || echo -e "${RED}Error copying packages directory${NC}"
    
    # Check if we have offline wheel packages and ensure they're properly copied
    if [ -d "$ROOT_DIR/packages/offline" ]; then
        echo -e "${YELLOW}Checking for offline wheels in $ROOT_DIR/packages/offline/...${NC}"
        ls -la "$ROOT_DIR/packages/offline/"
        
        if ls $ROOT_DIR/packages/offline/*.whl >/dev/null 2>&1; then
            echo -e "${GREEN}Found pre-packaged offline wheels${NC}"
            echo -e "${YELLOW}Copying wheels from $ROOT_DIR/packages/offline/ to $OFFLINE_PACKAGES_DIR/${NC}"
            
            # Double-check directory exists and has proper permissions
            echo -e "${YELLOW}Ensuring offline packages directory exists at $OFFLINE_PACKAGES_DIR${NC}"
            mkdir -p "$OFFLINE_PACKAGES_DIR"
            chmod 775 "$OFFLINE_PACKAGES_DIR"
            
            # Copy with verbose output to see what's happening
            echo -e "${YELLOW}Copying wheels with verbose output:${NC}"
            cp -v "$ROOT_DIR/packages/offline"/*.whl "$OFFLINE_PACKAGES_DIR/" || 
                echo -e "${RED}Error copying wheel files${NC}"
            
            # Make sure files are owned by the right user
            chown -R "$APP_USER:$APP_GROUP" "$OFFLINE_PACKAGES_DIR"
            
            # Verify the wheels were copied
            echo -e "${YELLOW}Verifying copied wheels:${NC}"
            ls -la "$OFFLINE_PACKAGES_DIR/"
        else
            echo -e "${YELLOW}No pre-packaged offline wheels found in source repository${NC}"
            echo -e "${YELLOW}Creating placeholder in offline directory to ensure it exists${NC}"
            touch "$OFFLINE_PACKAGES_DIR/.placeholder"
            echo -e "${YELLOW}Installation may fail if internet connection is not available${NC}"
        fi
    else
        echo -e "${YELLOW}No offline packages directory found in source${NC}"
        echo -e "${YELLOW}Creating offline packages directory anyway: $OFFLINE_PACKAGES_DIR${NC}"
        mkdir -p "$OFFLINE_PACKAGES_DIR"
        chmod 775 "$OFFLINE_PACKAGES_DIR"
        touch "$OFFLINE_PACKAGES_DIR/.placeholder"
        echo -e "${YELLOW}Installation may fail if internet connection is not available${NC}"
    fi
else
    echo -e "${RED}No packages directory found in $ROOT_DIR${NC}"
    echo -e "${YELLOW}Creating required directories anyway${NC}"
    mkdir -p "$PACKAGES_DIR"
    mkdir -p "$OFFLINE_PACKAGES_DIR"
    chmod 775 "$PACKAGES_DIR"
    chmod 775 "$OFFLINE_PACKAGES_DIR"
    touch "$OFFLINE_PACKAGES_DIR/.placeholder"
    echo -e "${RED}This is an incomplete distribution and may not work correctly${NC}"
fi

chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"

# Create Python virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
if [ ! -d "$INSTALL_DIR/venv" ]; then
    # Check Python version
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    echo -e "${GREEN}Using Python $PYTHON_VERSION${NC}"
    
    python3 -m venv "$INSTALL_DIR/venv"
    chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/venv"
    echo -e "${GREEN}Virtual environment created.${NC}"
else
    echo -e "${GREEN}Virtual environment already exists.${NC}"
fi

# Activate virtual environment
source "$INSTALL_DIR/venv/bin/activate"

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install --upgrade pip

echo -e "${YELLOW}Installing Python packages...${NC}"
pip3 install --no-index --find-links "$INSTALL_DIR/packages" -r "$INSTALL_DIR/requirements.txt"

echo -e "${YELLOW}Setting Python network capabilities...${NC}"
# Give Python permission to bind to privileged ports for ONVIF discovery
PYTHON_PATH=$(readlink -f $(which python3))
echo -e "${YELLOW}Setting capabilities for Python at: $PYTHON_PATH${NC}"
setcap 'cap_net_bind_service,cap_net_raw+ep' "$PYTHON_PATH" || {
    echo -e "${RED}Failed to set Python capabilities. This may affect ONVIF camera discovery.${NC}"
    echo -e "${RED}Error details: $?${NC}"
}

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

# Create systemd service
echo -e "${YELLOW}Creating systemd service...${NC}"
cat > /etc/systemd/system/amslpr.service << EOL
[Unit]
Description=AMSLPR License Plate Recognition Service
After=network.target multi-user.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$INSTALL_DIR:$SITE_PACKAGES_DIR"
Environment="HAILO_ENABLED=true"
Environment="PYTHONDONTWRITEBYTECODE=1"
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/run_server.py --port 5001
Restart=always
RestartSec=10
TimeoutStartSec=60
TimeoutStopSec=30
StandardOutput=append:/var/log/amslpr/server.log
StandardError=append:/var/log/amslpr/error.log

[Install]
WantedBy=multi-user.target
EOL

# Set proper permissions
chmod 644 /etc/systemd/system/amslpr.service

# Create log directory if it doesn't exist
mkdir -p /var/log/amslpr
chown -R $APP_USER:$APP_GROUP /var/log/amslpr

# Reload systemd and enable/start service
echo -e "${YELLOW}Enabling and starting AMSLPR service...${NC}"
systemctl daemon-reload
systemctl enable amslpr.service
systemctl start amslpr.service

# Check service status
echo -e "${YELLOW}Checking service status...${NC}"
systemctl status amslpr.service

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
        proxy_pass http://127.0.0.1:5001;
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
echo -e "${GREEN}https://$(hostname).local or http://$(hostname -I | awk '{print $1}'):5001${NC}"
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