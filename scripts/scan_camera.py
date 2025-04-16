#!/usr/bin/env python3

'''
Scan camera using nmap and extract information from headers
'''

import subprocess
import re
import sys
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CameraScan')

def scan_camera(ip):
    '''
    Scan camera using nmap and extract information
    '''
    try:
        logger.info(f"Scanning camera at {ip}")
        
        # Run nmap scan with service detection
        cmd = ['nmap', '-sV', '-p', '80,554,8000,8080,8081,8899', ip]
        logger.info(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout
        
        logger.info(f"Nmap scan results:\n{output}")
        
        # Extract service information
        service_info = {}
        for line in output.splitlines():
            # Look for service info lines
            if 'open' in line and 'http' in line:
                match = re.search(r'(\d+)/tcp\s+open\s+(\S+)\s+(.*)', line)
                if match:
                    port, service, details = match.groups()
                    service_info[port] = details
                    
        # Try to get HTTP headers
        try:
            logger.info(f"Getting HTTP headers from {ip}")
            response = requests.head(f"http://{ip}", timeout=2)
            headers = response.headers
            
            logger.info(f"HTTP headers:\n{headers}")
            
            # Look for server header which often contains manufacturer info
            if 'Server' in headers:
                server = headers['Server']
                logger.info(f"Server header: {server}")
                
                # Try to extract manufacturer
                manufacturer = 'Unknown'
                if 'hikvision' in server.lower():
                    manufacturer = 'Hikvision'
                elif 'axis' in server.lower():
                    manufacturer = 'Axis'
                elif 'dahua' in server.lower():
                    manufacturer = 'Dahua'
                
                print(f"\nCamera at {ip}")
                print(f"Manufacturer: {manufacturer} (from HTTP headers)")
                print(f"Server: {server}")
                
                return {
                    'ip': ip,
                    'manufacturer': manufacturer,
                    'server': server,
                    'headers': dict(headers)
                }
        except Exception as e:
            logger.error(f"Error getting HTTP headers: {str(e)}")
        
        # If we got service info but no headers
        if service_info:
            # Try to extract manufacturer from service details
            manufacturer = 'Unknown'
            model = 'Unknown'
            
            for port, details in service_info.items():
                if 'hikvision' in details.lower():
                    manufacturer = 'Hikvision'
                elif 'axis' in details.lower():
                    manufacturer = 'Axis'
                elif 'dahua' in details.lower():
                    manufacturer = 'Dahua'
            
            print(f"\nCamera at {ip}")
            print(f"Manufacturer: {manufacturer} (from nmap service detection)")
            print(f"Service details: {service_info}")
            
            return {
                'ip': ip,
                'manufacturer': manufacturer,
                'service_info': service_info
            }
        
        print(f"\nCamera at {ip}")
        print("Could not determine manufacturer information")
        return {'ip': ip, 'manufacturer': 'Unknown'}
        
    except Exception as e:
        logger.error(f"Error scanning camera: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'ip': ip, 'manufacturer': 'Unknown', 'error': str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scan_camera.py <ip>")
        sys.exit(1)
        
    ip = sys.argv[1]
    scan_camera(ip)
