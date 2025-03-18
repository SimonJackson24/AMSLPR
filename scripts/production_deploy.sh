#!/bin/bash

# AMSLPR Production Deployment Script
# This script automates the deployment of AMSLPR in a production environment

set -e

# Text colors
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Print header
echo -e "${BLUE}===========================================================${NC}"
echo -e "${BLUE}       AMSLPR Production Deployment Script               ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Configuration variables
INSTALL_DIR="/opt/amslpr"
DATA_DIR="/var/lib/amslpr"
LOG_DIR="/var/log/amslpr"
CONFIG_DIR="/etc/amslpr"
NGINX_CONF="/etc/nginx/sites-available/amslpr"
SSL_DIR="/etc/ssl/amslpr"
SYSTEMD_SERVICE="/etc/systemd/system/amslpr.service"

# Parse command line arguments
DEPLOY_TYPE="standard"
GENERATE_SSL=true
INSTALL_DEPS=true
CREATE_ADMIN=true
CONFIG_NGINX=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --high-availability)
            DEPLOY_TYPE="high-availability"
            shift
            ;;
        --no-ssl)
            GENERATE_SSL=false
            shift
            ;;
        --no-deps)
            INSTALL_DEPS=false
            shift
            ;;
        --no-admin)
            CREATE_ADMIN=false
            shift
            ;;
        --no-nginx)
            CONFIG_NGINX=false
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --high-availability  Deploy in high-availability mode"
            echo "  --no-ssl             Skip SSL certificate generation"
            echo "  --no-deps            Skip dependency installation"
            echo "  --no-admin           Skip admin user creation"
            echo "  --no-nginx           Skip Nginx configuration"
            echo "  --help               Display this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}Deployment type: ${DEPLOY_TYPE}${NC}"
echo -e "${GREEN}Generate SSL certificates: ${GENERATE_SSL}${NC}"
echo -e "${GREEN}Install dependencies: ${INSTALL_DEPS}${NC}"
echo -e "${GREEN}Create admin user: ${CREATE_ADMIN}${NC}"
echo -e "${GREEN}Configure Nginx: ${CONFIG_NGINX}${NC}"
echo

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Install dependencies
if [ "$INSTALL_DEPS" = true ]; then
    echo -e "${YELLOW}Step 1: Installing dependencies...${NC}"
    
    # Update package lists
    apt-get update
    
    # Install required packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        sqlite3 \
        libsqlite3-dev \
        libopencv-dev \
        python3-opencv \
        openssl \
        git \
        build-essential \
        libffi-dev \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        wget \
        curl \
        llvm \
        libncurses5-dev \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        liblzma-dev
    
    echo -e "${GREEN}Dependencies installed successfully${NC}"
else
    echo -e "${YELLOW}Skipping dependency installation${NC}"
fi

# Step 2: Create directory structure
echo -e "${YELLOW}Step 2: Creating directory structure...${NC}"

mkdir -p "$INSTALL_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$DATA_DIR/metrics"
mkdir -p "$DATA_DIR/backups"
mkdir -p "$DATA_DIR/images"
mkdir -p "$LOG_DIR"
mkdir -p "$LOG_DIR/errors"
mkdir -p "$CONFIG_DIR"
mkdir -p "$SSL_DIR"

echo -e "${GREEN}Directory structure created successfully${NC}"

# Step 3: Copy application files
echo -e "${YELLOW}Step 3: Copying application files...${NC}"

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Copy application files
cp -r "$PROJECT_DIR/src" "$INSTALL_DIR/"
cp -r "$PROJECT_DIR/static" "$INSTALL_DIR/"
cp -r "$PROJECT_DIR/templates" "$INSTALL_DIR/"
cp -r "$PROJECT_DIR/scripts" "$INSTALL_DIR/"
cp "$PROJECT_DIR/requirements.txt" "$INSTALL_DIR/"

# Create a version file
echo "1.0.0" > "$INSTALL_DIR/version.txt"

echo -e "${GREEN}Application files copied successfully${NC}"

# Step 4: Set up Python virtual environment
echo -e "${YELLOW}Step 4: Setting up Python virtual environment...${NC}"

