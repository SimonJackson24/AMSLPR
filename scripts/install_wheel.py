#!/usr/bin/env python3
"""
Robust wheel installation script

This script installs a wheel file with better error handling and fallbacks
for cases where uninstallation of existing packages fails due to missing RECORD files.
"""

import os
import sys
import subprocess
import argparse
import tempfile
import shutil
import glob
import re
import logging

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("wheel_installer")

def print_colored(message, color='green'):
    """Print colored message to terminal"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{message}{colors['end']}")

def get_package_name_from_wheel(wheel_path):
    """Extract package name from wheel filename"""
    wheel_filename = os.path.basename(wheel_path)
    parts = wheel_filename.split('-')
    
    # Convert from wheel format to pip package name (handling dashes)
    pkg_name = parts[0].replace('_', '-').lower()
    return pkg_name

def is_package_installed(package_name):
    """Check if a package is already installed"""
    try:
        # Run pip list and search for the package
        result = subprocess.run(['pip', 'list'], 
                               capture_output=True, 
                               text=True, 
                               check=True)
        
        # Parse output to check if package is installed
        pattern = fr'(?:^|\n){re.escape(package_name)}\s+'
        return bool(re.search(pattern, result.stdout, re.IGNORECASE))
    except subprocess.CalledProcessError:
        return False

def force_install_wheel(wheel_path, no_deps=False):
    """Force install a wheel without uninstalling existing package"""
    try:
        # Build the pip install command
        cmd = ['pip', 'install', '--force-reinstall']
        if no_deps:
            cmd.append('--no-deps')
        cmd.append(wheel_path)
        
        print_colored(f"Running: {' '.join(cmd)}", "blue")
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print_colored(f"Successfully installed {os.path.basename(wheel_path)}", "green")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print_colored(f"Error installing wheel: {e}", "red")
        print_colored(f"Error output: {e.stderr}", "red")
        return False, e.stderr

def regular_install_wheel(wheel_path, no_deps=False):
    """Regular install a wheel"""
    try:
        # Build the pip install command
        cmd = ['pip', 'install']
        if no_deps:
            cmd.append('--no-deps')
        cmd.append(wheel_path)
        
        print_colored(f"Running: {' '.join(cmd)}", "blue")
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print_colored(f"Successfully installed {os.path.basename(wheel_path)}", "green")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print_colored(f"Error installing wheel: {e}", "red")
        print_colored(f"Error output: {e.stderr}", "red")
        return False, e.stderr

def install_wheel(wheel_path, force=False, no_deps=False):
    """Install a wheel file with robust error handling"""
    wheel_basename = os.path.basename(wheel_path)
    print_colored(f"Installing wheel: {wheel_basename}", "blue")
    
    # Check if wheel file exists
    if not os.path.exists(wheel_path):
        print_colored(f"Wheel file not found: {wheel_path}", "red")
        return False
    
    # Get package name from wheel
    package_name = get_package_name_from_wheel(wheel_path)
    print_colored(f"Package name: {package_name}", "blue")
    
    # Check if package is already installed
    if is_package_installed(package_name):
        print_colored(f"Package {package_name} is already installed", "yellow")
        
        if force:
            # Try force reinstalling
            print_colored(f"Force reinstalling {package_name}...", "yellow")
            success, output = force_install_wheel(wheel_path, no_deps)
            if success:
                return True
            
            # If force install failed, try without uninstalling
            print_colored(f"Force install failed, trying install with --ignore-installed...", "yellow")
            cmd = ['pip', 'install', '--ignore-installed']
            if no_deps:
                cmd.append('--no-deps')
            cmd.append(wheel_path)
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                print_colored(f"Successfully installed {wheel_basename} with --ignore-installed", "green")
                return True
            except subprocess.CalledProcessError as e:
                print_colored(f"Error installing wheel with --ignore-installed: {e}", "red")
                print_colored(f"Error output: {e.stderr}", "red")
                return False
        else:
            # Skip installation if not forcing
            print_colored(f"Skipping installation of {package_name} (already installed)", "yellow")
            return True
    else:
        # Package not installed, just install it
        success, output = regular_install_wheel(wheel_path, no_deps)
        return success

def main():
    parser = argparse.ArgumentParser(description='Robust wheel installer')
    parser.add_argument('wheel_path', help='Path to the wheel file to install')
    parser.add_argument('--force', action='store_true', help='Force reinstall if already installed')
    parser.add_argument('--no-deps', action='store_true', help="Don't install dependencies")
    args = parser.parse_args()
    
    print_colored(f"Robust Wheel Installer", "blue")
    print_colored(f"====================", "blue")
    
    success = install_wheel(args.wheel_path, args.force, args.no_deps)
    
    if success:
        print_colored("Wheel installed successfully", "green")
        sys.exit(0)
    else:
        print_colored("Wheel installation failed", "red")
        sys.exit(1)

if __name__ == "__main__":
    main()