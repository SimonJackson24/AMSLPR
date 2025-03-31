#!/usr/bin/env python3
import sys
import os
import logging
import nest_asyncio
import asyncio

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('onvif_test')

# Enable nested event loops
nest_asyncio.apply()

# Add virtual environment site-packages to Python path
venv_path = "/opt/amslpr/venv/lib/python3.11/site-packages"
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

try:
    from onvif2 import ONVIFCamera, ONVIFService, ONVIFError
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
                
                # Create camera instance
                cam = ONVIFCamera(camera_ip, 80, username, password, no_cache=True)
                logger.debug("Camera object created")
                
                # Get device information
                devicemgmt = cam.create_devicemgmt_service()
                logger.debug("Device management service created")
                
                # Get capabilities first
                logger.debug("Getting device capabilities...")
                resp = await devicemgmt.GetCapabilities()
                logger.debug(f"Capabilities: {resp}")
                
                # Now try to get device information
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
    # Get event loop
    loop = asyncio.get_event_loop()
    try:
        # Run the test
        loop.run_until_complete(test_direct())
    finally:
        loop.close()
