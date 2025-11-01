#!/bin/bash

set -e

echo "Hailo SDK Auto-Download Script for VisiGate"
echo "======================================="
echo ""

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create packages directory
PACKAGES_DIR="$PROJECT_ROOT/packages/hailo"
mkdir -p "$PACKAGES_DIR"

echo "Step 1: Installing dependencies..."
apt-get update
apt-get install -y wget curl jq

echo "Step 2: Checking system architecture..."
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

if [[ "$ARCH" == "aarch64" || "$ARCH" == "armv7l" ]]; then
    echo "ARM architecture detected, downloading ARM-compatible packages..."
    
    # Download Hailo SDK for ARM
    echo "Downloading Hailo SDK packages for ARM..."
    
    # Hailo Runtime
    echo "Downloading Hailo Runtime package..."
    wget -O "$PACKAGES_DIR/hailort_4.16.0_arm64.deb" \
        "https://github.com/hailo-ai/hailort/releases/download/4.16.0/hailort_4.16.0_arm64.deb" || {
        echo "Failed to download Hailo Runtime package"
        echo "Please download it manually from the Hailo Developer Zone"
    }
    
    # Hailo Python SDK - Try different versions for compatibility
    echo "Downloading Hailo Python SDK wheels..."
    
    # Try multiple Python versions to ensure compatibility
    for pyver in cp310 cp311 cp39; do
        echo "Trying Python version: $pyver"
        wget -O "$PACKAGES_DIR/hailo_platform-4.16.0-${pyver}-${pyver}-linux_aarch64.whl" \
            "https://github.com/hailo-ai/hailort/releases/download/4.16.0/hailo_platform-4.16.0-${pyver}-${pyver}-linux_aarch64.whl" || {
            echo "Failed to download Hailo Python SDK wheel for $pyver"
            continue
        }
        echo "Successfully downloaded SDK for Python $pyver"
    done
    
    # Try older SDK versions if the latest doesn't work
    if [ ! -f "$PACKAGES_DIR/hailo_platform-"*".whl" ]; then
        echo "Trying older SDK versions..."
        for version in 4.15.0 4.14.0 4.13.0; do
            echo "Trying version $version"
            wget -O "$PACKAGES_DIR/hailo_platform-${version}-cp310-cp310-linux_aarch64.whl" \
                "https://github.com/hailo-ai/hailort/releases/download/${version}/hailo_platform-${version}-cp310-cp310-linux_aarch64.whl" || continue
            echo "Successfully downloaded SDK version $version"
            break
        done
    fi
    
    echo "Downloading Hailo Python API wheel..."
    wget -O "$PACKAGES_DIR/hailo_api-4.16.0-py3-none-any.whl" \
        "https://github.com/hailo-ai/hailort/releases/download/4.16.0/hailo_api-4.16.0-py3-none-any.whl" || {
        echo "Failed to download Hailo Python API wheel"
        echo "Please download it manually from the Hailo Developer Zone"
    }
    
    echo "Downloading Hailo Python SDK for TensorFlow wheel..."
    wget -O "$PACKAGES_DIR/hailo_tf_api-4.16.0-py3-none-any.whl" \
        "https://github.com/hailo-ai/hailort/releases/download/4.16.0/hailo_tf_api-4.16.0-py3-none-any.whl" || {
        echo "Failed to download Hailo Python SDK for TensorFlow wheel"
        echo "Please download it manually from the Hailo Developer Zone"
    }
