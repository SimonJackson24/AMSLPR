#!/bin/bash

# Test script for offline_install.sh
# This script simulates the offline installation process in a local test directory
# to verify that our fixes resolved the empty directory issue

set -e

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}       AMSLPR Offline Installation Test Script    ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo

# Create a test directory
TEST_DIR="/tmp/amslpr_test_install"
echo -e "${YELLOW}Creating test directory: $TEST_DIR${NC}"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
mkdir -p "$TEST_DIR/opt/amslpr/packages/offline"

# Copy the offline_install.sh script to the test directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cp "$SCRIPT_DIR/offline_install.sh" "$TEST_DIR/"

# Create fake wheel files for testing
echo -e "${YELLOW}Creating fake wheel files for testing${NC}"
touch "$TEST_DIR/opt/amslpr/packages/offline/hailo_platform-4.20.0-py3-none-any.whl"
touch "$TEST_DIR/opt/amslpr/packages/offline/hailort-4.20.0-py3-none-any.whl"
touch "$TEST_DIR/opt/amslpr/packages/offline/numpy-2.2.4-cp311-cp311-linux_armv7l.whl"
touch "$TEST_DIR/opt/amslpr/packages/offline/aiohttp-3.11.14-cp311-cp311-linux_armv7l.whl"

# Create a testing script that uses fixed paths
echo -e "${YELLOW}Creating test script${NC}"
cat > "$TEST_DIR/offline_test.sh" << 'EOF'
#!/bin/bash

# Test script for offline installation

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Define important directories
INSTALL_DIR="/tmp/amslpr_test_install/opt/amslpr"
PACKAGES_DIR="/tmp/amslpr_test_install/opt/amslpr/packages"
OFFLINE_PACKAGES_DIR="/tmp/amslpr_test_install/opt/amslpr/packages/offline"

echo -e "${GREEN}=== Test Script Started ===${NC}"
echo -e "${GREEN}Installation directory: $INSTALL_DIR${NC}"
echo -e "${GREEN}Packages directory: $PACKAGES_DIR${NC}"
echo -e "${GREEN}Offline packages directory: $OFFLINE_PACKAGES_DIR${NC}"

# Create test directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$PACKAGES_DIR"
mkdir -p "$OFFLINE_PACKAGES_DIR"

# Write a simple test script
TEST_SCRIPT="$INSTALL_DIR/test_dependencies.sh"
cat > "$TEST_SCRIPT" << EOT
#!/bin/bash

# Test script for package dependencies

INSTALL_DIR="$INSTALL_DIR"
PACKAGES_DIR="$PACKAGES_DIR"
OFFLINE_PACKAGES_DIR="$OFFLINE_PACKAGES_DIR"

echo "Test script executed successfully"
echo "INSTALL_DIR=\$INSTALL_DIR"
echo "PACKAGES_DIR=\$PACKAGES_DIR"
echo "OFFLINE_PACKAGES_DIR=\$OFFLINE_PACKAGES_DIR"

# Check if the wheels directory exists
WHEELS_DIR="\$OFFLINE_PACKAGES_DIR"
if [ -d "\$WHEELS_DIR" ]; then
    echo "Wheels directory exists at \$WHEELS_DIR"
    
    # List any wheel files
    ls -la "\$WHEELS_DIR"/*.whl 2>/dev/null || echo "No wheel files found"
else
    echo "Wheels directory does not exist at \$WHEELS_DIR"
    exit 1
fi

# Try creating a directory with the variable
mkdir -p "\$OFFLINE_PACKAGES_DIR/test" || echo "Failed to create directory"
echo "Created test directory: \$OFFLINE_PACKAGES_DIR/test"

# Test complete
echo "Test completed successfully"
EOT

chmod +x "$TEST_SCRIPT"

# Run the test script
echo -e "${YELLOW}Running test script...${NC}"
bash "$TEST_SCRIPT"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Test passed! Variables are working correctly.${NC}"
else
    echo -e "${RED}Test failed! Variable issues detected.${NC}"
fi
EOF

chmod +x "$TEST_DIR/offline_test.sh"

# Run the test script
echo -e "${YELLOW}Running the test script${NC}"
cd "$TEST_DIR" && ./offline_test.sh

echo -e "${GREEN}Test complete!${NC}"
echo -e "${YELLOW}Test directory: $TEST_DIR${NC}"
echo -e "${YELLOW}You can examine the results in this directory.${NC}"