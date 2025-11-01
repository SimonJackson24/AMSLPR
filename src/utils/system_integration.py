
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import os
import logging
import subprocess
import shutil
import platform
from pathlib import Path

# Configure logging
logger = logging.getLogger('VisiGate.system_integration')

class SystemIntegration:
    """
    Handles system-level integration tasks for the VisiGate system.
    This includes checking system dependencies, managing services,
    and interacting with the operating system.
    """
    
    def __init__(self, config):
        """
        Initialize the system integration module.
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.is_raspberry_pi = self._check_if_raspberry_pi()
        logger.info(f"System integration initialized. Raspberry Pi: {self.is_raspberry_pi}")
    
    def _check_if_raspberry_pi(self):
        """
        Check if the system is running on a Raspberry Pi.
        
        Returns:
            bool: True if running on a Raspberry Pi, False otherwise
        """
        # Check if running on Linux
        if platform.system() != 'Linux':
            return False
        
        # Check for Raspberry Pi model in /proc/cpuinfo
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            return 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo
        except Exception as e:
            logger.warning(f"Failed to check if system is Raspberry Pi: {e}")
            return False
    
    def check_dependencies(self):
        """
        Check if all required system dependencies are installed.
        
        Returns:
            dict: Dictionary of dependencies and their status
        """
        dependencies = {
            'python3': self._check_command('python3 --version'),
            'opencv': self._check_python_module('cv2'),
            'tesseract': self._check_command('tesseract --version'),
            'sqlite3': self._check_command('sqlite3 --version'),
        }
        
        # Check Raspberry Pi specific dependencies
        if self.is_raspberry_pi:
            dependencies['RPi.GPIO'] = self._check_python_module('RPi.GPIO')
            dependencies['picamera'] = self._check_python_module('picamera')
        
        logger.info(f"Dependency check results: {dependencies}")
        return dependencies
    
    def _check_command(self, command):
        """
        Check if a command is available on the system.
        
        Args:
            command (str): Command to check
            
        Returns:
            bool: True if command is available, False otherwise
        """
        try:
            subprocess.run(
                command.split(), 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=True
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _check_python_module(self, module_name):
        """
        Check if a Python module is installed.
        
        Args:
            module_name (str): Name of the module to check
            
        Returns:
            bool: True if module is installed, False otherwise
        """
        try:
            subprocess.run(
                [sys.executable, '-c', f"import {module_name}"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=True
            )
            return True
        except subprocess.SubprocessError:
            return False
    
    def install_service(self):
        """
        Install the VisiGate service to start on boot.
        
        Returns:
            bool: True if service was installed successfully, False otherwise
        """
        if not self.is_raspberry_pi:
            logger.warning("Service installation is only supported on Raspberry Pi")
            return False
        
        try:
            # Get project root directory
            project_root = Path(__file__).parent.parent.parent
            
            # Source and destination paths for service file
            service_src = project_root / 'scripts' / 'visigate.service'
            service_dest = '/etc/systemd/system/visigate.service'
            
            # Check if running as root
            if os.geteuid() != 0:
                logger.error("Service installation requires root privileges")
                return False
            
            # Copy service file
            shutil.copy(service_src, service_dest)
            
            # Reload systemd and enable service
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', 'enable', 'visigate.service'], check=True)
            
            logger.info("VisiGate service installed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to install service: {e}")
            return False
    
    def start_service(self):
        """
        Start the VisiGate service.
        
        Returns:
            bool: True if service was started successfully, False otherwise
        """
        if not self.is_raspberry_pi:
            logger.warning("Service management is only supported on Raspberry Pi")
            return False
        
        try:
            subprocess.run(['systemctl', 'start', 'visigate.service'], check=True)
            logger.info("VisiGate service started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            return False
    
    def stop_service(self):
        """
        Stop the VisiGate service.
        
        Returns:
            bool: True if service was stopped successfully, False otherwise
        """
        if not self.is_raspberry_pi:
            logger.warning("Service management is only supported on Raspberry Pi")
            return False
        
        try:
            subprocess.run(['systemctl', 'stop', 'visigate.service'], check=True)
            logger.info("VisiGate service stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            return False
    
    def get_service_status(self):
        """
        Get the status of the VisiGate service.
        
        Returns:
            str: Service status or error message
        """
        if not self.is_raspberry_pi:
            return "Service management is only supported on Raspberry Pi"
        
        try:
            result = subprocess.run(
                ['systemctl', 'status', 'visigate.service'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return f"Error: {str(e)}"
    
    def get_system_info(self):
        """
        Get system information.
        
        Returns:
            dict: Dictionary containing system information
        """
        info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'hostname': platform.node(),
            'is_raspberry_pi': self.is_raspberry_pi,
        }
        
        # Get Raspberry Pi specific information
        if self.is_raspberry_pi:
            try:
                # Get CPU temperature
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read().strip()) / 1000
                info['cpu_temperature'] = f"{temp:.1f}°C"
                
                # Get memory information
                mem_info = {}
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if 'MemTotal' in line or 'MemFree' in line or 'MemAvailable' in line:
                            key, value = line.split(':', 1)
                            mem_info[key.strip()] = value.strip()
                info['memory'] = mem_info
                
                # Get disk usage
                disk = shutil.disk_usage('/')
                info['disk'] = {
                    'total': f"{disk.total / (1024**3):.1f} GB",
                    'used': f"{disk.used / (1024**3):.1f} GB",
                    'free': f"{disk.free / (1024**3):.1f} GB",
                    'percent_used': f"{disk.used / disk.total * 100:.1f}%"
                }
                
                # Get IP address
                ip_cmd = subprocess.run(
                    ['hostname', '-I'], 
                    stdout=subprocess.PIPE, 
                    text=True
                )
                info['ip_address'] = ip_cmd.stdout.strip()
            except Exception as e:
                logger.error(f"Failed to get Raspberry Pi system info: {e}")
        
        logger.debug(f"System info: {info}")
        return info

# Add import for sys module if used directly
if __name__ == "__main__":
    import sys
    from src.config.settings import load_config
    
    # Load configuration
    config = load_config()
    
    # Initialize system integration
    system = SystemIntegration(config)
    
    # Check dependencies
    dependencies = system.check_dependencies()
    print("Dependencies:")
    for dep, status in dependencies.items():
        print(f"  {dep}: {'Installed' if status else 'Not Installed'}")
    
    # Get system information
    system_info = system.get_system_info()
    print("\nSystem Information:")
    for key, value in system_info.items():
        print(f"  {key}: {value}")