python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$INSTALL_DIR/requirements.txt"
deactivate

echo -e "${GREEN}Python virtual environment set up successfully${NC}"

# Step 5: Generate SSL certificates if needed
if [ "$GENERATE_SSL" = true ]; then
    echo -e "${YELLOW}Step 5: Generating SSL certificates...${NC}"
    
    # Generate SSL certificates
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/amslpr.key" \
        -out "$SSL_DIR/amslpr.crt" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    
    # Set proper permissions
    chmod 600 "$SSL_DIR/amslpr.key"
    chmod 644 "$SSL_DIR/amslpr.crt"
    
    echo -e "${GREEN}SSL certificates generated successfully${NC}"
else
    echo -e "${YELLOW}Skipping SSL certificate generation${NC}"
fi

# Step 6: Create configuration file
echo -e "${YELLOW}Step 6: Creating configuration file...${NC}"

cat > "$CONFIG_DIR/config.json" << EOF
{
    "server": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": false,
        "ssl": {
            "enabled": true,
            "cert_path": "$SSL_DIR/amslpr.crt",
            "key_path": "$SSL_DIR/amslpr.key"
        }
    },
    "database": {
        "path": "$DATA_DIR/amslpr.db",
        "backup_path": "$DATA_DIR/backups"
    },
    "camera": {
        "default_source": 0,
        "frame_width": 640,
        "frame_height": 480,
        "frame_rate": 10,
        "save_images": true,
        "image_path": "$DATA_DIR/images"
    },
    "recognition": {
        "confidence_threshold": 0.75,
        "min_plate_size": 0.1,
        "max_plate_size": 0.9,
        "processing_interval": 1.0
    },
    "barrier": {
        "enabled": true,
        "gpio_pin": 18,
        "open_time": 5.0
    },
    "logging": {
        "level": "INFO",
        "file_path": "$LOG_DIR/amslpr.log",
        "max_size": 10485760,
        "backup_count": 5
    },
    "monitoring": {
        "enabled": true,
        "log_interval": 300,
        "metrics_path": "$DATA_DIR/metrics",
        "alert_thresholds": {
            "cpu_percent": 80,
            "memory_percent": 80,
            "disk_percent": 90,
            "cpu_temp": 70
        }
    },
    "error_handling": {
        "log_path": "$LOG_DIR/errors",
        "max_log_size": 10485760,
        "backup_count": 5,
        "email_notifications": false,
        "email_config": {
            "server": "smtp.example.com",
            "port": 587,
            "username": "user@example.com",
            "password": "password",
            "from_addr": "amslpr@example.com",
            "to_addrs": ["admin@example.com"]
        }
    },
    "security": {
        "rate_limiting": {
            "enabled": true,
            "requests_per_minute": 100
        },
        "session": {
            "lifetime": 86400,
            "secure": true,
            "httponly": true
        }
    }
}
EOF

echo -e "${GREEN}Configuration file created successfully${NC}"

# Step 7: Configure Nginx if needed
if [ "$CONFIG_NGINX" = true ]; then
    echo -e "${YELLOW}Step 7: Configuring Nginx...${NC}"
    
    # Create Nginx configuration
    cat > "$NGINX_CONF" << EOF
server {
    listen 80;
    server_name _;
    
    # Redirect all HTTP requests to HTTPS
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name _;
    
    ssl_certificate $SSL_DIR/amslpr.crt;
    ssl_certificate_key $SSL_DIR/amslpr.key;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-XSS-Protection "1; mode=block";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'";
    
    # Proxy settings
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # Static files
    location /static/ {
        alias $INSTALL_DIR/static/;
        expires 30d;
    }
    
    # Captured images
    location /images/ {
        alias $DATA_DIR/images/;
        expires 1d;
    }
}
EOF
    
    # Enable the site
    ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
    
    # Test Nginx configuration
    nginx -t
    
    # Restart Nginx
    systemctl restart nginx
    
    echo -e "${GREEN}Nginx configured successfully${NC}"
else
    echo -e "${YELLOW}Skipping Nginx configuration${NC}"
