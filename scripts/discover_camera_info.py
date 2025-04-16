#!/usr/bin/env python3

'''
Test script to discover camera information using WS-Discovery without authentication
'''

import socket
import time
import logging
import re
import sys
import requests
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CameraDiscovery')

def discover_camera_info(target_ip=None, timeout=5):
    '''
    Discover camera information using WS-Discovery
    If target_ip is provided, only return info for that camera
    '''
    discovered_cameras = []
    
    try:
        # Create UDP socket for WS-Discovery
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.settimeout(timeout)

        # WS-Discovery probe message
        message = '''<?xml version="1.0" encoding="UTF-8"?>
        <e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
                   xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
                   xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
            <e:Header>
                <w:MessageID>uuid:84ede3de-7dec-11d0-c360-f01234567890</w:MessageID>
                <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
                <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
            </e:Header>
            <e:Body>
                <d:Probe>
                    <d:Types>dn:NetworkVideoTransmitter</d:Types>
                </d:Probe>
            </e:Body>
        </e:Envelope>'''

        # Send WS-Discovery probe
        logger.info("Sending WS-Discovery probe...")
        sock.sendto(message.encode('utf-8'), ('239.255.255.250', 3702))

        # Listen for responses
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(65535)
                if data:
                    ip = addr[0]
                    
                    # If target IP is specified, only process that camera
                    if target_ip and ip != target_ip:
                        continue
                        
                    logger.info(f"Received response from {ip}")
                    
                    # Parse the response to extract device information
                    response_str = data.decode('utf-8')
                    
                    # Extract XAddrs (device service URLs)
                    xaddrs_match = re.search(r'<d:XAddrs>(.*?)</d:XAddrs>', response_str)
                    if xaddrs_match:
                        xaddrs = xaddrs_match.group(1).strip()
                        device_urls = xaddrs.split()
                        
                        # Extract device metadata
                        types_match = re.search(r'<d:Types>(.*?)</d:Types>', response_str)
                        types = types_match.group(1) if types_match else 'Unknown'
                        
                        # Get device URL
                        device_url = device_urls[0] if device_urls else None
                        if device_url:
                            # Parse URL to get port
                            parsed_url = urlparse(device_url)
                            port = parsed_url.port or 80
                            
                            # Try to get device info from the device URL without authentication
                            try:
                                # Try to get device info using SOAP request without authentication
                                logger.info(f"Getting device info from {device_url}")
                                
                                # Create SOAP request for GetDeviceInformation
                                soap_request = '''<?xml version="1.0" encoding="UTF-8"?>
                                <s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
                                    <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                                        <GetDeviceInformation xmlns="http://www.onvif.org/ver10/device/wsdl"/>
                                    </s:Body>
                                </s:Envelope>'''
                                
                                headers = {
                                    'Content-Type': 'application/soap+xml; charset=utf-8',
                                    'SOAPAction': '"http://www.onvif.org/ver10/device/wsdl/GetDeviceInformation"'
                                }
                                
                                # Send request with a short timeout
                                response = requests.post(device_url, data=soap_request, headers=headers, timeout=2)
                                
                                # Check if we got device info or auth error
                                if response.status_code == 200:
                                    # Parse manufacturer and model from response
                                    manufacturer_match = re.search(r'<tds:Manufacturer>(.*?)</tds:Manufacturer>', response.text)
                                    model_match = re.search(r'<tds:Model>(.*?)</tds:Model>', response.text)
                                    firmware_match = re.search(r'<tds:FirmwareVersion>(.*?)</tds:FirmwareVersion>', response.text)
                                    
                                    manufacturer = manufacturer_match.group(1) if manufacturer_match else 'Unknown'
                                    model = model_match.group(1) if model_match else 'Unknown'
                                    firmware = firmware_match.group(1) if firmware_match else 'Unknown'
                                    
                                    logger.info(f"Found camera: {manufacturer} {model}, Firmware: {firmware}")
                                    
                                    camera_info = {
                                        'ip': ip,
                                        'port': port,
                                        'manufacturer': manufacturer,
                                        'model': model,
                                        'firmware': firmware,
                                        'url': device_url
                                    }
                                    
                                    discovered_cameras.append(camera_info)
                                    print(f"\nCamera at {ip}:{port}")
                                    print(f"Manufacturer: {manufacturer}")
                                    print(f"Model: {model}")
                                    print(f"Firmware: {firmware}")
                                    print(f"URL: {device_url}")
                                    
                                elif response.status_code in [401, 403]:
                                    # Authentication required, but we can still extract some info from WS-Discovery
                                    logger.info(f"Authentication required for {ip}")
                                    
                                    # Try to extract info from the device URL
                                    # Example: http://192.168.1.222/onvif/device_service for a Hikvision camera
                                    url_parts = device_url.split('/')
                                    if len(url_parts) >= 3:
                                        domain = url_parts[2].split(':')[0]  # Extract domain without port
                                        manufacturer = 'Unknown'
                                        
                                        # Try to guess manufacturer from URL or response
                                        if 'hikvision' in device_url.lower() or 'hikvision' in response.text.lower():
                                            manufacturer = 'Hikvision'
                                        elif 'axis' in device_url.lower() or 'axis' in response.text.lower():
                                            manufacturer = 'Axis'
                                        elif 'dahua' in device_url.lower() or 'dahua' in response.text.lower():
                                            manufacturer = 'Dahua'
                                        
                                        camera_info = {
                                            'ip': ip,
                                            'port': port,
                                            'manufacturer': manufacturer,
                                            'model': 'Unknown (Auth Required)',
                                            'firmware': 'Unknown (Auth Required)',
                                            'url': device_url
                                        }
                                        
                                        discovered_cameras.append(camera_info)
                                        print(f"\nCamera at {ip}:{port}")
                                        print(f"Manufacturer: {manufacturer} (guessed from URL)")
                                        print(f"Authentication required for more details")
                                        print(f"URL: {device_url}")
                            
                            except Exception as e:
                                logger.error(f"Error getting device info: {str(e)}")
                                # Still add basic camera info from discovery
                                camera_info = {
                                    'ip': ip,
                                    'port': port,
                                    'manufacturer': 'Unknown',
                                    'model': 'Unknown',
                                    'firmware': 'Unknown',
                                    'url': device_url
                                }
                                discovered_cameras.append(camera_info)
                    
            except socket.timeout:
                pass

        sock.close()
        
        if not discovered_cameras:
            logger.info("No cameras found")
            if target_ip:
                print(f"No camera found at {target_ip}")
            else:
                print("No cameras found on the network")
        
        return discovered_cameras
        
    except Exception as e:
        logger.error(f"Error during discovery: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

if __name__ == "__main__":
    target_ip = sys.argv[1] if len(sys.argv) > 1 else None
    discover_camera_info(target_ip)
