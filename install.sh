#!/bin/bash

# AMSLPR Installation Script
# This script installs the AMSLPR system on a Raspberry Pi

set -e

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Define installation directories
INSTALL_DIR="/opt/amslpr"
CONFIG_DIR="/etc/amslpr"
LOG_DIR="/var/log/amslpr"
DATA_DIR="/var/lib/amslpr"

# Print header
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}          AMSLPR Installation Script          ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo 

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Check if Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo && ! grep -q "raspberrypi" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}Warning: This system does not appear to be a Raspberry Pi.${NC}"
    echo -e "${YELLOW}The installation may not work correctly.${NC}"
    echo
    read -p "Continue anyway? (y/n) " -n 1 -r
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
    if ! dpkg -l "$1" | grep -q ^ii; then
        echo -e "${YELLOW}Installing $1...${NC}"
        apt-get install -y "$1"
    else
        echo -e "${GREEN}$1 is already installed.${NC}"
    fi
}

# Update package lists
echo -e "${YELLOW}Updating package lists...${NC}"
apt-get update

# Install required packages
echo -e "${YELLOW}Installing required packages...${NC}"
required_packages=("python3" "python3-pip" "python3-venv" "libopencv-dev" "python3-opencv" \
                    "libatlas-base-dev" "libjasper-dev" "libqtgui4" "libqt4-test" \
                    "libhdf5-dev" "libhdf5-serial-dev" "libopenjp2-7" "libtiff5" \
                    "nginx" "openssl" "supervisor")

for package in "${required_packages[@]}"; do
    install_package "$package"
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

# Create Python virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
    echo -e "${GREEN}Virtual environment created.${NC}"
else
    echo -e "${GREEN}Virtual environment already exists.${NC}"
fi

# Activate virtual environment
source "$INSTALL_DIR/venv/bin/activate"

# Copy application files
echo -e "${YELLOW}Copying application files...${NC}"
cp -r src "$INSTALL_DIR/"
cp -r docs "$INSTALL_DIR/"
cp -r tests "$INSTALL_DIR/"
cp run_tests.py "$INSTALL_DIR/"

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Create configuration file
echo -e "${YELLOW}Creating configuration file...${NC}"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cp config/config.json.example "$CONFIG_DIR/config.json"
    echo -e "${GREEN}Configuration file created.${NC}"
else
    echo -e "${GREEN}Configuration file already exists.${NC}"
fi

# Generate SSL certificate if it doesn't exist
if [ ! -f "$CONFIG_DIR/ssl/cert.pem" ] || [ ! -f "$CONFIG_DIR/ssl/key.pem" ]; then
    echo -e "${YELLOW}Generating SSL certificate...${NC}"
    openssl req -x509 -newkey rsa:2048 -keyout "$CONFIG_DIR/ssl/key.pem" -out "$CONFIG_DIR/ssl/cert.pem" \
        -days 365 -nodes -subj "/CN=amslpr.local"
    echo -e "${GREEN}SSL certificate generated.${NC}"
else
    echo -e "${GREEN}SSL certificate already exists.${NC}"
fi

# Update configuration file with correct paths
echo -e "${YELLOW}Updating configuration file...${NC}"
sed -i "s|\"path\": \"data/amslpr.db\"|\"path\": \"$DATA_DIR/amslpr.db\"|g" "$CONFIG_DIR/config.json"
sed -i "s|\"image_path\": \"data/images\"|\"image_path\": \"$DATA_DIR/images\"|g" "$CONFIG_DIR/config.json"
sed -i "s|\"cert_file\": \"/etc/amslpr/ssl/cert.pem\"|\"cert_file\": \"$CONFIG_DIR/ssl/cert.pem\"|g" "$CONFIG_DIR/config.json"
sed -i "s|\"key_file\": \"/etc/amslpr/ssl/key.pem\"|\"key_file\": \"$CONFIG_DIR/ssl/key.pem\"|g" "$CONFIG_DIR/config.json"
sed -i "s|\"file\": \"data/logs/amslpr.log\"|\"file\": \"$LOG_DIR/amslpr.log\"|g" "$CONFIG_DIR/config.json"

# Enable SSL in configuration
sed -i 's/"enabled": false/"enabled": true/g' "$CONFIG_DIR/config.json"

# Create systemd service
echo -e "${YELLOW}Creating systemd service...${NC}"
cp config/amslpr.service /etc/systemd/system/
sed -i "s|/opt/amslpr|$INSTALL_DIR|g" /etc/systemd/system/amslpr.service

# Set correct permissions
echo -e "${YELLOW}Setting permissions...${NC}"
chown -R pi:pi "$INSTALL_DIR"
chown -R pi:pi "$DATA_DIR"
chown -R pi:pi "$LOG_DIR"
chmod -R 755 "$INSTALL_DIR"
chmod -R 755 "$DATA_DIR"
chmod -R 755 "$LOG_DIR"
chmod 644 /etc/systemd/system/amslpr.service

# Configure Nginx
echo -e "${YELLOW}Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/amslpr << EOF
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
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/amslpr /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t

# Enable and start services
echo -e "${YELLOW}Enabling and starting services...${NC}"
systemctl daemon-reload
systemctl enable amslpr.service
systemctl enable nginx
systemctl restart nginx
systemctl start amslpr.service

# Create initial database
echo -e "${YELLOW}Creating initial database...${NC}"
if [ ! -f "$DATA_DIR/amslpr.db" ]; then
    # Run database initialization script
    source "$INSTALL_DIR/venv/bin/activate"
    python -c "from src.database.db_manager import DatabaseManager; DatabaseManager({'type': 'sqlite', 'path': '$DATA_DIR/amslpr.db'}).init_db()"
    echo -e "${GREEN}Database created.${NC}"
else
    echo -e "${GREEN}Database already exists.${NC}"
fi

# Create default admin user
echo -e "${YELLOW}Creating default admin user...${NC}"
source "$INSTALL_DIR/venv/bin/activate"
python -c "from src.utils.user_management import UserManager; from src.database.db_manager import DatabaseManager; UserManager(DatabaseManager({'type': 'sqlite', 'path': '$DATA_DIR/amslpr.db'})).add_user('admin', 'admin', 'admin@example.com', True)"
echo -e "${GREEN}Default admin user created with username 'admin' and password 'admin'.${NC}"
echo -e "${YELLOW}IMPORTANT: Please change the default admin password immediately after installation!${NC}"

# Installation complete
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}          AMSLPR Installation Complete          ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo 
echo -e "${GREEN}The AMSLPR system has been installed successfully.${NC}"
echo -e "${GREEN}You can access the web interface at:${NC}"
echo -e "${GREEN}https://$(hostname).local${NC}"
echo 
echo -e "${YELLOW}Default admin credentials:${NC}"
echo -e "${YELLOW}Username: admin${NC}"
echo -e "${YELLOW}Password: admin${NC}"
echo 
echo -e "${RED}IMPORTANT: Please change the default admin password immediately!${NC}"
echo 

# Exit virtual environment
deactivate
