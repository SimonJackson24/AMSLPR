# AMSLPR Offline Wheel Packages

This directory contains pre-built Python wheel packages and APT packages for ARM architecture (Raspberry Pi) to enable true offline installation of the AMSLPR system with Hailo TPU support.

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
9. **nest-asyncio**: nest-asyncio-1.5.8-py3-none-any.whl - Async event loop support

## Included APT Packages

The following APT packages are included in the `apt` directory:

1. python3
2. python3-pip
3. python3-venv
4. redis-server
5. libgl1-mesa-glx
6. libglib2.0-0
7. tesseract-ocr
8. libsm6
9. libxext6
10. libxrender1
11. libfontconfig1

## Installation

These packages are automatically used by the offline installation script (`scripts/offline_install.sh`). The script will:

1. Create the necessary directories
2. Install APT packages from the offline repository
3. Create and configure Python virtual environment
4. Install Python wheels in the correct order with proper dependencies
5. Configure Redis for Flask sessions
6. Set up the TPU environment
7. Configure systemd service

## Testing Installation

After installation, you can verify the setup with:

```bash
# Check service status
sudo systemctl status amslpr

# View logs
sudo journalctl -u amslpr -f

# Test web interface
curl http://localhost:5004
```

The web interface will be available at `http://<pi-ip>:5004`