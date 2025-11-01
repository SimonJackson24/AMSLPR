# VisiGate Hardware Setup Guide

This guide provides instructions for setting up the hardware components of the Vision-Based Access Control System (VisiGate) system.

## Hardware Requirements

### Core Components

- **Raspberry Pi 4** (4GB RAM recommended)
- **Camera Module**
  - Raspberry Pi Camera Module v2 or compatible camera
  - Weatherproof camera housing for outdoor installation
- **Relay Module** for barrier control
  - 1-channel or 2-channel relay module (depending on your barrier system)
- **Power Supply**
  - 5V/3A power supply for Raspberry Pi
  - Appropriate power for your barrier system
- **Storage**
  - 32GB+ microSD card (Class 10 or better)
- **Network Connectivity**
  - Ethernet cable (recommended for reliability)
  - Or Wi-Fi connectivity

### Optional Components

- **Infrared Illuminator** for night-time operation
- **Motion Sensor** to trigger the system only when a vehicle is present
- **Weatherproof Enclosure** for the Raspberry Pi and electronics
- **UPS** (Uninterruptible Power Supply) for power backup

## Physical Setup

### Camera Positioning

The camera should be positioned to capture clear images of license plates. Consider these guidelines:

1. **Height**: Mount the camera at a height of 1-1.5 meters (3-5 feet)
2. **Angle**: Position at a slight downward angle (15-30 degrees) facing the vehicle's front or rear
3. **Distance**: Optimal distance is 2-3 meters (6-10 feet) from where vehicles will stop
4. **Field of View**: Ensure the camera's field of view covers the entire width of the lane

### Wiring Diagram

#### Raspberry Pi GPIO Connections

| Component | Raspberry Pi GPIO Pin | Description |
|-----------|----------------------|-------------|
| Camera    | Camera CSI Port      | Connect the camera ribbon cable to the CSI port |
| Relay (Entry Barrier) | GPIO 17 (Pin 11)     | Connect to the relay control pin |
| Relay (Exit Barrier)  | GPIO 27 (Pin 13)     | Connect to the relay control pin (if using separate exit barrier) |
| Ground    | GND (Pin 6)          | Connect to the ground pin of the relay module |
| Motion Sensor (Optional) | GPIO 22 (Pin 15)  | Connect to the output pin of the motion sensor |

#### Relay to Barrier Connection

The relay module acts as a switch to control the barrier. Connect it according to your barrier system's requirements:

1. **Normally Open (NO)** and **Common (COM)** terminals of the relay connect to the barrier control input
2. Ensure the barrier system's voltage and current requirements are compatible with the relay specifications

## Camera Setup

### Enabling the Camera

1. Connect the camera module to the Raspberry Pi's CSI port
2. Enable the camera interface using `raspi-config`:

```bash
sudo raspi-config
```

Navigate to "Interface Options" > "Camera" and select "Yes" to enable the camera.

### Testing the Camera

Test the camera to ensure it's working properly:

```bash
raspistill -o test.jpg
```

This should capture an image and save it as `test.jpg`. Check the image quality and adjust the camera position if needed.

## Barrier Control Setup

### Testing the Relay

Test the relay connection using the GPIO pins:

```bash
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(17, GPIO.OUT); GPIO.output(17, GPIO.HIGH); input('Press Enter to turn off...'); GPIO.output(17, GPIO.LOW); GPIO.cleanup()"
```

This script will turn on the relay connected to GPIO 17. Press Enter to turn it off.

## Network Setup

### Static IP Address (Recommended)

For reliable access to the VisiGate system, configure a static IP address:

1. Edit the DHCP configuration file:

```bash
sudo nano /etc/dhcpcd.conf
```

2. Add the following lines (adjust according to your network):

```
interface eth0  # or wlan0 for Wi-Fi
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

3. Save and reboot:

```bash
sudo reboot
```

## Troubleshooting

### Camera Issues

- **No image captured**: Check the ribbon cable connection and ensure the camera is enabled in `raspi-config`
- **Poor image quality**: Adjust camera position, focus, and lighting conditions
- **Camera not detected**: Run `vcgencmd get_camera` to check if the camera is detected by the system

### Relay/Barrier Issues

- **Relay not activating**: Check GPIO connections and ensure the software is using the correct pin numbers
- **Barrier not responding**: Verify the wiring between the relay and barrier control system
- **Relay clicks but barrier doesn't move**: Check the barrier system's power supply and control mechanism

### Network Issues

- **Can't access the web interface**: Check network connections and firewall settings
- **System not accessible from other devices**: Verify the static IP configuration and network router settings

## Maintenance

### Regular Checks

- Clean the camera lens regularly to ensure clear images
- Check all cable connections for signs of wear or damage
- Ensure the weatherproof enclosure remains sealed and free from moisture
- Monitor the system's temperature, especially during hot weather

### Backup

Regularly backup the VisiGate database and configuration:

```bash
sudo cp /home/pi/VisiGate/data/database.db /home/pi/VisiGate/data/database_backup_$(date +%Y%m%d).db
sudo cp /home/pi/VisiGate/src/config/config.json /home/pi/VisiGate/src/config/config_backup_$(date +%Y%m%d).json
```

Consider automating this process using a cron job.
