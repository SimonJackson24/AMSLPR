#!/bin/bash

set -e

echo "Hailo TPU Diagnostic Script for Raspberry Pi 5"
echo "============================================="
echo ""

echo "Step 1: Checking system information..."
echo "OS: $(uname -a)"
echo "Architecture: $(uname -m)"
echo "Kernel: $(uname -r)"
echo ""

echo "Step 2: Checking for Hailo device..."
if [ -e /dev/hailo0 ]; then
    echo "✅ Hailo device found at /dev/hailo0"
    ls -la /dev/hailo*
    
    # Check permissions
    if [ -r /dev/hailo0 ] && [ -w /dev/hailo0 ]; then
        echo "✅ Hailo device is readable and writable"
    else
        echo "❌ Hailo device is not readable and writable"
        echo "Fixing permissions..."
        sudo chmod 666 /dev/hailo0
    fi
else
    echo "❌ Hailo device not found at /dev/hailo0"
    
    # Check if the device is connected via USB
    echo "Checking USB devices..."
    lsusb | grep -i hailo || echo "No Hailo USB device found"
    
    # Check if the device is connected via PCIe
    echo "Checking PCIe devices..."
    lspci | grep -i hailo || echo "No Hailo PCIe device found"
fi
echo ""

echo "Step 3: Checking kernel modules..."
echo "Loaded kernel modules:"
lsmod | grep -i hailo || echo "No Hailo kernel modules found"

echo "Available kernel modules:"
find /lib/modules/$(uname -r) -name "*hailo*" || echo "No Hailo kernel modules found in /lib/modules"
echo ""

echo "Step 4: Checking udev rules..."
if [ -f /etc/udev/rules.d/99-hailo.rules ]; then
    echo "✅ Hailo udev rules found"
    cat /etc/udev/rules.d/99-hailo.rules
else
    echo "❌ Hailo udev rules not found"
    echo "Creating udev rules..."
    echo 'SUBSYSTEM=="pci", ATTR{vendor}=="0x1e60", MODE="0666"' | sudo tee -a /etc/udev/rules.d/99-hailo.rules
    echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee -a /etc/udev/rules.d/99-hailo.rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger
fi
echo ""

echo "Step 5: Checking Hailo SDK installation..."
echo "Installed Python packages:"
pip list | grep -i hailo || echo "No Hailo Python packages found"

echo "Checking for hailo_platform module:"
if python3 -c "import hailo_platform; print('✅ hailo_platform module found')" 2>/dev/null; then
    # Module found, check version
    python3 -c "import hailo_platform; print(f'Version: {hailo_platform.__version__}')" 2>/dev/null || echo "Could not determine version"
else
    echo "❌ hailo_platform module not found"
fi

echo "Checking for hailort module:"
if python3 -c "import hailort; print('✅ hailort module found')" 2>/dev/null; then
    # Module found, check version
    python3 -c "import hailort; print(f'Version: {hailort.__version__}')" 2>/dev/null || echo "Could not determine version"
else
    echo "❌ hailort module not found"
fi
echo ""

echo "Step 6: Checking system resources..."
echo "Memory usage:"
free -h

echo "CPU usage:"
top -bn1 | head -n 5

echo "Power supply:"
vcgencmd measure_volts || echo "vcgencmd not available"
echo ""

echo "Step 7: Checking for known issues..."

# Check for Raspberry Pi 5 specific issues
if grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
    echo "Detected Raspberry Pi 5"
    
    # Check for PCIe power issues
    echo "Checking PCIe power management..."
    if [ -f /sys/bus/pci/devices/*/power/control ]; then
        for f in /sys/bus/pci/devices/*/power/control; do
            echo "$f: $(cat $f)"
        done
    else
        echo "No PCIe power management controls found"
    fi
    
    # Check for USB power issues
    echo "Checking USB power management..."
    if [ -d /sys/bus/usb/devices ]; then
        for d in /sys/bus/usb/devices/*; do
            if [ -f "$d/power/control" ]; then
                echo "$d: $(cat $d/power/control)"
            fi
        done
    else
        echo "No USB power management controls found"
    fi
fi
echo ""

echo "Step 8: Attempting to fix common issues..."

# Try to reload the kernel module
echo "Reloading kernel modules..."
if lsmod | grep -q hailo; then
    echo "Unloading Hailo kernel module..."
    sudo rmmod hailo || echo "Failed to unload Hailo kernel module"
    sleep 1
fi

# Find and load the Hailo kernel module
HAILO_MODULE=$(find /lib/modules/$(uname -r) -name "*hailo*.ko" | head -n 1)
if [ -n "$HAILO_MODULE" ]; then
    echo "Loading Hailo kernel module from $HAILO_MODULE..."
    sudo insmod "$HAILO_MODULE" || echo "Failed to load Hailo kernel module"
else
    echo "No Hailo kernel module found to load"
fi

# Fix permissions again
if [ -e /dev/hailo0 ]; then
    echo "Fixing permissions for /dev/hailo0..."
    sudo chmod 666 /dev/hailo0
fi

echo ""
echo "Diagnostic complete. Please review the output for any issues."
echo "If the Hailo device is still not accessible, please try rebooting the Raspberry Pi."
echo ""

# Final check
if [ -e /dev/hailo0 ] && [ -r /dev/hailo0 ] && [ -w /dev/hailo0 ]; then
    echo "✅ Hailo device is present and accessible"
    echo "Try running the verification script again:"
    echo "python3 $(dirname "$0")/verify_hailo_installation.py"
else
    echo "❌ Hailo device is still not accessible"
    echo "Please check the hardware connection and try rebooting."
fi
