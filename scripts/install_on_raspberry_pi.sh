#!/bin/bash

set -e

echo "AMSLPR Installation Script for Raspberry Pi with Hailo TPU"
echo "====================================================="
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Please use sudo."
    exit 1
fi

# Set up variables
INSTALL_DIR="/opt/amslpr"
APP_USER="pi"
APP_GROUP="pi"

echo "Step 1: Updating system packages..."
apt-get update
apt-get upgrade -y

echo "Step 2: Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    tesseract-ocr \
    libtesseract-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    wget

echo "Step 3: Creating application directory..."
mkdir -p "$INSTALL_DIR"
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"

echo "Step 4: Cloning AMSLPR repository..."
cd "$INSTALL_DIR"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning fresh repository..."
    # Replace with your actual repository URL
    git clone https://github.com/yourusername/AMSLPR.git .
    chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"
fi

echo "Step 5: Setting up Python virtual environment..."
if [ ! -d "$INSTALL_DIR/venv" ]; then
    # Check Python version
    PYTHON_VERSION=$(python3 --version | cut -d" " -f2 | cut -d"." -f1,2)
    echo "Detected Python version: $PYTHON_VERSION"
    
    # Verify Python 3.11 is available
    if [ "$PYTHON_VERSION" != "3.11" ]; then
        echo "Error: Python 3.11 is required for AMSLPR with Hailo TPU integration."
        echo "Your current Python version is $PYTHON_VERSION"
        echo "Please install Python 3.11 and try again."
        exit 1
    fi
    
    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/venv"
fi

echo "Step 6: Installing Python dependencies..."
source "$INSTALL_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$INSTALL_DIR/requirements.txt"

echo "Step 7: Setting up Hailo TPU..."
echo "Checking for Hailo device..."
if [ -e "/dev/hailo0" ]; then
    echo "Hailo device found at /dev/hailo0"
    echo "Checking for Hailo SDK packages..."
    
    # Create Hailo packages directory if it doesn't exist
    mkdir -p "/opt/hailo/packages"
    
    # Check if Hailo packages are in the project directory
    if [ -d "$INSTALL_DIR/packages/hailo" ] && [ "$(ls -A "$INSTALL_DIR/packages/hailo/" 2>/dev/null)" ]; then
        echo "Found Hailo packages in project directory"
        echo "Copying packages to /opt/hailo/packages/"
        cp "$INSTALL_DIR/packages/hailo/"* "/opt/hailo/packages/"
    fi
    
    # Check if Hailo packages are already downloaded
    HAILO_PACKAGES_COUNT=$(ls -1 /opt/hailo/packages/hailo*.whl 2>/dev/null | wc -l)
    HAILO_DRIVER_COUNT=$(ls -1 /opt/hailo/packages/hailort*.deb 2>/dev/null | wc -l)
    
    if [ "$HAILO_PACKAGES_COUNT" -gt 0 ] && [ "$HAILO_DRIVER_COUNT" -gt 0 ]; then
        echo "Hailo packages found in /opt/hailo/packages/"
        echo "Installing Hailo driver..."
        dpkg -i /opt/hailo/packages/hailort*.deb
        
        echo "Installing Hailo Python packages..."
        # Check Python version to ensure compatibility with Hailo SDK
        PYTHON_VERSION=$(python3 --version | cut -d" " -f2 | cut -d"." -f1,2)
        HAILO_WHEEL=$(ls /opt/hailo/packages/hailo*.whl | head -1)
        HAILO_WHEEL_PYTHON_VERSION=$(basename "$HAILO_WHEEL" | grep -oP "cp\K\d+" | head -1)
        
        echo "Python version: $PYTHON_VERSION"
        echo "Hailo wheel Python version: $HAILO_WHEEL_PYTHON_VERSION"
        
        # Verify Python 3.11 is available
        if [ "$PYTHON_VERSION" != "3.11" ]; then
            echo "Error: Python 3.11 is required for AMSLPR with Hailo TPU integration."
            echo "Your current Python version is $PYTHON_VERSION"
            echo "Please install Python 3.11 and try again."
            exit 1
        fi
        
        echo "Installing Hailo wheel for Python 3.11..."
        pip install /opt/hailo/packages/hailo*.whl
    else
        echo "Hailo packages not found in /opt/hailo/packages/"
        echo "Please download the Hailo SDK packages from the Hailo Developer Zone (https://hailo.ai/developer-zone/)"
        echo "and place them in /opt/hailo/packages/ directory."
        echo "Then run this script again."
        echo ""
        echo "Required packages:"
        echo "1. Hailo Runtime Package (hailort*.deb)"
        echo "2. Hailo Python SDK Wheel Files (hailo*.whl)"
        echo ""
        echo "See docs/raspberry_pi_hailo_setup.md for detailed instructions."
    fi
    
    # Create Hailo models directory
    mkdir -p "$INSTALL_DIR/models"
    chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/models"
    
    # First check if models are included in the packages directory
    echo "Checking for pre-packaged Hailo models..."
    if [ -d "$INSTALL_DIR/packages/models" ] && [ "$(ls -A "$INSTALL_DIR/packages/models/" 2>/dev/null)" ]; then
        echo "Found pre-packaged Hailo models in packages/models directory"
        echo "Copying models to $INSTALL_DIR/models/"
        cp "$INSTALL_DIR/packages/models/"*.hef "$INSTALL_DIR/models/"
        chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/models"
        echo "Pre-packaged models copied successfully"
    else
        # If no pre-packaged models, try to copy from Downloads folder
        echo "Looking for Hailo models in Downloads folder..."
        bash "$INSTALL_DIR/scripts/copy_hailo_models.sh"
        
        # If models are still missing, run the Hailo model download script
        if [ $? -ne 0 ]; then
            echo "Some models are missing, running Hailo model download script..."
            bash "$INSTALL_DIR/scripts/hailo_raspberry_pi_setup.sh"
        fi
    fi
    echo "Hailo TPU setup completed."