fi

# Step 8: Create systemd service
echo -e "${YELLOW}Step 8: Creating systemd service...${NC}"

cat > "$SYSTEMD_SERVICE" << EOF
[Unit]
Description=AMSLPR License Plate Recognition System
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python -m src.app --config $CONFIG_DIR/config.json
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable the service to start at boot
systemctl enable amslpr.service

echo -e "${GREEN}Systemd service created successfully${NC}"

# Step 9: Initialize the database
echo -e "${YELLOW}Step 9: Initializing database...${NC}"

# Activate virtual environment
source "$INSTALL_DIR/venv/bin/activate"

# Initialize the database
python -c "from src.utils.database import init_db; init_db('$CONFIG_DIR/config.json')"

# Create admin user if needed
if [ "$CREATE_ADMIN" = true ]; then
    # Generate a random password
    ADMIN_PASSWORD=$(openssl rand -base64 12)
    
    # Create admin user
    python -c "from src.utils.user_manager import create_user; create_user('admin', '$ADMIN_PASSWORD', 'admin', '$CONFIG_DIR/config.json')"
    
    echo -e "${GREEN}Admin user created with the following credentials:${NC}"
    echo -e "${GREEN}Username: admin${NC}"
    echo -e "${GREEN}Password: $ADMIN_PASSWORD${NC}"
    echo -e "${YELLOW}Please change this password after first login!${NC}"
else
    echo -e "${YELLOW}Skipping admin user creation${NC}"
fi

# Deactivate virtual environment
deactivate

echo -e "${GREEN}Database initialized successfully${NC}"

# Step 10: Set proper permissions
echo -e "${YELLOW}Step 10: Setting proper permissions...${NC}"

# Set ownership
chown -R root:root "$INSTALL_DIR"
chown -R root:root "$CONFIG_DIR"
chown -R www-data:www-data "$DATA_DIR"
chown -R www-data:www-data "$LOG_DIR"

# Set permissions
chmod -R 755 "$INSTALL_DIR"
chmod -R 640 "$CONFIG_DIR/config.json"
chmod -R 755 "$DATA_DIR"
chmod -R 755 "$LOG_DIR"

echo -e "${GREEN}Permissions set successfully${NC}"

# Step 11: Start the service
echo -e "${YELLOW}Step 11: Starting AMSLPR service...${NC}"

systemctl start amslpr.service

# Check if service started successfully
if systemctl is-active --quiet amslpr.service; then
    echo -e "${GREEN}AMSLPR service started successfully${NC}"
else
    echo -e "${RED}Failed to start AMSLPR service${NC}"
    echo -e "${YELLOW}Check logs with: journalctl -u amslpr.service${NC}"
fi

# Final message
echo
echo -e "${BLUE}===========================================================${NC}"
echo -e "${GREEN}AMSLPR has been successfully deployed in production mode!${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo
echo -e "${YELLOW}Access the web interface at: https://$(hostname -I | awk '{print $1}')${NC}"
echo -e "${YELLOW}Admin username: admin${NC}"
if [ "$CREATE_ADMIN" = true ]; then
    echo -e "${YELLOW}Admin password: $ADMIN_PASSWORD${NC}"
fi
echo
echo -e "${BLUE}Configuration files:${NC}"
echo -e "${BLUE}- Main configuration: $CONFIG_DIR/config.json${NC}"
echo -e "${BLUE}- Nginx configuration: $NGINX_CONF${NC}"
echo -e "${BLUE}- Systemd service: $SYSTEMD_SERVICE${NC}"
echo
echo -e "${BLUE}Important directories:${NC}"
echo -e "${BLUE}- Installation directory: $INSTALL_DIR${NC}"
echo -e "${BLUE}- Data directory: $DATA_DIR${NC}"
echo -e "${BLUE}- Log directory: $LOG_DIR${NC}"
echo
echo -e "${YELLOW}For more information, see the documentation in the docs/ directory.${NC}"
echo -e "${YELLOW}If you encounter any issues, check the logs in $LOG_DIR${NC}"
echo

exit 0