else
    echo "Non-ARM architecture detected, downloading x86-compatible packages..."
    
    # Download Hailo SDK for x86
    echo "Downloading Hailo SDK packages for x86..."
    
    # Hailo Runtime
    echo "Downloading Hailo Runtime package..."
    wget -O "$PACKAGES_DIR/hailort_4.16.0_amd64.deb" \
        "https://github.com/hailo-ai/hailort/releases/download/4.16.0/hailort_4.16.0_amd64.deb" || {
        echo "Failed to download Hailo Runtime package"
        echo "Please download it manually from the Hailo Developer Zone"
    }
    
    # Hailo Python SDK - Try different versions for compatibility
    echo "Downloading Hailo Python SDK wheels..."
    
    # Try multiple Python versions to ensure compatibility
    for pyver in cp310 cp311 cp39; do
        echo "Trying Python version: $pyver"
        wget -O "$PACKAGES_DIR/hailo_platform-4.16.0-${pyver}-${pyver}-linux_x86_64.whl" \
            "https://github.com/hailo-ai/hailort/releases/download/4.16.0/hailo_platform-4.16.0-${pyver}-${pyver}-linux_x86_64.whl" || {
            echo "Failed to download Hailo Python SDK wheel for $pyver"
            continue
        }
        echo "Successfully downloaded SDK for Python $pyver"
    done
    
    # Try older SDK versions if the latest doesn't work
    if [ ! -f "$PACKAGES_DIR/hailo_platform-"*".whl" ]; then
        echo "Trying older SDK versions..."
        for version in 4.15.0 4.14.0 4.13.0; do
            echo "Trying version $version"
            wget -O "$PACKAGES_DIR/hailo_platform-${version}-cp310-cp310-linux_x86_64.whl" \
                "https://github.com/hailo-ai/hailort/releases/download/${version}/hailo_platform-${version}-cp310-cp310-linux_x86_64.whl" || continue
            echo "Successfully downloaded SDK version $version"
            break
        done
    fi
    
    echo "Downloading Hailo Python API wheel..."
    wget -O "$PACKAGES_DIR/hailo_api-4.16.0-py3-none-any.whl" \
        "https://github.com/hailo-ai/hailort/releases/download/4.16.0/hailo_api-4.16.0-py3-none-any.whl" || {
        echo "Failed to download Hailo Python API wheel"
        echo "Please download it manually from the Hailo Developer Zone"
    }
    
    echo "Downloading Hailo Python SDK for TensorFlow wheel..."
    wget -O "$PACKAGES_DIR/hailo_tf_api-4.16.0-py3-none-any.whl" \
        "https://github.com/hailo-ai/hailort/releases/download/4.16.0/hailo_tf_api-4.16.0-py3-none-any.whl" || {
        echo "Failed to download Hailo Python SDK for TensorFlow wheel"
        echo "Please download it manually from the Hailo Developer Zone"
    }
fi

echo "Step 3: Downloading Hailo models..."

# Create models directory
MODELS_DIR="$PROJECT_ROOT/packages/models"
mkdir -p "$MODELS_DIR"

# Download LPRNet model
echo "Downloading LPRNet Vehicle License Recognition model..."
wget -O "$MODELS_DIR/lprnet_vehicle_license_recognition.hef" \
    "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/HailoNets/LPR/ocr/lprnet/2022-03-09/lprnet.hef" || {
    echo "Failed to download LPRNet model"
    echo "Creating placeholder file..."
    touch "$MODELS_DIR/lprnet_vehicle_license_recognition.hef"
}

# Download YOLOv5m model (placeholder)
echo "NOTE: YOLOv5m model needs to be downloaded from Hailo Developer Zone."
echo "Creating placeholder for YOLOv5m License Plates model..."
touch "$MODELS_DIR/yolov5m_license_plates.hef"

# Download Tiny YOLOv4 model (placeholder)
echo "NOTE: Tiny YOLOv4 model needs to be downloaded from Hailo Developer Zone."
echo "Creating placeholder for Tiny YOLOv4 License Plate Detection model..."
touch "$MODELS_DIR/tiny_yolov4_license_plate_detection.hef"

# Set permissions
chown -R $(logname):$(logname) "$PACKAGES_DIR"
chmod -R 755 "$PACKAGES_DIR"
chown -R $(logname):$(logname) "$MODELS_DIR"
chmod -R 755 "$MODELS_DIR"

echo ""
echo "Hailo SDK and model download completed!"
echo ""
echo "The following packages are available in $PACKAGES_DIR:"
ls -la "$PACKAGES_DIR"
echo ""
echo "The following models are available in $MODELS_DIR:"
ls -la "$MODELS_DIR"
echo ""
echo "These packages and models will be used during the VisiGate installation."
