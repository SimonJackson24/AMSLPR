# Pre-packaged Hailo SDK

This directory contains pre-packaged Hailo SDK packages for the AMSLPR system.

## Included Packages

### Hailo Runtime Package
- Filename: `hailort_4.20.0_arm64.deb`
- Purpose: Hailo runtime libraries and drivers for ARM64/Raspberry Pi
- Size: ~6.4MB

### Hailo Python SDK Wheel
- Filename: `hailort-4.20.0-cp311-cp311-linux_aarch64.whl`
- Purpose: Python bindings for the Hailo SDK
- Size: ~8.2MB
- **Python Version**: 3.11

### Hailo PCIe Driver Package
- Filename: `hailort-pcie-driver_4.20.0_all.deb`
- Purpose: PCIe driver for Hailo devices
- Size: ~140KB

## Python Version Requirement

**IMPORTANT**: Python 3.11 is **REQUIRED** for AMSLPR with Hailo TPU integration. No other Python versions are supported.

The included Hailo Python SDK wheel file is compiled specifically for Python 3.11. The installation script will check for Python 3.11 and will exit with an error if it's not available.

## Automatic Installation

These packages will be automatically installed by the `install_on_raspberry_pi.sh` script. No manual intervention is required.

## Package Source

These packages are sourced from the Hailo Developer Zone. They have been included in this package with permission to simplify the installation process.

## License

These packages are subject to the Hailo license terms and conditions. They are provided for use with the AMSLPR system only.