else
    echo "Warning: Hailo device not found at /dev/hailo0"
    echo "Please make sure the Hailo TPU is properly connected."
    echo "You can run this script again after connecting the device."
    
    # Still try to set up models even if device is not connected
    echo "Setting up Hailo models anyway..."
    mkdir -p "$INSTALL_DIR/models"
    chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/models"
    
    # First check if models are included in the packages directory
    echo "Checking for pre-packaged Hailo models..."
    if [ -d "$INSTALL_DIR/packages/models" ] && [ "$(ls -A "$INSTALL_DIR/packages/models/" 2>/dev/null)" ]; then
        echo "Found pre-packaged Hailo models in packages/models directory"
        echo "Copying models to $INSTALL_DIR/models/"
        cp "$INSTALL_DIR/packages/models/"*.hef "$INSTALL_DIR/models/"
        chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/models"
        echo "Pre-packaged models copied successfully"
    else
        # If no pre-packaged models, try to copy from Downloads folder
        echo "Looking for Hailo models in Downloads folder..."
        bash "$INSTALL_DIR/scripts/copy_hailo_models.sh"
        
        # If models are still missing, run the Hailo model download script
        if [ $? -ne 0 ]; then
            echo "Some models are missing, running Hailo model download script..."
            bash "$INSTALL_DIR/scripts/hailo_raspberry_pi_setup.sh"
        fi
    fi
fi

echo "Step 8: Creating necessary directories..."
mkdir -p "$INSTALL_DIR/data"
mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/config"
mkdir -p "$INSTALL_DIR/models"
mkdir -p "$INSTALL_DIR/instance/flask_session"

chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/data"
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/logs"
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/config"
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/models"
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/instance"

touch "$INSTALL_DIR/config/users.json"
chmod 666 "$INSTALL_DIR/config/users.json"

echo "Step 9: Setting up systemd service..."
cat > /etc/systemd/system/amslpr.service << EOL
[Unit]
Description=AMSLPR License Plate Recognition Service
After=network.target

[Service]
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
Environment="HAILO_ENABLED=true"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run_server.py --port 5001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

systemctl daemon-reload
systemctl enable amslpr.service

echo "Step 10: Running Hailo TPU setup script..."
# Run the Hailo setup script to configure OCR
su - "$APP_USER" -c "cd $INSTALL_DIR && source venv/bin/activate && python scripts/enable_hailo_tpu.py --auto-approve"

# Verify Hailo installation
echo "Step 11: Verifying Hailo TPU installation..."
su - "$APP_USER" -c "cd $INSTALL_DIR && source venv/bin/activate && python scripts/verify_hailo_installation.py"
VERIFY_RESULT=$?

if [ $VERIFY_RESULT -ne 0 ]; then
    echo "Warning: Hailo TPU verification found issues. The system will still work but may have limited functionality."
    echo "Please check the verification output and follow the instructions in docs/raspberry_pi_hailo_setup.md"
fi

echo ""
echo "Installation completed successfully!"
echo "You can start the service with: sudo systemctl start amslpr"
echo "Check status with: sudo systemctl status amslpr"
echo "View logs with: sudo journalctl -u amslpr -f"
echo ""
echo "The application will be available at: http://$(hostname -I | awk '{print $1}'):5001"
echo ""

# Ask if user wants to start the service now
read -p "Do you want to start the AMSLPR service now? (y/n): " START_SERVICE
if [[ $START_SERVICE == "y" || $START_SERVICE == "Y" ]]; then
    systemctl start amslpr
    echo "Service started. Check status with: sudo systemctl status amslpr"
else
    echo "You can start the service later with: sudo systemctl start amslpr"
fi
