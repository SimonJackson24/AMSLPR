#!/bin/bash

# AMSLPR Test Server Script
# This script tests if the AMSLPR server can run manually

echo "=== AMSLPR Test Server ==="
echo "Activating virtual environment..."
cd /opt/amslpr
source venv/bin/activate

echo "\nChecking Python version..."
python --version

echo "\nChecking if run_server.py exists..."
ls -la run_server.py

echo "\nChecking if required modules are installed..."
pip list | grep -E 'Flask|Pillow|numpy|opencv'

echo "\nTrying to run the server manually (will run for 10 seconds)..."
python run_server.py --port 5001 &
SERVER_PID=$!
sleep 10
kill $SERVER_PID

echo "\nDone testing server"
