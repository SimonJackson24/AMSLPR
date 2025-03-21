#!/bin/bash

set -e

echo "Hailo TPU Installation Fix Script"
echo "==============================="
echo ""

echo "Step 1: Checking for Hailo packages..."
PACKAGES_DIR="$(dirname "$0")/../packages/hailo"
if [ ! -d "$PACKAGES_DIR" ]; then
    echo "❌ Hailo packages directory not found at $PACKAGES_DIR"
    echo "Please download the Hailo SDK packages first."
    exit 1
fi

HAILO_WHEELS=($(find "$PACKAGES_DIR" -name "*.whl"))
HAILO_DEBS=($(find "$PACKAGES_DIR" -name "*.deb"))

if [ ${#HAILO_WHEELS[@]} -eq 0 ] && [ ${#HAILO_DEBS[@]} -eq 0 ]; then
    echo "❌ No Hailo packages found in $PACKAGES_DIR"
    echo "Please download the Hailo SDK packages first."
    exit 1
fi

echo "✅ Found $(( ${#HAILO_WHEELS[@]} + ${#HAILO_DEBS[@]} )) Hailo packages"

echo ""
echo "Step 2: Creating a dedicated virtual environment..."
VENV_DIR="$(dirname "$0")/../hailo_venv"

# Remove existing virtual environment if it exists
if [ -d "$VENV_DIR" ]; then
    echo "Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

# Create a new virtual environment
echo "Creating new virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo ""
echo "Step 3: Upgrading pip..."
pip install --upgrade pip

echo ""
echo "Step 4: Installing Hailo DEB packages..."
for deb in "${HAILO_DEBS[@]}"; do
    echo "Installing $deb..."
    sudo dpkg -i "$deb"
done

echo ""
echo "Step 5: Installing Hailo Python packages..."
# Sort wheels to install hailort before hailo_platform
for wheel in $(ls -v "${HAILO_WHEELS[@]}" | grep -i hailort | grep -v hailo_platform); do
    echo "Installing $wheel..."
    pip install --force-reinstall "$wheel"
done

for wheel in $(ls -v "${HAILO_WHEELS[@]}" | grep -i hailo_platform); do
    echo "Installing $wheel..."
    pip install --force-reinstall "$wheel"
done

# Install any remaining wheels
for wheel in $(ls -v "${HAILO_WHEELS[@]}" | grep -v hailort | grep -v hailo_platform); do
    echo "Installing $wheel..."
    pip install --force-reinstall "$wheel"
done

echo ""
echo "Step 6: Installing hailort directly from PyPI..."
pip install hailort

echo ""
echo "Step 7: Creating udev rules..."
echo 'SUBSYSTEM=="pci", ATTR{vendor}=="0x1e60", MODE="0666"' | sudo tee /etc/udev/rules.d/99-hailo.rules
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee -a /etc/udev/rules.d/99-hailo.rules
sudo udevadm control --reload-rules
sudo udevadm trigger

echo ""
echo "Step 8: Creating wrapper script..."
WRAPPER_SCRIPT="$(dirname "$0")/../run_with_hailo.sh"
cat > "$WRAPPER_SCRIPT" << EOL
#!/bin/bash
# This script runs commands with the Hailo virtual environment
source "$VENV_DIR/bin/activate"
exec "\$@"
EOL
chmod +x "$WRAPPER_SCRIPT"

echo ""
echo "Step 9: Verifying installation..."
python -c "import hailo_platform; print(f'hailo_platform version: {getattr(hailo_platform, "__version__", "unknown")}')" || echo "❌ Failed to import hailo_platform"
python -c "import hailort; print(f'hailort version: {getattr(hailort, "__version__", "unknown")}')" || echo "❌ Failed to import hailort"

echo ""
echo "Installation complete!"
echo "To use the Hailo SDK, run commands with: ./run_with_hailo.sh python3 your_script.py"
echo "For example: ./run_with_hailo.sh python3 scripts/verify_hailo_installation.py"

# Deactivate the virtual environment
deactivate
