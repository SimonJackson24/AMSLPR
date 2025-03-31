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
    from onvif import ONVIFCamera, ONVIFService, ONVIFError
    logger.info("Successfully imported ONVIF modules")
except ImportError as e:
    logger.error(f"Failed to import ONVIF modules: {e}")
    sys.exit(1)

async def init_onvif_client(camera_ip, username, password):
    mycam = ONVIFCamera(camera_ip, 80, username, password, no_cache=True)
    await mycam.update_xaddrs()
    return mycam

async def test_direct():
    try:
        camera_ip = "192.168.1.222"
        username = "admin"
        password = "Aut0mate2048"
        
        logger.info(f"Attempting to connect to camera at {camera_ip}")
        logger.info(f"Using credentials: {username}/{password}")
        
        # Initialize camera with async
        cam = await init_onvif_client(camera_ip, username, password)
        logger.debug("Camera object created and initialized")
        
        # Get device information
        devicemgmt = cam.create_devicemgmt_service()
        logger.debug("Device management service created")
        
        # Get device information
        logger.debug("Getting device information...")
        info = await devicemgmt.GetDeviceInformation()
        
        logger.info("\nConnection successful!")
        logger.info(f"Manufacturer: {info.Manufacturer}")
        logger.info(f"Model: {info.Model}")
        logger.info(f"Firmware Version: {info.FirmwareVersion}")
        
        # Get capabilities
        logger.debug("Getting device capabilities...")
        caps = await devicemgmt.GetCapabilities({'Category': 'All'})
        
        if hasattr(caps, 'Media') and caps.Media:
            logger.info("\nMedia capabilities found")
            # Create media service
            media = cam.create_media_service()
            
            # Get profiles
            logger.debug("Getting media profiles...")
            profiles = await media.GetProfiles()
            
            # Get stream URIs for each profile
            for profile in profiles:
                logger.info(f"\nProfile: {profile.Name}")
                stream_setup = {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}}
                uri = await media.GetStreamUri({'ProfileToken': profile.token, 'StreamSetup': stream_setup})
                logger.info(f"Stream URI: {uri.Uri}")
        
        return True
        
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
