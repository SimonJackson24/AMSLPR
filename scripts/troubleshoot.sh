#!/bin/bash

# VisiGate Troubleshooting Script
# This script helps diagnose issues with the VisiGate installation

echo "=== VisiGate Troubleshooting ==="
echo "Checking service status..."
sudo systemctl status visigate.service

echo "\nChecking service logs..."
sudo journalctl -u visigate.service --no-pager -n 50

echo "\nChecking if port 5001 is listening..."
sudo netstat -tuln | grep 5001

echo "\nChecking firewall status..."
sudo ufw status

echo "\nChecking run_server.py exists..."
ls -la /opt/visigate/run_server.py

echo "\nChecking Python virtual environment..."
ls -la /opt/visigate/venv/bin/python

echo "\nChecking network interfaces..."
ip addr

echo "\nTrying to access the service locally..."
curl -v http://localhost:5001/

echo "\nChecking Nginx configuration..."
sudo nginx -t

echo "\nChecking Nginx status..."
sudo systemctl status nginx
