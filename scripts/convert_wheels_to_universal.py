#!/usr/bin/env python3
"""
Script to convert platform-specific wheels to universal wheels

Some wheels are built for specific platforms like linux_armv7l which may not match
the current platform. This script converts them to universal py3-none-any.whl wheels.
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

def is_platform_specific(wheel_path):
    """Check if a wheel file is platform-specific"""
    wheel_name = os.path.basename(wheel_path)
    parts = wheel_name.split('-')
    
    # Check for platform tag
    if len(parts) < 5:
        return False
    
    # Check if it's already a universal wheel
    if parts[-1] == 'any.whl':
        return False
    
    return True

def convert_to_universal(wheel_path):
    """Convert a platform-specific wheel to a universal wheel"""
    wheel_name = os.path.basename(wheel_path)
    print_colored(f"Converting {wheel_name} to universal wheel", "yellow")
    
    # Parse wheel name parts
    parts = wheel_name.split('-')
    if len(parts) < 5:
        print_colored(f"  Cannot parse wheel name: {wheel_name}", "red")
        return False
    
    package_name = parts[0]
    version = parts[1]
    
    # Create new wheel name (py3-none-any.whl)
    new_parts = parts[:-3] + ['py3', 'none', 'any.whl']
    new_wheel_name = '-'.join(new_parts)
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_wheel = os.path.join(temp_dir, wheel_name)
        universal_wheel = os.path.join(os.path.dirname(wheel_path), new_wheel_name)
        
        # Copy the wheel to the temporary directory
        shutil.copy2(wheel_path, temp_wheel)
        
        try:
            # Extract dist-info directory name from wheel
            dist_info_name = f"{package_name.replace('-', '_')}-{version}.dist-info"
            
            with zipfile.ZipFile(temp_wheel, 'r') as zf_in:
                # Check for WHEEL file
                wheel_file = next((name for name in zf_in.namelist() if name.endswith('.dist-info/WHEEL')), None)
                
                if not wheel_file:
                    print_colored(f"  Missing WHEEL file in {wheel_name}, cannot convert", "red")
                    return False
                
                # Read the WHEEL file
                wheel_content = zf_in.read(wheel_file).decode('utf-8')
                
                # Modify the WHEEL file to make it universal
                new_wheel_content = []
                for line in wheel_content.splitlines():
                    if line.startswith('Tag:'):
                        line = 'Tag: py3-none-any'
                    elif line.startswith('Root-Is-Purelib:'):
                        line = 'Root-Is-Purelib: true'
                    new_wheel_content.append(line)
                
                # Create a new wheel file with modified content
                with zipfile.ZipFile(universal_wheel, 'w') as zf_out:
                    # Copy all files except the WHEEL file
                    for item in zf_in.infolist():
                        if item.filename != wheel_file:
                            data = zf_in.read(item.filename)
                            zf_out.writestr(item, data)
                    
                    # Add the modified WHEEL file
                    zf_out.writestr(wheel_file, '\n'.join(new_wheel_content))
            
            print_colored(f"  Created universal wheel: {new_wheel_name}", "green")
            return True
            
        except Exception as e:
            print_colored(f"  Error converting wheel: {str(e)}", "red")
            if os.path.exists(universal_wheel):
                os.remove(universal_wheel)
            return False

def main():
    # Check for wheel directory argument
    if len(sys.argv) > 1:
        wheel_dir = sys.argv[1]
    else:
        wheel_dir = os.path.join('/opt', 'amslpr', 'packages', 'offline')
    
    print_colored(f"Scanning for platform-specific wheels in: {wheel_dir}", "blue")
    
    # Find all wheel files
    wheel_files = glob.glob(os.path.join(wheel_dir, '*.whl'))
    
    if not wheel_files:
        print_colored("No wheel files found", "yellow")
        return
    
    print_colored(f"Found {len(wheel_files)} wheel files", "green")
    
    # Process each wheel file
    converted_count = 0
    already_universal = 0
    
    for wheel_path in wheel_files:
        wheel_name = os.path.basename(wheel_path)
        
        if not is_platform_specific(wheel_path):
            print_colored(f"✅ {wheel_name}: Already a universal wheel", "green")
            already_universal += 1
            continue
        
        print_colored(f"🔄 {wheel_name}: Converting to universal format", "yellow")
        if convert_to_universal(wheel_path):
            converted_count += 1
    
    print_colored(f"Converted {converted_count} wheels to universal format", "green")
    print_colored(f"{already_universal} wheels were already universal", "green")

if __name__ == "__main__":
    main()