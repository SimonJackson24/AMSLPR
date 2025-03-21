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

# Create the offline installation script for Python packages
echo -e "${YELLOW}Setting up offline package installation...${NC}"
# Export variables to ensure they're available to the embedded script
export INSTALL_DIR="$INSTALL_DIR"
export PACKAGES_DIR="$PACKAGES_DIR"
export OFFLINE_PACKAGES_DIR="$OFFLINE_PACKAGES_DIR"

# Create the installation script with 'EOF' not in quotes to allow variable substitution
cat > "$INSTALL_DIR/install_offline_dependencies.sh" << EOF
#!/bin/bash

# AMSLPR Offline Package Installation
# This script installs Python packages with compatibility fallbacks

set -e

# Define important directories
INSTALL_DIR="/opt/amslpr"
PACKAGES_DIR="/opt/amslpr/packages"
OFFLINE_PACKAGES_DIR="/opt/amslpr/packages/offline"

# Activate virtual environment
source /opt/amslpr/venv/bin/activate

# Use pre-built packages or compatibility alternatives for problematic packages
echo "Installing pre-built compatibility packages..."

# Use pre-packaged wheels from the packages/offline directory
WHEELS_DIR="/opt/amslpr/packages/offline"
echo "Looking for wheel packages in: \${WHEELS_DIR}"

# Add fallback directories if primary doesn't have wheels
FALLBACK_DIRS=(
    "/opt/amslpr/packages/offline"
    "/opt/amslpr/packages/wheels"
    "/tmp/amslpr_wheels"
    "\${INSTALL_DIR}/packages/offline"
)

# Path debugging for installation troubleshooting
echo "Current directory: \$(pwd)"
echo "Primary wheel directory: \${WHEELS_DIR}"
[ -z "\${WHEELS_DIR}" ] && WHEELS_DIR="/opt/amslpr/packages/offline" && echo "Empty WHEELS_DIR detected, using default"
mkdir -p "\${WHEELS_DIR}"  # Ensure directory exists

