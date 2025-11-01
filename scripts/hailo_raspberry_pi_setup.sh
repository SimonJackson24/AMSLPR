#!/bin/bash

set -e

echo "Hailo TPU Model Download Script for VisiGate"
echo "========================================="
echo ""

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create models directory
MODELS_DIR="$PROJECT_ROOT/models"
mkdir -p "$MODELS_DIR"

echo "Step 1: Installing dependencies..."
apt-get update
apt-get install -y wget git

echo "Step 2: Downloading license plate recognition models..."

# Check if models already exist in the project directory
if [ -f "$MODELS_DIR/lprnet_vehicle_license_recognition.hef" ] && \
   [ -f "$MODELS_DIR/yolov5m_license_plates.hef" ] && \
   [ -f "$MODELS_DIR/tiny_yolov4_license_plate_detection.hef" ]; then
    echo "All required models already exist in $MODELS_DIR"
    echo "Skipping model download..."
else
    # Try to download pre-compiled models
    echo "Downloading pre-compiled models..."

    # Download LPRNet if it doesn't exist
    if [ ! -f "$MODELS_DIR/lprnet_vehicle_license_recognition.hef" ]; then
        echo "Downloading LPRNet Vehicle License Recognition model..."
        wget -O "$MODELS_DIR/lprnet_vehicle_license_recognition.hef" https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/HailoNets/LPR/ocr/lprnet/2022-03-09/lprnet.hef || echo "Failed to download lprnet model"
    fi

    # Create placeholder for YOLOv5m if it doesn't exist
    if [ ! -f "$MODELS_DIR/yolov5m_license_plates.hef" ]; then
        echo "NOTE: YOLOv5m model needs to be downloaded from Hailo Developer Zone."
        echo "Creating placeholder for YOLOv5m License Plates model..."
        touch "$MODELS_DIR/yolov5m_license_plates.hef"
    fi

    # Create placeholder for Tiny YOLOv4 if it doesn't exist
    if [ ! -f "$MODELS_DIR/tiny_yolov4_license_plate_detection.hef" ]; then
        echo "NOTE: Tiny YOLOv4 model needs to be downloaded from Hailo Developer Zone."
        echo "Creating placeholder for Tiny YOLOv4 License Plate Detection model..."
        touch "$MODELS_DIR/tiny_yolov4_license_plate_detection.hef"
    fi
fi

# Download character map for OCR if it doesn't exist
if [ ! -f "$MODELS_DIR/char_map.json" ]; then
    echo "Downloading character map for OCR..."
    cat > "$MODELS_DIR/char_map.json" << EOL
{
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "A": 10,
    "B": 11,
    "C": 12,
    "D": 13,
    "E": 14,
    "F": 15,
    "G": 16,
    "H": 17,
    "I": 18,
    "J": 19,
    "K": 20,
    "L": 21,
    "M": 22,
    "N": 23,
    "O": 24,
    "P": 25,
    "Q": 26,
    "R": 27,
    "S": 28,
    "T": 29,
    "U": 30,
    "V": 31,
    "W": 32,
    "X": 33,
    "Y": 34,
    "Z": 35
}
EOL
fi

# Set permissions for models directory
chown -R $(logname):$(logname) "$MODELS_DIR"
chmod -R 755 "$MODELS_DIR"

echo ""
echo "Model setup completed!"
echo ""
echo "The following models are available in $MODELS_DIR:"
ls -la "$MODELS_DIR" | grep -E "\.hef|\.json"
echo ""
echo "Important Notes:"
echo "1. The Hailo SDK requires registration at https://hailo.ai/developer-zone/"
echo "2. You need to download the appropriate Hailo SDK package for ARM64/Raspberry Pi"
echo "   from the Hailo Developer Zone and place it in the /opt/hailo/packages directory."
echo "3. After installing the Hailo SDK, run the enable_hailo_tpu.py script in your VisiGate installation"
echo "   to configure the OCR system to use these models."
echo ""
echo "For detailed instructions, see docs/raspberry_pi_hailo_setup.md"
echo ""
