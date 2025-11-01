#!/usr/bin/env python3
"""
Fix VisiGate service to use the virtual environment Python
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger()

# Get project root
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENV_PATH = PROJECT_ROOT / 'venv'

def run_command(command, as_root=False):
    """Run a shell command and return output"""
    cmd = f"sudo {command}" if as_root else command
    log.info(f"Running: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            log.error(f"Command failed with error: {result.stderr}")
            return False, result.stderr
        
        return True, result.stdout
    except Exception as e:
        log.error(f"Error running command: {e}")
        return False, str(e)

def get_current_service_file():
    """Get the current service file content"""
    service_path = '/etc/systemd/system/visigate.service'
    
    success, output = run_command(f"cat {service_path}", as_root=True)
    if not success:
        log.error(f"Failed to read service file: {output}")
        return None
    
    return output

def update_service_for_venv():
    """Update the VisiGate service to use the virtual environment Python"""
    log.info("\n===== FIXING VisiGate SERVICE TO USE VIRTUAL ENVIRONMENT =====\n")
    
    # Verify virtual environment exists
    venv_python = VENV_PATH / 'bin' / 'python'
    
    if not venv_python.exists():
        log.error(f"Virtual environment Python not found at {venv_python}")
        log.error("Please run the install_tensorflow.py script first")
        return False
    
    log.info(f"Found virtual environment Python at {venv_python}")
    
    # Get current service file
    service_content = get_current_service_file()
    if not service_content:
        return False
    
    # Check if already using venv
    if str(venv_python) in service_content:
        log.info("Service is already configured to use the virtual environment")
        return True
    
    # Parse and update service file
    new_lines = []
    found_exec_start = False
    
    for line in service_content.splitlines():
        if line.strip().startswith('ExecStart=') and 'python' in line:
            # Replace path to Python with venv Python
            parts = line.split()
            for i, part in enumerate(parts):
                if 'python' in part and not 'venv' in part:
                    parts[i] = str(venv_python)
                    found_exec_start = True
                    break
            
            new_line = ' '.join(parts)
            new_lines.append(new_line)
            log.info(f"Updated service ExecStart:\n  From: {line}\n  To:   {new_line}")
        else:
            new_lines.append(line)
    
    if not found_exec_start:
        log.error("Could not find Python in ExecStart line of service file")
        return False
    
    # Write new service file to temporary location
    temp_file = '/tmp/visigate.service'
    with open(temp_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    # Install new service file
    success, output = run_command(f"cp {temp_file} /etc/systemd/system/visigate.service", as_root=True)
    if not success:
        log.error(f"Failed to update service file: {output}")
        return False
    
    # Reload systemd
    success, output = run_command("systemctl daemon-reload", as_root=True)
    if not success:
        log.error(f"Failed to reload systemd: {output}")
        return False
    
    log.info("\n===== SERVICE UPDATED SUCCESSFULLY =====\n")
    log.info("The VisiGate service is now configured to use the virtual environment Python.")
    log.info("This will enable detection of TensorFlow and Hailo TPU.")
    
    # Restart service
    log.info("\nRestarting VisiGate service...")
    success, output = run_command("systemctl restart visigate", as_root=True)
    if not success:
        log.error(f"Failed to restart service: {output}")
        return False
    
    log.info("VisiGate service restarted successfully")
    log.info("\nThe TPU detection should now work correctly. Please check the OCR settings page.")
    return True

if __name__ == "__main__":
    # Check if running as root
    if os.geteuid() != 0:
        log.error("This script must be run as root (with sudo)")
        log.error("Please run: sudo python scripts/fix_service_for_venv.py")
        sys.exit(1)
    
    success = update_service_for_venv()
    sys.exit(0 if success else 1)
