# AMSLPR Installation Guide for Raspberry Pi 5

> **IMPORTANT LICENSE NOTICE**: This software is proprietary and confidential. Unauthorized use, reproduction, or distribution is prohibited. All rights reserved by Automate Systems.

This guide provides step-by-step instructions for installing the AMSLPR (Automated Machine Learning-based System for License Plate Recognition) on a Raspberry Pi 5 with Hailo TPU acceleration.

## Prerequisites

### Hardware Requirements

- Raspberry Pi 5 (4GB or 8GB RAM recommended)
- Hailo-8 TPU (connected via M.2 or PCIe adapter)
- USB camera or IP camera with ONVIF support
- MicroSD card (32GB or larger recommended)
- Power supply (official 5V/5A USB-C power supply recommended)

### Software Requirements

- Raspberry Pi OS (64-bit, Debian Bookworm or newer)
- Python 3.11 (REQUIRED - no other Python versions are supported)
- Git

## Installation Steps

### Step 1: Set Up Raspberry Pi OS

1. Download the latest 64-bit Raspberry Pi OS image from [the official website](https://www.raspberrypi.org/software/)
2. Flash the image to your microSD card using Raspberry Pi Imager or similar tool
3. Boot your Raspberry Pi and complete the initial setup

### Step 2: Update System and Install Dependencies

Open a terminal and run:

```bash
sudo apt update
sudo apt upgrade -y
```

### Step 3: Install Python 3.11

Python 3.11 is **REQUIRED** for AMSLPR with Hailo TPU integration. No other Python versions are supported.

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

Verify the installation:

```bash
python3.11 --version
```

Make Python 3.11 the default Python version:

```bash
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### Step 4: Install Git and Other Dependencies

```bash
sudo apt install -y git cmake build-essential libopencv-dev
```

### Step 5: Clone the AMSLPR Repository

```bash
git clone https://github.com/SimonJackson24/AMSLPR.git
cd AMSLPR
```

### Step 6: Run the Installation Script

First, make the installation script executable:

```bash
chmod +x scripts/install_on_raspberry_pi.sh
```

Then run the installation script from the AMSLPR directory:

```bash
sudo scripts/install_on_raspberry_pi.sh
```

This script will:
1. Check for Python 3.11 (and exit if not found)
2. Automatically detect your current user account (no longer requires the default 'pi' user)
3. Detect that you're running from an existing repository (no GitHub authentication needed)
4. Create a Python virtual environment
5. Install required Python packages
6. Install Hailo TPU drivers and SDK
7. Set up the AMSLPR service
8. Configure the system for automatic startup

### Step 7: Verify the Installation

Make the verification script executable:

```bash
chmod +x scripts/verify_hailo_installation.py
```

Run the verification script to ensure everything is working correctly:

```bash
source venv/bin/activate
python scripts/verify_hailo_installation.py
```

This will check:
- Hailo SDK installation
- Hailo device detection
- Model availability
- OCR configuration

### Step 8: Start the AMSLPR Service

```bash
sudo systemctl start amslpr
```

Check the status:

```bash
sudo systemctl status amslpr
```

## Accessing the AMSLPR Web Interface

Once the service is running, you can access the AMSLPR web interface by opening a browser and navigating to:

```
http://<raspberry-pi-ip-address>:5000
```

Replace `<raspberry-pi-ip-address>` with the actual IP address of your Raspberry Pi.

## Troubleshooting

### Python Version Issues

If you encounter errors related to Python version compatibility:

1. Ensure you have Python 3.11 installed:
   ```bash
   python3.11 --version
   ```

2. If Python 3.11 is not available, install it as described in Step 3.

### Hailo TPU Detection Issues

If the system cannot detect the Hailo TPU:

1. Check the physical connection of the Hailo-8 TPU
2. Verify the Hailo drivers are installed:
   ```bash
   sudo hailortcli fw-control identify
   ```

3. If the driver is not found, reinstall it:
   ```bash
   sudo dpkg -i /opt/hailo/packages/hailort*.deb
   ```

### Model Loading Issues

If you encounter issues with loading the Hailo models:

1. Check that all required models are present in the `models` directory:
   ```bash
   ls -l models/*.hef
   ```

2. If models are missing, run the model download script:
   ```bash
   python scripts/download_hailo_models.py
   ```

### Script Permission Issues

If you encounter "command not found" or permission errors when running scripts:

1. Make sure all scripts have executable permissions:
   ```bash
   chmod +x scripts/*.sh scripts/*.py
   ```

2. Ensure you're running the scripts from the AMSLPR root directory:
   ```bash
   cd /path/to/AMSLPR
   ```

### Dependency Conflicts

If you encounter dependency conflicts during installation, particularly with `typing-extensions`, the installation script will automatically handle these by:

1. First attempting to install all packages at once
2. If that fails, installing packages one by one
3. Updating `typing-extensions` to a version compatible with all dependencies

If you need to manually resolve dependency conflicts:

```bash
# Install a compatible version of typing-extensions
pip install typing-extensions>=4.5.0

# Reinstall the conflicting packages
pip install Flask-Limiter==2.5.0 fastapi==0.103.2
```

### TensorFlow Installation

The installation script now handles TensorFlow installation automatically with multiple fallback options:

1. First attempts to install TensorFlow 2.15.0 from PyPI
2. If that fails, tries a newer version (2.16.1)
3. If that fails, automatically builds TensorFlow from source using the official GitHub repository
4. As a last resort, installs TensorFlow Lite as a fallback

This process requires no user interaction and will select the best available option for your system.

If you need to manually install TensorFlow, here are the options:

```bash
# Option 1: Install from PyPI
pip install tensorflow==2.15.0

# Option 2: Try a newer version
pip install tensorflow==2.16.1

# Option 3: Install TensorFlow Lite as a lightweight alternative
pip install tflite-runtime
```

### Python Package Build Issues

If you encounter errors building Python packages with C extensions (like aiohttp, uvloop):

1. Make sure you have the Python development packages installed:
   ```bash
   sudo apt install -y python3-dev python3.11-dev build-essential
   ```

2. For specific packages that fail to build, you can try installing them with pre-built wheels:
   ```bash
   pip install --only-binary=:all: aiohttp uvloop
   ```

3. If that doesn't work, you can try installing older versions that have pre-built wheels available:
   ```bash
   pip install aiohttp==3.8.1 uvloop==0.16.0
   ```

### Pillow Installation Issues

If you encounter errors building Pillow from source:

1. Install the required system dependencies:
   ```bash
   sudo apt install -y libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7-dev libtiff5-dev libwebp-dev
   ```

2. Try installing Pillow with a pre-built wheel:
   ```bash
   pip install --only-binary=:all: Pillow
   ```

3. For Python 3.12, you need to use Pillow 10.0.0 or higher:
   ```bash
   pip install Pillow>=10.0.0
   ```

4. For Python 3.11, you can use Pillow 9.5.0:
   ```bash
   pip install Pillow==9.5.0
   ```

### Package Installation Issues

If you encounter issues with specific packages during installation:

#### uvloop

The `uvloop` package is optional but provides better performance for async operations. It may fail to build on ARM architecture. The installation script will handle this gracefully:

1. On non-ARM platforms, uvloop will be installed automatically
2. On ARM platforms (like Raspberry Pi), the system will fall back to the standard asyncio event loop
3. The application is designed to work correctly with or without uvloop

If you want to manually install uvloop on ARM (which may require additional build dependencies):

```bash
# Install build dependencies
sudo apt-get update
sudo apt-get install -y python3-dev build-essential

# Try installing uvloop
pip install uvloop
```

#### Invalid Requirement Format

If you see errors about invalid requirement format (such as with comments in requirements.txt), the installation script will handle this automatically. If you need to manually fix this:

```bash
# Remove comments from requirements.txt
sed -i 's/#.*$//' requirements.txt
```

## Additional Resources

- [Hailo Developer Zone](https://hailo.ai/developer-zone/) - For additional Hailo TPU documentation
- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/) - For Raspberry Pi specific issues
- [AMSLPR GitHub Repository](https://github.com/SimonJackson24/AMSLPR) - For the latest updates and issue tracking

## Support

If you encounter any issues not covered in this guide, please open an issue on the [AMSLPR GitHub repository](https://github.com/SimonJackson24/AMSLPR/issues).
