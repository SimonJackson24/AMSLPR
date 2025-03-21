# AMSLPR Offline Wheel Packages

This directory should contain pre-built Python wheel packages for ARM (Raspberry Pi) architecture to enable true offline installation.

## Required Wheel Files

Place the following wheel files in this directory before creating a distribution for offline installation:

1. **NumPy**: numpy-1.21.0-cp311-cp311-linux_aarch64.whl
2. **Pillow**: Pillow-8.4.0-cp311-cp311-linux_aarch64.whl 
3. **OpenCV**: opencv_python_headless-4.5.3.56-cp311-cp311-linux_aarch64.whl
4. **aiohttp**: aiohttp-3.7.4-cp311-cp311-linux_aarch64.whl
5. **Flask**: Flask-2.0.1-py3-none-any.whl
6. **Werkzeug**: Werkzeug-2.0.1-py3-none-any.whl

## How to Obtain These Wheels

You can download pre-built binaries for ARM architecture (aarch64) from:

1. https://www.piwheels.org/ - Official Python package repository for Raspberry Pi
2. https://pypi.org/project/[package-name]/#files - Check if ARM wheels are available
3. Or build them on a similar ARM device using:
   ```bash
   pip wheel --wheel-dir=./wheels [package-name]==version
   ```

## Installation

These wheel files will be automatically installed by the offline installation script when the system is installed on a Raspberry Pi.