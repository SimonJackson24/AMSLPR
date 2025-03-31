#!/usr/bin/env python3
from onvif import ONVIFCamera
import asyncio
import sys

async def test_direct():
    try:
        print("Attempting to connect to camera at 192.168.1.222...")
        # Try common default credentials
        credentials = [
            ('admin', 'admin'),
            ('admin', ''),
            ('admin', 'Admin123'),
            ('root', 'root')
        ]
        
        for username, password in credentials:
            try:
                print(f"\nTrying credentials: {username}/{password}")
                cam = ONVIFCamera('192.168.1.222', 80, username, password, no_cache=True)
                await cam.update_xaddrs()
                
                # Get device information
                devicemgmt = cam.create_devicemgmt_service()
                info = await devicemgmt.GetDeviceInformation()
                print("\nConnection successful!")
                print(f"Manufacturer: {info.Manufacturer}")
                print(f"Model: {info.Model}")
                print(f"Firmware Version: {info.FirmwareVersion}")
                print(f"\nWorking credentials: {username}/{password}")
                return True
            except Exception as e:
                print(f"Failed with {username}/{password}: {str(e)}")
                continue
        
        print("\nCould not connect with any of the common credentials")
        return False
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_direct())
