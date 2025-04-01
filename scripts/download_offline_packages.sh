#!/bin/bash

# Script to download ARM64 packages for offline installation
# This script should be run on a Raspberry Pi or ARM64 system

set -e

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Create directories
mkdir -p packages/offline/apt
mkdir -p packages/offline/pip

# Download APT packages
echo -e "${YELLOW}Downloading APT packages...${NC}"
cd packages/offline/apt

# List of required packages
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

# Download each package
for package in "${PACKAGES[@]}"; do
    echo -e "${YELLOW}Downloading $package...${NC}"
    apt-get download "$package"
done

cd ../../..

# Download Python packages
echo -e "${YELLOW}Downloading Python packages...${NC}"
pip3 download -r requirements.txt -d packages/offline/pip/

echo -e "${GREEN}Package download complete!${NC}"
echo -e "${GREEN}You can now commit the packages to the repository.${NC}"
