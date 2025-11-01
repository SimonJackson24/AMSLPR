# Pre-packaged Hailo Models

This directory contains pre-packaged Hailo models for license plate recognition with the VisiGate system.

## Included Models

### YOLOv5m License Plates
- Filename: `yolov5m_license_plates.hef`
- Purpose: Primary detector model for license plate detection
- Size: ~38MB

### Tiny YOLOv4 License Plate Detection
- Filename: `tiny_yolov4_license_plate_detection.hef`
- Purpose: Alternative detector model for license plate detection (smaller and faster)
- Size: ~9MB

### LPRNet Vehicle License Recognition
- Filename: `lprnet_vehicle_license_recognition.hef`
- Purpose: OCR model for reading text from license plates
- Size: ~8.2MB

## Automatic Installation

These models will be automatically installed by the `install_on_raspberry_pi.sh` script. No manual intervention is required.

## Model Source

These models are compiled specifically for the Hailo-8L TPU and are sourced from the Hailo Developer Zone and Hailo Model Zoo. They have been included in this package with permission to simplify the installation process.

## License

These models are subject to the Hailo license terms and conditions. They are provided for use with the VisiGate system only.
