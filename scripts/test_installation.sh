#!/bin/bash

# Test installation script for AMSLPR on Raspberry Pi
# This script simulates the installation process without actually installing system services

set -e

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3 first."
    exit 1
fi

# Create a virtual environment for testing
PROJECT_DIR="$(pwd)"
VENV_DIR="${PROJECT_DIR}/venv_test"

# Remove existing virtual environment if it exists
if [ -d "${VENV_DIR}" ]; then
    echo "Removing existing virtual environment..."
    rm -rf "${VENV_DIR}"
fi

echo "Creating test virtual environment in ${VENV_DIR}..."
python3 -m venv "${VENV_DIR}"

# Activate the virtual environment
source "${VENV_DIR}/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install packages one by one with detailed error reporting
echo "Installing packages one by one..."

echo "Installing NumPy..."
pip install "numpy>=1.23.5,<2.0.0"

echo "Installing OpenCV..."
pip install "opencv-python-headless==4.5.5.64" --only-binary=:all:

echo "Installing Pillow..."
pip install "Pillow>=10.0.0" --only-binary=:all:

# Install TensorFlow
echo "Installing TensorFlow..."
pip install "tensorflow==2.15.0" --extra-index-url https://tf.pypi.io/simple

# If TensorFlow installation fails, provide information about alternatives
if ! python -c "import tensorflow" &> /dev/null; then
    echo "TensorFlow installation failed. Here are some alternatives:"
    echo "1. Try installing a different version: pip install tensorflow==2.16.1"
    echo "2. Use TensorFlow Lite: pip install tflite-runtime"
    echo "3. Build from source: https://github.com/tensorflow/tensorflow"
    
    # Try installing TensorFlow Lite as a fallback
    echo "Trying TensorFlow Lite as a fallback..."
    pip install tflite-runtime
fi

echo "Installing pytesseract..."
pip install "pytesseract==0.3.9"

echo "Installing imutils..."
pip install "imutils==0.5.4"

echo "Installing Flask..."
pip install "Flask==2.0.3"

echo "Installing Flask-SQLAlchemy..."
pip install "Flask-SQLAlchemy==2.5.1"

echo "Installing Flask-Limiter..."
pip install "Flask-Limiter==2.5.0"

echo "Installing Werkzeug..."
pip install "Werkzeug==2.0.3"

echo "Installing FastAPI..."
pip install "fastapi==0.103.2"

echo "Installing Uvicorn..."
pip install "uvicorn==0.23.2"

echo "Installing aiohttp..."
pip install "aiohttp==3.8.1" --only-binary=:all:

echo "Installing uvloop..."
pip install "uvloop==0.16.0" --only-binary=:all:

echo "Installing asgiref..."
pip install "asgiref==3.5.2"

echo "Testing import of key packages..."
python -c "import numpy; print('NumPy version:', numpy.__version__)"
python -c "import cv2; print('OpenCV version:', cv2.__version__)"
python -c "import PIL; print('Pillow version:', PIL.__version__)"
python -c "import flask; print('Flask version:', flask.__version__)"
python -c "import fastapi; print('FastAPI version:', fastapi.__version__)"
python -c "import uvicorn; print('Uvicorn version:', uvicorn.__version__)"
python -c "import aiohttp; print('aiohttp version:', aiohttp.__version__)"

echo "\nTest installation completed successfully!"
echo "You can activate the test environment with: source ${VENV_DIR}/bin/activate"
