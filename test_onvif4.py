#!/usr/bin/env python3
import sys
import os
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('onvif_test')

# Add virtual environment site-packages to Python path
venv_path = "/opt/visigate/venv/lib/python3.11/site-packages"
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

try:
    from onvif2 import ONVIFCamera, ONVIFService, ONVIFError
    import asyncio
    logger.info("Successfully imported ONVIF modules")
except ImportError as e:
    logger.error(f"Failed to import ONVIF modules: {e}")
    sys.exit(1)

async def test_direct():
    try:
        camera_ip = "192.168.1.222"
        logger.info(f"Attempting to connect to camera at {camera_ip}")
        
        # Try common default credentials
        credentials = [
            ('admin', 'admin'),
            ('admin', ''),
            ('admin', 'Admin123'),
            ('root', 'root')
        ]
        
        for username, password in credentials:
            try:
                logger.info(f"Trying credentials: {username}/{password}")
                cam = ONVIFCamera(camera_ip, 80, username, password, no_cache=True, verbose=True)
                logger.debug("Camera object created")
                
                logger.debug("Updating xaddrs...")
                await cam.update_xaddrs()
                logger.debug("xaddrs updated successfully")
                
                # Get device information
                logger.debug("Creating device management service...")
                devicemgmt = cam.create_devicemgmt_service()
                logger.debug("Getting device information...")
                info = await devicemgmt.GetDeviceInformation()
                
                logger.info("\nConnection successful!")
                logger.info(f"Manufacturer: {info.Manufacturer}")
                logger.info(f"Model: {info.Model}")
                logger.info(f"Firmware Version: {info.FirmwareVersion}")
                logger.info(f"\nWorking credentials: {username}/{password}")
                return True
                
            except ONVIFError as e:
                logger.error(f"ONVIF Error with {username}/{password}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error with {username}/{password}: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                continue
        
        logger.warning("\nCould not connect with any of the common credentials")
        return False
        
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_direct())
