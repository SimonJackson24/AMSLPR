# Setting up VisiGate with Hailo TPU on Raspberry Pi

This guide provides instructions for setting up the VisiGate system on a Raspberry Pi with Hailo TPU acceleration.

## Hardware Requirements

- Raspberry Pi 4 (8GB RAM recommended)
- Hailo-8 TPU device
- MicroSD card (32GB or larger recommended)
- Power supply for Raspberry Pi (3A minimum)
- Optional: Cooling solution for Raspberry Pi (heatsink/fan)

## Automated Installation

The VisiGate installation script now handles the entire setup process automatically, including Hailo TPU configuration:

```bash
git clone https://github.com/yourusername/VisiGate.git
cd VisiGate
sudo ./scripts/install_on_raspberry_pi.sh
```

The installation script will:
1. Install system dependencies
2. Set up a Python virtual environment
3. Install Python dependencies
4. **Automatically download and install Hailo SDK packages**
5. Install the pre-packaged Hailo models or download them automatically
6. Configure the application to use Hailo TPU
7. Set up a systemd service for automatic startup

**No manual downloads are required!** The installation script will automatically download all necessary Hailo SDK packages and models, or use pre-packaged ones if available.

## Verification

After installation, the script will automatically verify the Hailo TPU setup. If everything is working correctly, you should see a success message. If there are any issues, the script will provide detailed information about what went wrong and how to fix it.

You can manually verify the Hailo TPU installation at any time by running:

```bash
sudo systemctl stop visigate  # Stop the service if it's running
cd /opt/visigate
source venv/bin/activate
python scripts/verify_hailo_installation.py
```

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

> **Note**: While manual installation requires registration at the [Hailo Developer Zone](https://hailo.ai/developer-zone/), the automated installation script will download the necessary packages for you.

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

### Step 4: Download Hailo Models

1. Create a models directory:
   ```bash
   mkdir -p /opt/visigate/models
   ```

2. Download the LPRNet model (for license plate recognition):
   ```bash
   wget -O /opt/visigate/models/lprnet_vehicle_license_recognition.hef \
       https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/HailoNets/LPR/ocr/lprnet/2022-03-09/lprnet.hef
   ```

3. Download the YOLOv5m and Tiny YOLOv4 models from the Hailo Developer Zone and place them in the models directory:
   ```bash
   # After downloading from Hailo Developer Zone
   mv /path/to/downloaded/yolov5m.hef /opt/visigate/models/yolov5m_license_plates.hef
   mv /path/to/downloaded/tiny_yolov4.hef /opt/visigate/models/tiny_yolov4_license_plate_detection.hef
   ```

4. Create the character map for OCR:
   ```bash
   cat > /opt/visigate/models/char_map.json << EOL
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
   ```

### Step 5: Enable Hailo TPU in VisiGate

1. Run the Hailo TPU setup script:
   ```bash
   cd /opt/visigate
   source venv/bin/activate
   sudo python scripts/enable_hailo_tpu.py --auto-approve
   ```

This script will:
- Check if the Hailo device is accessible
- Configure the OCR system to use Hailo TPU
- Update the configuration files

## Troubleshooting

### Hailo Device Not Detected

If the Hailo device is not detected (`/dev/hailo0` does not exist):

1. Check if the device is properly connected to the USB port
2. Try a different USB port (preferably USB 3.0)
3. Check if the udev rules are properly set up
4. Restart the system and try again

### Hailo SDK Import Error

If you encounter an error importing the Hailo SDK:

1. Check if the Hailo Python packages are installed correctly:
   ```bash
   pip list | grep hailo
   ```

2. Make sure you're using the correct Python version (3.10 or higher):
   ```bash
   python --version
   ```

3. Try reinstalling the Hailo Python packages:
   ```bash
   pip install --force-reinstall /opt/hailo/packages/hailo*.whl
   ```

### Model Not Found Error

If you encounter an error about missing models:

1. Check if the models are in the correct location:
   ```bash
   ls -l /opt/visigate/models/*.hef
   ```

2. Make sure the models have the correct names:
   - `lprnet_vehicle_license_recognition.hef`
   - `yolov5m_license_plates.hef`
   - `tiny_yolov4_license_plate_detection.hef`

3. If any models are missing, download them as described in Step 4 of the manual installation.

## Performance Considerations

When using the Hailo TPU with a Raspberry Pi:

1. Ensure adequate cooling for both the Raspberry Pi and the Hailo TPU
2. Use a high-quality power supply (5V/3A minimum)
3. For optimal performance, use a USB 3.0 port for the Hailo TPU
4. Monitor the system temperature during operation

## Additional Resources

- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo)
- [Hailo Documentation](https://hailo.ai/documentation/)