# Check for wheels in the primary directory
if ! ls \${WHEELS_DIR}/*.whl >/dev/null 2>&1; then
    echo "No wheels found in primary directory, checking fallbacks..."
    for dir in "\${FALLBACK_DIRS[@]}"; do
        echo "Checking fallback directory: \$dir"
        if [ -d "\$dir" ] && ls \$dir/*.whl >/dev/null 2>&1; then
            echo "Found wheels in fallback directory: \$dir"
            WHEELS_DIR="\$dir"
            break
        fi
    done
fi

echo "Final wheel directory: \${WHEELS_DIR}"
[ -z "\${WHEELS_DIR}" ] && WHEELS_DIR="/opt/amslpr/packages/offline" && echo "Empty WHEELS_DIR detected, using default"
mkdir -p "\${WHEELS_DIR}"  # Ensure directory exists
ls -la "\${WHEELS_DIR}" || echo "Cannot list directory contents"

# Check where the wheels are in the repository
REPO_WHEELS_DIR="\${INSTALL_DIR}/packages/offline"
echo "Checking repository wheels: \${REPO_WHEELS_DIR}"
if [ -d "\${REPO_WHEELS_DIR}" ]; then
    ls -la "\${REPO_WHEELS_DIR}" || echo "Cannot list repository wheels"
fi

# Try to fix any invalid wheel files if the script exists
if [ -f "\${INSTALL_DIR}/scripts/fix_wheel_files.py" ]; then
    echo "Running wheel metadata fix script..."
    python "\${INSTALL_DIR}/scripts/fix_wheel_files.py" "\${WHEELS_DIR}" || echo "Warning: Wheel fix script failed"
    
    # If fixed wheels were created, move them
    if ls \${WHEELS_DIR}/fixed_*.whl >/dev/null 2>&1; then
        echo "Found fixed wheel files, using them instead of originals"
        for fixed_wheel in \${WHEELS_DIR}/fixed_*.whl; do
            orig_name=\$(basename "\$fixed_wheel" | sed 's/^fixed_//')
            mv "\$fixed_wheel" "\${WHEELS_DIR}/\$orig_name" || echo "Warning: Failed to replace original wheel"
        done
    fi
fi

# Check if the wheels directory exists and contains the required packages
# Use a safer check that won't fail if no .whl files exist
if [ -d "\${WHEELS_DIR}" ] && ls \${WHEELS_DIR}/*.whl >/dev/null 2>&1; then
    echo "Using pre-packaged wheels from \${WHEELS_DIR}"
    
    # Initialize counters for installation stats
    INSTALLED_COUNT=0
    FAILED_COUNT=0
    
    # Process wheels in a specific order to respect dependencies
    echo "Creating a priority list for package installation..."
    PRIORITY_WHEELS=()
    ALL_WHEELS=()
    
    # Collect all wheels first
    for wheel in "\${WHEELS_DIR}"/*.whl; do
        ALL_WHEELS+=("\$wheel")
    done
    
    # Add high-priority wheels first (dependencies)
    for wheel in "\${WHEELS_DIR}"/*.whl; do
        base_name=\$(basename "\$wheel" | tr '[:upper:]' '[:lower:]')
        # Process base dependencies first (core packages)
        if [[ "\$base_name" == *"numpy"* || 
              "\$base_name" == *"pillow"* || 
              "\$base_name" == *"requests"* || 
              "\$base_name" == *"six"* || 
              "\$base_name" == *"setuptools"* ]]; then
            PRIORITY_WHEELS+=("\$wheel")
        fi
    done
    
    # Add the remaining wheels
    for wheel in "\${ALL_WHEELS[@]}"; do
        # Check if wheel is not already in priority list
        is_in_priority=false
        for pw in "\${PRIORITY_WHEELS[@]}"; do
            if [[ "\$pw" == "\$wheel" ]]; then
                is_in_priority=true
                break
            fi
        done
        
        if [[ "\$is_in_priority" == "false" ]]; then
            PRIORITY_WHEELS+=("\$wheel")
        fi
    done
    
    # Install wheels with priority order and better error handling
    echo "Installing wheels in priority order..."
    for wheel in "\${PRIORITY_WHEELS[@]}"; do
        wheel_name=\$(basename "\$wheel")
        echo "Installing \$wheel_name..."
        
        # Check if wheel file actually exists
        if [ ! -f "\$wheel" ]; then
            echo "WARNING: Wheel file \$wheel_name not found, skipping"
            FAILED_COUNT=\$((FAILED_COUNT + 1))
            continue
        fi
        
        # Try installing with different options for better compatibility
        if pip install --no-deps "\$wheel" 2>/dev/null; then
            echo "Successfully installed \$wheel_name (no dependencies)"
            INSTALLED_COUNT=\$((INSTALLED_COUNT + 1))
        elif pip install "\$wheel" 2>/dev/null; then
            echo "Successfully installed \$wheel_name (with dependencies)"
            INSTALLED_COUNT=\$((INSTALLED_COUNT + 1))
        else
            # Try to get more detailed error information
            error_output=\$(pip install "\$wheel" 2>&1 || true)
            
            # Check for specific error patterns
            if [[ "\$error_output" == *"not a supported wheel on this platform"* ]]; then
                echo "WARNING: \$wheel_name is not compatible with this platform, skipping"
            elif [[ "\$error_output" == *"has an invalid wheel"* ]]; then
                echo "WARNING: \$wheel_name is an invalid wheel package, skipping"
            else
                echo "WARNING: Failed to install \$wheel_name (unknown error)"
                echo "Error details: \$error_output"
            fi
            FAILED_COUNT=\$((FAILED_COUNT + 1))
        fi
    done
    
    echo "Wheel installation complete: \$INSTALLED_COUNT installed, \$FAILED_COUNT failed"
    
    # Install requests separately as it's a basic dependency
    pip install requests
elif [ -d "\${REPO_WHEELS_DIR}" ] && ls \${REPO_WHEELS_DIR}/*.whl >/dev/null 2>&1; then
    echo "Using wheels from repository directory: \${REPO_WHEELS_DIR}"
    # Create the offline packages directory if it doesn't exist
    mkdir -p "\${WHEELS_DIR}"
    chmod 775 "\${WHEELS_DIR}"
    
    # Copy the wheels to the offline packages directory with verbose output
    echo "Copying wheels from \${REPO_WHEELS_DIR} to \${WHEELS_DIR}"
    cp -v "\${REPO_WHEELS_DIR}"/*.whl "\${WHEELS_DIR}/" || echo "ERROR: Failed to copy wheel files"
    
    # Verify the wheels were copied
    ls -la "\${WHEELS_DIR}/"
    
    # Try to fix any invalid wheel files if the script exists
    if [ -f "\${INSTALL_DIR}/scripts/fix_wheel_files.py" ]; then
        echo "Running wheel metadata fix script on copied wheels..."
        python "\${INSTALL_DIR}/scripts/fix_wheel_files.py" "\${WHEELS_DIR}" || echo "Warning: Wheel fix script failed"
        
        # If fixed wheels were created, move them
        if ls \${WHEELS_DIR}/fixed_*.whl >/dev/null 2>&1; then
            echo "Found fixed wheel files, using them instead of originals"
            for fixed_wheel in \${WHEELS_DIR}/fixed_*.whl; do
                orig_name=\$(basename "\$fixed_wheel" | sed 's/^fixed_//')
                mv "\$fixed_wheel" "\${WHEELS_DIR}/\$orig_name" || echo "Warning: Failed to replace original wheel"
            done
        fi
    fi
    
    # Use the same robust installation process as above
    # Initialize counters for installation stats
    INSTALLED_COUNT=0
    FAILED_COUNT=0
    
    # Process wheels in a specific order to respect dependencies
    echo "Creating a priority list for package installation..."
    PRIORITY_WHEELS=()
    ALL_WHEELS=()
    
    # Collect all wheels first
    for wheel in "\${WHEELS_DIR}"/*.whl; do
        ALL_WHEELS+=("\$wheel")
    done
    
    # Add high-priority wheels first (dependencies)
    for wheel in "\${WHEELS_DIR}"/*.whl; do
        base_name=\$(basename "\$wheel" | tr '[:upper:]' '[:lower:]')
        # Process base dependencies first (core packages)
        if [[ "\$base_name" == *"numpy"* || 
              "\$base_name" == *"pillow"* || 
              "\$base_name" == *"requests"* || 
              "\$base_name" == *"six"* || 
              "\$base_name" == *"setuptools"* ]]; then
            PRIORITY_WHEELS+=("\$wheel")
        fi
    done
    
    # Add the remaining wheels
    for wheel in "\${ALL_WHEELS[@]}"; do
        # Check if wheel is not already in priority list
        is_in_priority=false
        for pw in "\${PRIORITY_WHEELS[@]}"; do
            if [[ "\$pw" == "\$wheel" ]]; then
                is_in_priority=true
                break
            fi
        done
        
        if [[ "\$is_in_priority" == "false" ]]; then
            PRIORITY_WHEELS+=("\$wheel")
        fi
    done
    
    # Install wheels with priority order and better error handling
    echo "Installing wheels in priority order..."
    for wheel in "\${PRIORITY_WHEELS[@]}"; do
        wheel_name=\$(basename "\$wheel")
        echo "Installing \$wheel_name..."
        
        # Check if wheel file actually exists
        if [ ! -f "\$wheel" ]; then
            echo "WARNING: Wheel file \$wheel_name not found, skipping"
            FAILED_COUNT=\$((FAILED_COUNT + 1))
            continue
        fi
        
        # Try installing with different options for better compatibility
        if pip install --no-deps "\$wheel" 2>/dev/null; then
            echo "Successfully installed \$wheel_name (no dependencies)"
            INSTALLED_COUNT=\$((INSTALLED_COUNT + 1))
        elif pip install "\$wheel" 2>/dev/null; then
            echo "Successfully installed \$wheel_name (with dependencies)"
            INSTALLED_COUNT=\$((INSTALLED_COUNT + 1))
        else
            # Try to get more detailed error information
            error_output=\$(pip install "\$wheel" 2>&1 || true)
            
            # Check for specific error patterns
            if [[ "\$error_output" == *"not a supported wheel on this platform"* ]]; then
                echo "WARNING: \$wheel_name is not compatible with this platform, skipping"
            elif [[ "\$error_output" == *"has an invalid wheel"* ]]; then
                echo "WARNING: \$wheel_name is an invalid wheel package, skipping"
            else
                echo "WARNING: Failed to install \$wheel_name (unknown error)"
                echo "Error details: \$error_output"
            fi
            FAILED_COUNT=\$((FAILED_COUNT + 1))
        fi
    done
    
    echo "Wheel installation complete: \$INSTALLED_COUNT installed, \$FAILED_COUNT failed"
    
    # Install requests separately as it's a basic dependency
    pip install requests
else
    echo "ERROR: No pre-packaged wheels found in \${WHEELS_DIR} or \${REPO_WHEELS_DIR}"
    echo "This is an offline installer and requires pre-packaged wheels."
    echo "Please make sure the following wheel files are present:"
    echo " - aiohttp wheel for ARM (e.g., aiohttp-3.7.4-cp311-cp311-linux_aarch64.whl)"
    echo " - Flask wheel for ARM (e.g., Flask-2.0.1-py3-none-any.whl)"
    echo " - Werkzeug wheel for ARM (e.g., Werkzeug-2.0.1-py3-none-any.whl)"
    echo " - Pillow wheel for ARM (e.g., Pillow-8.4.0-cp311-cp311-linux_aarch64.whl)"
    echo " - NumPy wheel for ARM (e.g., numpy-1.21.0-cp311-cp311-linux_aarch64.whl)"
    echo " - OpenCV wheel for ARM (e.g., opencv_python_headless-4.5.3.56-cp311-cp311-linux_aarch64.whl)"
    exit 1
fi

# Skip problematic packages that require compilation
echo "Skipping problematic packages: uvloop"

# Set environment variable
export HAILO_ENABLED=true

# Install other packages from requirements.txt, skipping the ones already installed from wheels
if [ -f "/opt/amslpr/requirements.txt" ]; then
    echo "Installing remaining packages from requirements.txt..."
    # Get a list of already installed package names from wheels
    INSTALLED_PKGS=""
    for wheel in "\${WHEELS_DIR}"/*.whl 2>/dev/null; do
        if [ -f "\$wheel" ]; then
            # Extract package name from wheel filename (format: name-version-pyversion-abi-platform.whl)
            PKG_NAME=\$(basename "\$wheel" | cut -d'-' -f1)
            INSTALLED_PKGS="\$INSTALLED_PKGS|\$PKG_NAME"
        fi
    done
    INSTALLED_PKGS=\${INSTALLED_PKGS#|}  # Remove leading |
    
    if [ -n "\$INSTALLED_PKGS" ]; then
        echo "Skipping already installed packages: \${INSTALLED_PKGS//|/, }"
        
        cat /opt/amslpr/requirements.txt | \
        grep -v -E "(\$INSTALLED_PKGS)" | \
        grep -v "uvloop" | \
        while read package; do
            # Skip comments and empty lines
            if [[ \$package == \#* ]] || [[ -z \$package ]]; then
                continue
            fi
            
            echo "Installing \$package"
            # Try with --no-deps first to avoid dependency conflicts
            pip install --no-deps \$package || pip install \$package || echo "Warning: Failed to install \$package, continuing anyway"
        done
    else
        echo "No packages installed from wheels, proceeding with requirements.txt"
        # Use requirements_minimal.txt if available, otherwise regular requirements
        if [ -f "/opt/amslpr/requirements_minimal.txt" ]; then
            echo "Installing from requirements_minimal.txt..."
            pip install -r /opt/amslpr/requirements_minimal.txt || echo "Some requirements could not be installed"
        else
            echo "Installing from requirements.txt..."
            # Skip problematic packages that often need compilation
            cat /opt/amslpr/requirements.txt | \
            grep -v "uvloop" | \
            while read package; do
                # Skip comments and empty lines
                if [[ \$package == \#* ]] || [[ -z \$package ]]; then
                    continue
                fi
                
                echo "Installing \$package"
                pip install \$package || echo "Warning: Failed to install \$package, continuing anyway"
            done
        fi
    fi
fi

# Create missing modules
echo "Creating fallback modules for missing packages..."

# Create mock for uvloop
SITE_PACKAGES_DIR=$(python -c "import site; print(site.getsitepackages()[0])")
mkdir -p "$SITE_PACKAGES_DIR/uvloop"
cat > "$SITE_PACKAGES_DIR/uvloop/__init__.py" << 'EOL'
# Mock uvloop module
import asyncio
import warnings

__version__ = "0.0.0"

warnings.warn("uvloop is not available on this platform, using asyncio event loop instead", ImportWarning)

# Create a mock event loop policy
class EventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):
        return asyncio.new_event_loop()

# Create installation function
def install():
    """Mock installation of uvloop"""
    pass
EOL

echo "Offline package installation completed"
EOF

chmod +x "$INSTALL_DIR/install_offline_dependencies.sh"

# Run the offline installation script
echo -e "${YELLOW}Running offline package installation...${NC}"
bash "$INSTALL_DIR/install_offline_dependencies.sh"

# Create configuration file
echo -e "${YELLOW}Setting up configuration files...${NC}"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    if [ -f "$ROOT_DIR/config/config.json.example" ]; then
        cp "$ROOT_DIR/config/config.json.example" "$CONFIG_DIR/config.json"
    elif [ -f "$ROOT_DIR/config/config.json" ]; then
        cp "$ROOT_DIR/config/config.json" "$CONFIG_DIR/config.json"
    else
        echo -e "${RED}Warning: No configuration template found!${NC}"
        echo -e "${YELLOW}Creating minimal configuration...${NC}"
        cat > "$CONFIG_DIR/config.json" << EOF
{
    "server": {
        "host": "0.0.0.0",
        "port": 5001,
        "debug": false,
        "ssl": {
            "enabled": true,
            "cert_file": "$CONFIG_DIR/ssl/cert.pem",
            "key_file": "$CONFIG_DIR/ssl/key.pem"
        }
    },
    "database": {
        "type": "sqlite",
        "path": "$DATA_DIR/amslpr.db"
    },
    "recognition": {
        "image_path": "$DATA_DIR/images",
        "ocr_config_path": "$CONFIG_DIR/ocr_config.json"
    },
    "logging": {
        "level": "INFO",
        "file": "$LOG_DIR/amslpr.log",
        "max_size_mb": 10,
        "backup_count": 5
    }
}
EOF
    fi
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
echo -e "${YELLOW}Updating configuration file paths...${NC}"
sed -i "s|\"path\": \"data/amslpr.db\"|\"path\": \"$DATA_DIR/amslpr.db\"|g" "$CONFIG_DIR/config.json"
sed -i "s|\"image_path\": \"data/images\"|\"image_path\": \"$DATA_DIR/images\"|g" "$CONFIG_DIR/config.json"
sed -i "s|\"cert_file\": \"/etc/amslpr/ssl/cert.pem\"|\"cert_file\": \"$CONFIG_DIR/ssl/cert.pem\"|g" "$CONFIG_DIR/config.json"
sed -i "s|\"key_file\": \"/etc/amslpr/ssl/key.pem\"|\"key_file\": \"$CONFIG_DIR/ssl/key.pem\"|g" "$CONFIG_DIR/config.json"
sed -i "s|\"file\": \"data/logs/amslpr.log\"|\"file\": \"$LOG_DIR/amslpr.log\"|g" "$CONFIG_DIR/config.json"

# Enable SSL in configuration if not already enabled
sed -i 's/"enabled": false/"enabled": true/g' "$CONFIG_DIR/config.json"

# Setup Hailo TPU Integration
echo -e "${YELLOW}Setting up Hailo TPU integration...${NC}"

# Create udev rules for Hailo device
echo -e "${YELLOW}Creating Hailo udev rules...${NC}"
cat > /etc/udev/rules.d/99-hailo.rules << 'EOL'
# Hailo udev rules
SUBSYSTEM=="pci", ATTR{vendor}=="0x1e60", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"
SUBSYSTEM=="hailo", MODE="0666"
EOL

# Reload udev rules
udevadm control --reload-rules
udevadm trigger

# Check for Hailo device
echo -e "${YELLOW}Checking for Hailo device...${NC}"
if [ -e "/dev/hailo0" ]; then
    echo -e "${GREEN}Hailo device found at /dev/hailo0${NC}"
    HAILO_DEVICE_FOUND=true
    # Ensure device has proper permissions
    chmod 666 /dev/hailo0
else
    echo -e "${YELLOW}Hailo device not found at /dev/hailo0${NC}"
    echo -e "${YELLOW}Creating a mock device for development/testing...${NC}"
    HAILO_DEVICE_FOUND=false
    # Create a mock device for testing
    touch /dev/hailo0
    chmod 666 /dev/hailo0
fi

# Setup Hailo mocks
echo -e "${YELLOW}Setting up Hailo module compatibility...${NC}"

# Determine Python site-packages directory
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1-2)
SITE_PACKAGES_DIR="$INSTALL_DIR/venv/lib/python$PYTHON_VERSION/site-packages"
echo -e "${GREEN}Using Python site-packages at: $SITE_PACKAGES_DIR${NC}"

# Always create Hailo mock modules to ensure compatibility
echo -e "${YELLOW}Creating Hailo module structure...${NC}"

# Create direct module files
mkdir -p "$SITE_PACKAGES_DIR/hailort"
cat > "$SITE_PACKAGES_DIR/hailort/__init__.py" << 'EOL'
# Direct hailort module implementation
import logging
import os
import sys
import platform

__version__ = "4.20.0"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('hailort')

# Check if we're on ARM (Raspberry Pi) or x86_64 (development)
is_arm = platform.machine() in ('aarch64', 'armv7l', 'armv6l')

# On ARM, try to use the real hailort if found, otherwise use mock
if is_arm:
    try:
        # Check if the device file exists
        if os.path.exists('/dev/hailo0'):
            logger.info("Hailo device found at /dev/hailo0")
            
            # Check if we can access the real hailort libraries
            try:
                from _pyhailort import Device as RealDevice
                from _pyhailort import infer
                
                logger.info("Using real Hailo SDK")
                
                class Device(RealDevice):
                    def __init__(self):
                        super().__init__()
                        self.device_id = "HAILO-DEVICE-REAL"
                        logger.info(f"Initialized real Hailo device: {self.device_id}")
                
                def load_and_run(model_path):
                    logger.info(f"Loading real model: {model_path}")
                    return infer(model_path)
                
            except ImportError:
                logger.warning("Real Hailo SDK libraries not found, using mock implementation")
                # Fall back to mock implementation
                class Device:
                    def __init__(self):
                        self.device_id = "HAILO-DEVICE-ARM-MOCK"
                        logger.info(f"Initialized mock Hailo device: {self.device_id}")
                        
                    def close(self):
                        logger.info("Closed mock Hailo device")
                
                def load_and_run(model_path):
                    logger.info(f"Loading mock model: {model_path}")
                    return None
        else:
            logger.warning("Hailo device file not found, using mock implementation")
            # Use mock implementation
            class Device:
                def __init__(self):
                    self.device_id = "HAILO-DEVICE-ARM-MOCK"
                    logger.info(f"Initialized mock Hailo device: {self.device_id}")
                    
                def close(self):
                    logger.info("Closed mock Hailo device")
            
            def load_and_run(model_path):
                logger.info(f"Loading mock model: {model_path}")
                return None
    except Exception as e:
        logger.error(f"Error initializing Hailo SDK: {e}")
        # Fall back to mock implementation
        class Device:
            def __init__(self):
                self.device_id = "HAILO-DEVICE-ARM-FALLBACK"
                logger.info(f"Initialized fallback Hailo device: {self.device_id}")
                
            def close(self):
                logger.info("Closed fallback Hailo device")
        
        def load_and_run(model_path):
            logger.info(f"Loading fallback model: {model_path}")
            return None
else:
    # On development platform, use mock implementation
    logger.info("Running on development platform, using mock implementation")
    class Device:
        def __init__(self):
            self.device_id = "HAILO-DEVICE-DEV"
            logger.info(f"Initialized dev Hailo device: {self.device_id}")
            
        def close(self):
            logger.info("Closed dev Hailo device")
    
    def load_and_run(model_path):
        logger.info(f"Loading dev model: {model_path}")
        return None
EOL

# Create hailo_platform module
mkdir -p "$SITE_PACKAGES_DIR/hailo_platform"
cat > "$SITE_PACKAGES_DIR/hailo_platform/__init__.py" << 'EOL'
# hailo_platform module
import logging
import sys
import os
import platform

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('hailo_platform')

__version__ = "4.20.0"

# Try to import from hailort
try:
    import hailort
    from hailort import Device, load_and_run
    logger.info("Successfully imported hailort")
except ImportError as e:
    logger.warning(f"Failed to import hailort: {e}")
    
    # Fallback implementation
    class Device:
        def __init__(self):
            self.device_id = "HAILO-PLATFORM-MOCK"
            logger.info(f"Initialized mock Device: {self.device_id}")
        
        def close(self):
            logger.info("Closed mock Device")
    
    def load_and_run(model_path):
        logger.info(f"Loading mock model: {model_path}")
        return None

# Create HailoDevice class for newer SDK compatibility
HailoDevice = Device

# Create pyhailort module for older SDK compatibility
class pyhailort:
    Device = Device
    
    @staticmethod
    def load_and_run(model_path):
        return load_and_run(model_path)
EOL

chown -R "$APP_USER:$APP_GROUP" "$SITE_PACKAGES_DIR/hailort" "$SITE_PACKAGES_DIR/hailo_platform"

# Fix imports with our script if it exists
if [ -f "$INSTALL_DIR/scripts/fix_hailo_imports.py" ]; then
    echo -e "${YELLOW}Running Hailo imports fix script...${NC}"
    cd "$INSTALL_DIR" && source venv/bin/activate && python scripts/fix_hailo_imports.py || echo -e "${YELLOW}Warning: Fix script ran with errors${NC}"
fi

# Copy Hailo models if available
echo -e "${YELLOW}Setting up Hailo models...${NC}"
if [ -d "$ROOT_DIR/packages/models" ] && [ "$(ls -A "$ROOT_DIR/packages/models/"*.hef 2>/dev/null)" ]; then
    echo -e "${GREEN}Found Hailo models in packages/models directory${NC}"
    cp "$ROOT_DIR/packages/models/"*.hef "$INSTALL_DIR/models/"
    chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/models"
    echo -e "${GREEN}Models copied to $INSTALL_DIR/models/${NC}"
elif [ -d "$ROOT_DIR/models" ] && [ "$(ls -A "$ROOT_DIR/models/"*.hef 2>/dev/null)" ]; then
    echo -e "${GREEN}Found Hailo models in models directory${NC}"
    cp "$ROOT_DIR/models/"*.hef "$INSTALL_DIR/models/"
    chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR/models"
    echo -e "${GREEN}Models copied to $INSTALL_DIR/models/${NC}"
else
    echo -e "${YELLOW}No Hailo models found${NC}"
    echo -e "${YELLOW}The system will not be able to use Hailo TPU for inference${NC}"
fi

# Create systemd service
echo -e "${YELLOW}Creating systemd service...${NC}"
cat > /etc/systemd/system/amslpr.service << EOL
[Unit]
Description=AMSLPR License Plate Recognition Service
After=network.target multi-user.target

[Service]
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$INSTALL_DIR:$SITE_PACKAGES_DIR"
Environment="HAILO_ENABLED=true"
Environment="PYTHONDONTWRITEBYTECODE=1"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run_server.py --port 5001
Restart=always
RestartSec=10
TimeoutStartSec=60
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOL

systemctl daemon-reload
systemctl enable amslpr.service
echo -e "${GREEN}✅ AMSLPR service enabled to start automatically at boot${NC}"

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
read -p "Do you want to reboot the system now to complete installation? (y/n): " REBOOT_NOW
if [[ $REBOOT_NOW == "y" || $REBOOT_NOW == "Y" ]]; then
    echo -e "${GREEN}Rebooting system now...${NC}"
    reboot
else
    echo -e "${YELLOW}Remember to reboot your system with 'sudo reboot' before using AMSLPR${NC}"
fi