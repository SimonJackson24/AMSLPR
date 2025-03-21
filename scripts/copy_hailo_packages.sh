#!/bin/bash

set -e

echo "Copying Hailo packages to Raspberry Pi"
echo "===================================="
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Please use sudo."
    exit 1
fi

# Set up variables
HAILO_PACKAGES_DIR="/opt/hailo/packages"

# Create Hailo packages directory if it doesn't exist
mkdir -p "$HAILO_PACKAGES_DIR"

# Check if packages exist in the project directory
if [ -d "$(dirname "$0")/../packages/hailo" ]; then
    echo "Found Hailo packages in project directory"
    
    # Copy packages to the Hailo packages directory
    cp "$(dirname "$0")/../packages/hailo/"* "$HAILO_PACKAGES_DIR/"
    
    echo "Packages copied to $HAILO_PACKAGES_DIR"
    ls -la "$HAILO_PACKAGES_DIR"
    
    echo ""
    echo "You can now install the Hailo driver and SDK by running:"
    echo "sudo dpkg -i $HAILO_PACKAGES_DIR/hailort*.deb"
    echo "pip install $HAILO_PACKAGES_DIR/hailo*.whl"
    echo ""
    echo "For detailed instructions, see docs/raspberry_pi_hailo_setup.md"
else
    echo "Error: Hailo packages not found in project directory"
    echo "Please make sure the packages are in the packages/hailo/ directory"
    exit 1
fi
