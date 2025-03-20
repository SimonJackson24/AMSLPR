# Setting up AMSLPR with Hailo TPU on Raspberry Pi

This guide provides instructions for setting up the AMSLPR system on a Raspberry Pi with Hailo TPU acceleration.

## Hardware Requirements

- Raspberry Pi 4 (8GB RAM recommended)
- Hailo-8 TPU device
- MicroSD card (32GB or larger recommended)
- Power supply for Raspberry Pi (3A minimum)
- Optional: Cooling solution for Raspberry Pi (heatsink/fan)

## Automated Installation

The AMSLPR installation script now handles the entire setup process automatically, including Hailo TPU configuration:

```bash
git clone https://github.com/yourusername/AMSLPR.git
cd AMSLPR
sudo ./scripts/install_on_raspberry_pi.sh
```

The installation script will:
1. Install system dependencies
2. Set up a Python virtual environment
3. Install Python dependencies
4. Check for Hailo packages and install them if available
5. Install the pre-packaged Hailo models (all required models are included)
6. Configure the application to use Hailo TPU
7. Set up a systemd service for automatic startup

**No manual downloads are required!** All necessary Hailo models (YOLOv5m, Tiny YOLOv4, and LPRNet) are included in the AMSLPR package.

## Manual Installation Steps

If you prefer to perform the installation manually or need to troubleshoot specific components, follow these steps:

### Step 1: Prepare the Raspberry Pi

1. Download and install the latest Raspberry Pi OS (64-bit recommended) using the Raspberry Pi Imager:
   https://www.raspberrypi.org/software/

2. During setup, enable SSH for remote access

3. Boot the Raspberry Pi and complete the initial setup

4. Update the system:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

### Step 2: Install Hailo Driver and SDK

> **Important Note**: The Hailo SDK requires registration at the [Hailo Developer Zone](https://hailo.ai/developer-zone/). You will need to download the appropriate Hailo SDK package for ARM64/Raspberry Pi from the Hailo Developer Zone.

1. Register and download the following packages from the Hailo Developer Zone (https://hailo.ai/developer-zone/):
   - Hailo Runtime Package (hailort*.deb) for ARM64/Raspberry Pi
   - Hailo Python SDK Wheel Files (hailo*.whl) for ARM64/Raspberry Pi

2. Transfer the downloaded packages to your Raspberry Pi (e.g., using SCP or a USB drive)

3. Create a directory for Hailo packages:
   ```bash
   sudo mkdir -p /opt/hailo/packages
   ```

4. Move the downloaded packages to the Hailo packages directory:
   ```bash
   sudo mv /path/to/downloaded/hailort*.deb /opt/hailo/packages/
   sudo mv /path/to/downloaded/hailo*.whl /opt/hailo/packages/
   ```

5. Install the Hailo driver package:
   ```bash
   sudo dpkg -i /opt/hailo/packages/hailort*.deb
   sudo apt-get install -f -y
   ```

6. Set up udev rules for the Hailo device:
   ```bash
   sudo bash -c 'cat > /etc/udev/rules.d/99-hailo.rules << EOL
SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"
SUBSYSTEM=="hailo", MODE="0666"
EOL'
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

7. Verify the driver installation by checking if the Hailo device is detected:
   ```bash
   ls -l /dev/hailo*
   ```
   You should see `/dev/hailo0` if the device is properly connected and the driver is installed.

### Step 3: Install Python SDK for Hailo

1. Install the Hailo Python packages:
   ```bash
   pip install /opt/hailo/packages/hailo*.whl
   ```

2. Verify the installation by importing the Hailo SDK in Python:
   ```bash
   python3 -c "import hailo_platform; print('Hailo SDK version:', hailo_platform.__version__)"
   ```

### Step 4: Install AMSLPR

1. Clone the AMSLPR repository or copy it to the Raspberry Pi:
   ```bash
   git clone https://github.com/yourusername/AMSLPR.git
   cd AMSLPR
   ```

2. Run the installation script:
   ```bash
   sudo chmod +x scripts/install_on_raspberry_pi.sh
   sudo ./scripts/install_on_raspberry_pi.sh
   ```

## Python Version Requirement

**IMPORTANT**: Python 3.11 is **REQUIRED** for AMSLPR with Hailo TPU integration. No other Python versions are supported.

The Hailo SDK wheel file included in this repository is specifically compiled for Python 3.11 on ARM64 architecture. The installation script will check for Python 3.11 and will exit with an error if it's not available.

To install Python 3.11 on Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

If Python 3.11 is not available in your repositories, you may need to use a more recent version of Raspberry Pi OS or add a third-party repository that provides Python 3.11.

## Step 5: Download Hailo Models

**No manual downloads are required!** All necessary Hailo models (YOLOv5m, Tiny YOLOv4, and LPRNet) are included in the AMSLPR package.

## Step 6: Configure AMSLPR to Use Hailo TPU

After installing AMSLPR and the Hailo SDK, you need to configure the system to use the Hailo TPU for inference:

```bash
sudo python scripts/enable_hailo_tpu.py
```

This script will:
- Check if the Hailo device is accessible
- Look for available Hailo models in the models directory
- Update the OCR configuration to use the Hailo TPU and models

## Step 7: Verify Hailo TPU Integration

You can verify that the Hailo TPU is properly integrated with AMSLPR by running:

```bash
python scripts/verify_hailo_installation.py
```

This script will check:
- If the Hailo SDK is installed
- If the Hailo device is accessible
- If the required models are available
- If the OCR configuration is set up to use Hailo TPU

## Step 8: Access the Application

1. Start the AMSLPR service if it's not already running:
   ```bash
   sudo systemctl start amslpr
   ```

2. Access the web interface at:
   ```
   http://<raspberry-pi-ip>:5001
   ```

3. Log in with the default credentials:
   - Username: admin
   - Password: admin

4. Change the default password immediately after logging in

## Troubleshooting

### Hailo Device Not Detected

If the Hailo device is not detected (`/dev/hailo0` does not exist):

1. Check if the device is properly connected
2. Verify that the driver is installed:
   ```bash
   dpkg -l | grep hailo
   ```
3. Check dmesg for any USB or Hailo-related errors:
   ```bash
   dmesg | grep -E 'hailo|usb'
   ```
4. Try rebooting the Raspberry Pi:
   ```bash
   sudo reboot
   ```

### Hailo SDK Import Error

If you get an import error when trying to import the Hailo SDK:

1. Verify that the Hailo Python packages are installed:
   ```bash
   pip list | grep hailo
   ```
2. Make sure you're using the correct Python environment
3. Try reinstalling the packages:
   ```bash
   pip install --force-reinstall /opt/hailo/packages/hailo*.whl
   ```

### Model Not Found

If the models are not found or the OCR configuration is not working:

1. Check if the models are downloaded:
   ```bash
   ls -l /opt/amslpr/models/*.hef
   ```
2. If the models are missing, run the model download script:
   ```bash
   sudo ./scripts/hailo_raspberry_pi_setup.sh
   ```
3. Reconfigure the OCR system to use the Hailo TPU:
   ```bash
   sudo python scripts/enable_hailo_tpu.py
   ```

## Additional Resources

- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo)
- [Hailo Documentation](https://hailo.ai/documentation/)
