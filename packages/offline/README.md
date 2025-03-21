# AMSLPR Offline Wheel Packages

This directory contains pre-built Python wheel packages for ARM architecture (Raspberry Pi) to enable true offline installation of the AMSLPR system with Hailo TPU support.

## Included Wheel Files

The following wheel files are included for offline installation:

1. **NumPy**: numpy-2.2.4-cp311-cp311-linux_armv7l.whl - Mathematical operations for image processing
2. **Pillow**: Pillow-10.1.0-cp311-cp311-linux_armv7l.whl - Image processing library
3. **aiohttp**: aiohttp-3.11.14-cp311-cp311-linux_armv7l.whl - Asynchronous HTTP client/server
4. **Flask**: Flask-2.0.1-py3-none-any.whl - Web framework for the UI
5. **Werkzeug**: Werkzeug-2.0.1-py3-none-any.whl - WSGI utility library for Flask
6. **OpenCV**: opencv_python_headless-4.8.0.74-cp311-cp311-linux_armv7l.whl - Computer vision library
7. **Hailo Platform**: hailo_platform-4.20.0-py3-none-any.whl - Hailo TPU integration
8. **Hailort**: hailort-4.20.0-py3-none-any.whl - Hailo runtime library

## Hailo TPU Integration

The Hailo TPU wheels provide integration with the Hailo hardware accelerator. These packages have the following features:

1. **Real hardware detection** - Attempts to detect and use real Hailo hardware if present
2. **Graceful fallback** - Falls back to mock implementations if hardware is not available
3. **Diagnostic capabilities** - Provides diagnostic functions to verify TPU functionality
4. **Environment variable control** - Can be controlled via the `HAILO_ENABLED` environment variable
5. **Hardware-accelerated inference** - When hardware is present, provides accelerated inference

## Installation

These wheel files are automatically used by the offline installation script (`scripts/offline_install.sh`). The script will:

1. Create the necessary directories
2. Copy the wheel files to the appropriate location
3. Install the wheels in the correct order with proper dependencies
4. Create any necessary configuration files
5. Set up the TPU environment

## Testing Hailo TPU Integration

After installation, you can test the Hailo TPU integration with:

```python
import hailo_platform
print(hailo_platform.get_status())  # Shows TPU status
print(hailo_platform.diagnose())    # Run full diagnostics

# Initialize device
device = hailo_platform.Device()
print(f"Device ID: {device.device_id}")
```

## Updating Wheels

To update these wheels with newer versions:

1. Download the appropriate ARM-compatible wheels from piwheels.org
2. Replace the existing wheel files in this directory
3. Test the installation on a Raspberry Pi

For the Hailo TPU wheels, you may need to repackage the updated modules if there are changes to the API.