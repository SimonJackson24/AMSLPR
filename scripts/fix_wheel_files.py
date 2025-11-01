#!/usr/bin/env python3
"""
Script to fix invalid wheel files by creating proper wheel metadata

Some wheel files may have been created incorrectly, missing the WHEEL metadata file.
This script will scan wheel files and attempt to add the missing metadata if needed.
"""

import os
import sys
import zipfile
import tempfile
import shutil
import glob
from pathlib import Path

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

def check_wheel_metadata(wheel_path):
    """Check if a wheel file has the required WHEEL metadata"""
    try:
        with zipfile.ZipFile(wheel_path, 'r') as zf:
            # Check for the dist-info directory
            dist_info_dirs = [name for name in zf.namelist() if name.endswith('.dist-info/') and 'egg-info' not in name.lower()]
            
            if not dist_info_dirs:
                dist_info_dirs = [name for name in zf.namelist() if '.dist-info/' in name and 'egg-info' not in name.lower()]
            
            if not dist_info_dirs:
                return False, "No .dist-info directory found"
            
            # Get the name of the dist-info directory
            dist_info_dir = dist_info_dirs[0]
            
            # Check for WHEEL file
            wheel_file = next((name for name in zf.namelist() if name.endswith('.dist-info/WHEEL')), None)
            
            if not wheel_file:
                return False, f"Missing WHEEL file in {dist_info_dir}"
            
            return True, "Wheel metadata is valid"
            
    except zipfile.BadZipFile:
        return False, "Not a valid zip file"
    except Exception as e:
        return False, f"Error checking wheel: {str(e)}"

def fix_wheel_metadata(wheel_path):
    """Try to fix wheel metadata by adding missing WHEEL file"""
    wheel_name = os.path.basename(wheel_path)
    print_colored(f"Fixing wheel metadata for {wheel_name}", "yellow")
    
    # Extract name and version from wheel filename
    parts = wheel_name.split('-')
    if len(parts) < 2:
        print_colored(f"  Cannot parse wheel name: {wheel_name}", "red")
        return False
    
    package_name = parts[0]
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_wheel = os.path.join(temp_dir, wheel_name)
        fixed_wheel = os.path.join(os.path.dirname(wheel_path), f"fixed_{wheel_name}")
        
        # Copy the wheel to the temporary directory
        shutil.copy2(wheel_path, temp_wheel)
        
        try:
            # Extract dist-info directory name from wheel
            dist_info_name = f"{package_name.replace('-', '_')}-{parts[1]}.dist-info"
            
            # Try to add missing WHEEL file
            with zipfile.ZipFile(temp_wheel, 'a') as zf:
                # Check if the dist-info directory exists
                dist_info_entries = [name for name in zf.namelist() if '.dist-info/' in name]
                
                if not dist_info_entries:
                    # Create dist-info directory
                    print_colored(f"  Creating {dist_info_name}/", "blue")
                    zf.writestr(f"{dist_info_name}/", "")
                else:
                    # Extract existing dist-info name
                    dist_info_name = os.path.dirname(dist_info_entries[0])
                
                # Add WHEEL file
                wheel_content = """Wheel-Version: 1.0
Generator: fix_wheel_files.py
Root-Is-Purelib: true
Tag: py3-none-any
"""
                print_colored(f"  Adding {dist_info_name}/WHEEL", "blue")
                zf.writestr(f"{dist_info_name}/WHEEL", wheel_content)
                
                # Add METADATA file if missing
                if f"{dist_info_name}/METADATA" not in zf.namelist():
                    metadata_content = f"""Metadata-Version: 2.1
Name: {package_name}
Version: {parts[1]}
Summary: Fixed wheel package
Home-page: 
Author: 
Author-email: 
License: 
"""
                    print_colored(f"  Adding {dist_info_name}/METADATA", "blue")
                    zf.writestr(f"{dist_info_name}/METADATA", metadata_content)
            
            # Copy fixed wheel back with new name
            shutil.copy2(temp_wheel, fixed_wheel)
            print_colored(f"  Fixed wheel saved as {os.path.basename(fixed_wheel)}", "green")
            return True
            
        except Exception as e:
            print_colored(f"  Error fixing wheel: {str(e)}", "red")
            if os.path.exists(fixed_wheel):
                os.remove(fixed_wheel)
            return False

def main():
    # Check for wheel directory argument
    if len(sys.argv) > 1:
        wheel_dir = sys.argv[1]
    else:
        wheel_dir = os.path.join('/opt', 'visigate', 'packages', 'offline')
    
    print_colored(f"Scanning for wheel files in: {wheel_dir}", "blue")
    
    # Find all wheel files
    wheel_files = glob.glob(os.path.join(wheel_dir, '*.whl'))
    
    if not wheel_files:
        print_colored("No wheel files found", "yellow")
        return
    
    print_colored(f"Found {len(wheel_files)} wheel files", "green")
    
    # Check each wheel file
    fixed_count = 0
    for wheel_path in wheel_files:
        wheel_name = os.path.basename(wheel_path)
        is_valid, message = check_wheel_metadata(wheel_path)
        
        if is_valid:
            print_colored(f"✅ {wheel_name}: {message}", "green")
        else:
            print_colored(f"❌ {wheel_name}: {message}", "red")
            if fix_wheel_metadata(wheel_path):
                fixed_count += 1
    
    print_colored(f"Fixed {fixed_count} wheel files", "green")

if __name__ == "__main__":
    main()