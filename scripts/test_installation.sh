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

# Function to handle dependency conflicts
handle_dependency_conflicts() {
    echo "Handling dependency conflicts..."
    
    # Update typing-extensions to a compatible version
    echo "Updating typing-extensions to a compatible version..."
    pip install "typing-extensions>=4.5.0"
    
    # Try installing the problematic packages again
    echo "Reinstalling Flask-Limiter and FastAPI..."
    pip install Flask-Limiter==2.5.0 fastapi==0.103.2
}

# Function to handle package installation with fallback
install_package() {
    package=$1
    echo "Installing $package..."
    
    # Skip uvloop as it fails to build on ARM architecture
    if [[ $package == *"uvloop"* ]]; then
        echo "Skipping uvloop as it may fail to build on ARM architecture"
        return 0
    fi
    
    # Try installing with specified version
    pip install "$package" || {
        echo "Failed to install $package"
        
        # Try installing without version constraint
        if [[ $package == *"=="* ]]; then
            package_name=${package%%==*}
            echo "Trying to install $package_name without version constraint"
            pip install "$package_name" || {
                echo "Warning: Failed to install $package_name"
                return 1
            }
        else
            return 1
        fi
    }
    return 0
}

# Install packages one by one with detailed error reporting
echo "Installing packages one by one..."

install_package "numpy>=1.23.5,<2.0.0"
install_package "opencv-python-headless==4.5.5.64" 
install_package "Pillow>=10.0.0" 
install_package "pytesseract==0.3.9"
install_package "imutils==0.5.4"
install_package "Flask==2.0.3"
install_package "Flask-SQLAlchemy==2.5.1"
install_package "Flask-Limiter==2.5.0"
install_package "Werkzeug==2.0.3"
install_package "fastapi==0.103.2"
install_package "uvicorn==0.23.2"
install_package "aiohttp==3.8.1" 
install_package "uvloop==0.16.0" 
install_package "asgiref==3.5.2"

# Install TensorFlow
echo "Installing TensorFlow..."

# Try installing from PyPI first
pip install tensorflow==2.15.0 &> /dev/null || {
    echo "Standard TensorFlow installation failed, trying alternative methods..."
    
    # Try a newer version
    pip install tensorflow==2.16.1 &> /dev/null || {
        echo "Newer TensorFlow version installation failed, trying to build from source..."
        
        # Create a temporary directory for building
        BUILD_DIR=$(mktemp -d)
        
        # Clone the TensorFlow repository
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
            ./configure_script.sh | ./configure &> /dev/null
            
            # Build TensorFlow
            echo "Building TensorFlow from source (this may take a while)..."
            bazel build --config=opt --config=noaws --config=nogcp --config=nohdfs --config=nonccl //tensorflow/tools/pip_package:build_pip_package &> /dev/null
            
            # Check if build was successful
            if [ -f "./bazel-bin/tensorflow/tools/pip_package/build_pip_package" ]; then
                # Build the pip package
                ./bazel-bin/tensorflow/tools/pip_package/build_pip_package "$BUILD_DIR/tensorflow_pkg" &> /dev/null
                
                # Install the pip package
                pip install "$BUILD_DIR"/tensorflow_pkg/tensorflow-*.whl &> /dev/null
            fi
            
            cd - &> /dev/null
        fi
        
        # Clean up
        rm -rf "$BUILD_DIR"
        
        # If TensorFlow is still not installed, try TensorFlow Lite
        if ! python -c "import tensorflow" &> /dev/null; then
            echo "Building from source failed, installing TensorFlow Lite as fallback..."
            pip install tflite-runtime &> /dev/null
        fi
    }
}

# Check if any TensorFlow variant is installed
if python -c "import tensorflow" &> /dev/null; then
    echo "TensorFlow installed successfully."
elif python -c "import tflite_runtime" &> /dev/null; then
    echo "TensorFlow Lite installed as fallback."
else
    echo "WARNING: Neither TensorFlow nor TensorFlow Lite could be installed."
fi

# Call the function to handle dependency conflicts
handle_dependency_conflicts

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
