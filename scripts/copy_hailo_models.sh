#!/bin/bash

set -e

echo "Copying Hailo models from Downloads folder to AMSLPR models directory"
echo "================================================================"
echo ""

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create models directory
MODELS_DIR="$PROJECT_ROOT/models"
mkdir -p "$MODELS_DIR"

# Get current user's home directory
if [ "$(id -u)" -eq 0 ]; then
    # If running as root, get the home directory of the sudo user
    if [ -n "$SUDO_USER" ]; then
        USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    else
        USER_HOME="/home/$(logname 2>/dev/null || echo 'pi')"
    fi
else
    # If running as normal user
    USER_HOME="$HOME"
fi

DOWNLOADS_DIR="$USER_HOME/Downloads"

echo "Looking for models in $DOWNLOADS_DIR"

# Check for YOLOv5m model
YOLOV5M_SOURCES=("$DOWNLOADS_DIR/yolov5m.hef" "$DOWNLOADS_DIR/yolov5m_license_plates.hef")
YOLOV5M_DEST="$MODELS_DIR/yolov5m_license_plates.hef"

for src in "${YOLOV5M_SOURCES[@]}"; do
    if [ -f "$src" ]; then
        echo "Found YOLOv5m model at $src"
        echo "Copying to $YOLOV5M_DEST"
        cp "$src" "$YOLOV5M_DEST"
        echo "✅ YOLOv5m model copied successfully"
        break
    fi
done

# Check for Tiny YOLOv4 model
TINY_YOLO_SOURCES=("$DOWNLOADS_DIR/tiny_yolov4.hef" "$DOWNLOADS_DIR/tiny_yolov4_license_plate_detection.hef")
TINY_YOLO_DEST="$MODELS_DIR/tiny_yolov4_license_plate_detection.hef"

for src in "${TINY_YOLO_SOURCES[@]}"; do
    if [ -f "$src" ]; then
        echo "Found Tiny YOLOv4 model at $src"
        echo "Copying to $TINY_YOLO_DEST"
        cp "$src" "$TINY_YOLO_DEST"
        echo "✅ Tiny YOLOv4 model copied successfully"
        break
    fi
done

# Check if LPRNet model exists, if not download it
LPRNET_DEST="$MODELS_DIR/lprnet_vehicle_license_recognition.hef"
if [ ! -f "$LPRNET_DEST" ]; then
    echo "LPRNet model not found, attempting to download..."
    wget -O "$LPRNET_DEST" https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/HailoNets/LPR/ocr/lprnet/2022-03-09/lprnet.hef || echo "Failed to download LPRNet model"
    if [ -f "$LPRNET_DEST" ]; then
        echo "✅ LPRNet model downloaded successfully"
    fi
else
    echo "✅ LPRNet model already exists at $LPRNET_DEST"
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

# Check if all required models are available
if [ -f "$YOLOV5M_DEST" ] && [ -f "$TINY_YOLO_DEST" ] && [ -f "$LPRNET_DEST" ]; then
    echo "✅ All required models are available"
    exit 0
else
    echo "⚠️ Some models are missing:"
    [ ! -f "$YOLOV5M_DEST" ] && echo "   - YOLOv5m License Plates model is missing"
    [ ! -f "$TINY_YOLO_DEST" ] && echo "   - Tiny YOLOv4 License Plate Detection model is missing"
    [ ! -f "$LPRNET_DEST" ] && echo "   - LPRNet Vehicle License Recognition model is missing"
    echo ""
    echo "Please download the missing models from the Hailo Developer Zone (https://hailo.ai/developer-zone/)"
    echo "and place them in the $DOWNLOADS_DIR directory, then run this script again."
    exit 1
fi
