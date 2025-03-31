from onvif import ONVIFCamera
import asyncio
import sys

async def test_camera():
    try:
        # Try common username/password combinations
        credentials = [
            ('admin', 'admin'),
            ('admin', ''),
            ('admin', 'Admin123'),
            ('root', 'root'),
            ('service', 'service')
        ]
        
        for username, password in credentials:
            try:
                print(f"\nTrying credentials: {username}/{password}")
                mycam = ONVIFCamera('192.168.1.222', 80, username, password, no_cache=True)
                await mycam.update_xaddrs()
                
                # Get device information
                info = await mycam.devicemgmt.GetDeviceInformation()
                print("\nSuccess! Camera information:")
                print(f"Manufacturer: {info.Manufacturer}")
                print(f"Model: {info.Model}")
                print(f"Serial Number: {info.SerialNumber}")
                print(f"Hardware ID: {info.HardwareId}")
                print(f"Firmware Version: {info.FirmwareVersion}")
                
                # These were the working credentials
                print(f"\nWorking credentials: {username}/{password}")
                return
                
            except Exception as e:
                print(f"Failed with {username}/{password}: {str(e)}")
                continue
                
        print("\nCould not connect with any of the common credentials")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_camera())
