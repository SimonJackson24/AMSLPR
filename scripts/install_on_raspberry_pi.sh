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

echo "Installing for user: $APP_USER:$APP_GROUP"

echo "Step 1: Updating system packages..."
apt-get update
apt-get upgrade -y

echo "Step 2: Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3.11-dev \
    git \
    tesseract-ocr \
    libtesseract-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    wget \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev

echo "Step 3: Creating application directory..."
mkdir -p "$INSTALL_DIR"
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"

echo "Step 4: Setting up AMSLPR repository..."

# Check if we're already in the AMSLPR repository
CURRENT_DIR=$(pwd)
if [ -d "$CURRENT_DIR/.git" ] && [ -f "$CURRENT_DIR/scripts/install_on_raspberry_pi.sh" ]; then
    echo "Running from existing AMSLPR repository, using current directory..."
    INSTALL_DIR="$CURRENT_DIR"
    echo "Installation directory set to: $INSTALL_DIR"
else
    # Original repository cloning logic
    echo "Setting up repository in $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "Repository already exists, pulling latest changes..."
        cd "$INSTALL_DIR"
        git pull
    else
        echo "Cloning fresh repository..."
        # Clone from the official AMSLPR repository
        git clone https://github.com/SimonJackson24/AMSLPR.git .
        chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"
    fi
fi

echo "Step 5: Setting up Python virtual environment..."
if [ ! -d "$INSTALL_DIR/venv" ]; then
    # Check Python version
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MAJOR" -eq 3 -a "$PYTHON_MINOR" -lt 10 ]; then
        echo "Error: Python 3.10 or higher is required. Found Python $PYTHON_VERSION"
        echo "Please install Python 3.10 or higher before continuing."
        exit 1
    fi

    echo "Using Python $PYTHON_VERSION"

    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/venv"
fi

echo "Step 6: Installing Python dependencies..."
source "$INSTALL_DIR/venv/bin/activate"
pip install --upgrade pip
echo "Installing Python packages..."
pip install -r "$INSTALL_DIR/requirements.txt"

# Check if TensorFlow was installed successfully
if ! python -c "import tensorflow" &> /dev/null; then
    echo "TensorFlow installation failed. Trying alternative methods automatically..."
    
    # Try installing a newer version
    echo "Attempting to install newer TensorFlow version..."
    pip install tensorflow==2.16.1 &> /dev/null
    
    # Check if that worked
    if ! python -c "import tensorflow" &> /dev/null; then
        echo "Newer version installation failed. Attempting to build from source..."
        
        # Install build dependencies silently
        apt-get update -qq &> /dev/null
        apt-get install -y -qq build-essential git python3-dev python3-pip &> /dev/null
        
        # Install Bazel if not already installed
        if ! command -v bazel &> /dev/null; then
            echo "Installing Bazel (this may take a while)..."
            apt-get install -y -qq apt-transport-https curl gnupg &> /dev/null
            curl -fsSL https://bazel.build/bazel-release.pub.gpg | gpg --dearmor > bazel-archive-keyring.gpg &> /dev/null
            mv bazel-archive-keyring.gpg /usr/share/keyrings/bazel-archive-keyring.gpg &> /dev/null
            echo "deb [arch=amd64 signed-by=/usr/share/keyrings/bazel-archive-keyring.gpg] https://storage.googleapis.com/bazel-apt stable jdk1.8" | tee /etc/apt/sources.list.d/bazel.list &> /dev/null
            apt-get update -qq &> /dev/null && apt-get install -y -qq bazel &> /dev/null
        fi
        
        # Create a temporary directory for building
        BUILD_DIR=$(mktemp -d)
        
        # Clone TensorFlow repository
        echo "Cloning TensorFlow repository..."
        git clone --depth=1 --branch=v2.15.0 https://github.com/tensorflow/tensorflow.git "$BUILD_DIR/tensorflow" &> /dev/null
        
        # Check if clone was successful
        if [ -d "$BUILD_DIR/tensorflow" ]; then
            cd "$BUILD_DIR/tensorflow"
            
            # Create a simple yes-to-all configuration script
            cat > configure_script.sh << 'EOF'
#!/bin/bash
echo -e "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n"
EOF
            chmod +x configure_script.sh
            
            # Run configure with automatic responses
            echo "Configuring TensorFlow build..."
            ./configure_script.sh | ./configure &> /dev/null
            
            # Build TensorFlow
            echo "Building TensorFlow from source (this may take a long time)..."
            bazel build --config=opt --config=noaws --config=nogcp --config=nohdfs --config=nonccl //tensorflow/tools/pip_package:build_pip_package &> /dev/null
            
            # Check if build was successful
            if [ -f "./bazel-bin/tensorflow/tools/pip_package/build_pip_package" ]; then
                # Build the pip package
                echo "Creating TensorFlow package..."
                ./bazel-bin/tensorflow/tools/pip_package/build_pip_package "$BUILD_DIR/tensorflow_pkg" &> /dev/null
                
                # Install the pip package
                echo "Installing TensorFlow from built package..."
                pip install "$BUILD_DIR"/tensorflow_pkg/tensorflow-*.whl &> /dev/null
            fi
            
            cd - &> /dev/null
        fi
        
        # Clean up
        rm -rf "$BUILD_DIR"
        
        # If TensorFlow is still not installed, try TensorFlow Lite
        if ! python -c "import tensorflow" &> /dev/null; then
            echo "Building from source failed. Installing TensorFlow Lite as fallback..."
            pip install tflite-runtime &> /dev/null
            
            if python -c "import tflite_runtime" &> /dev/null; then
                echo "TensorFlow Lite installed successfully as fallback."
            else
                echo "WARNING: Neither TensorFlow nor TensorFlow Lite could be installed."
                echo "The system will continue with installation, but some functionality may be limited."
            fi
        else
            echo "TensorFlow built and installed successfully from source."
        fi
    else
        echo "Newer TensorFlow version installed successfully."
    fi
fi

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
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MAJOR" -eq 3 -a "$PYTHON_MINOR" -lt 10 ]; then
            echo "Error: Python 3.10 or higher is required. Found Python $PYTHON_VERSION"
            echo "Please install Python 3.10 or higher before continuing."
            exit 1
        fi

        echo "Using Python $PYTHON_VERSION"

        HAILO_WHEEL=$(ls /opt/hailo/packages/hailo*.whl | head -1)
        HAILO_WHEEL_PYTHON_VERSION=$(basename "$HAILO_WHEEL" | grep -oP "cp\K\d+" | head -1)
        
        echo "Python version: $PYTHON_VERSION"
        echo "Hailo wheel Python version: $HAILO_WHEEL_PYTHON_VERSION"
        
        echo "Installing Hailo wheel for Python $PYTHON_VERSION..."
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
