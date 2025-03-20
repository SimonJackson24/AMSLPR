# AMSLPR Installation Guide for Raspberry Pi 5

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
chmod +x ./scripts/install_on_raspberry_pi.sh
```

Then run the installation script:

```bash
sudo ./scripts/install_on_raspberry_pi.sh
```

This script will:
1. Check for Python 3.11 (and exit if not found)
2. Create a Python virtual environment
3. Install required Python packages
4. Install Hailo TPU drivers and SDK
5. Set up the AMSLPR service
6. Configure the system for automatic startup

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

## Additional Resources

- [Hailo Developer Zone](https://hailo.ai/developer-zone/) - For additional Hailo TPU documentation
- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/) - For Raspberry Pi specific issues
- [AMSLPR GitHub Repository](https://github.com/SimonJackson24/AMSLPR) - For the latest updates and issue tracking

## Support

If you encounter any issues not covered in this guide, please open an issue on the [AMSLPR GitHub repository](https://github.com/SimonJackson24/AMSLPR/issues).
