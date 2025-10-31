# Hailo TPU Setup Guide

This document provides instructions for setting up Hailo TPU acceleration with the AMSLPR system.

## Overview

The AMSLPR system supports Hailo TPU acceleration for improved license plate recognition performance. When properly configured, the system will automatically detect and use Hailo hardware acceleration when available.

## Prerequisites

1. **Hardware Requirements**
   - Raspberry Pi 5 with Hailo-8 AI accelerator module
   - Hailo-8 M.2 or H.2.5 AI module
   - Compatible camera (IP/ONVIF)

2. **Software Requirements**
   - Python 3.11 (required for Hailo SDK)
   - AMSLPR application with Hailo support
   - Hailo SDK and model files

## Configuration

### 1. Main Configuration (config/config.json)

The main configuration file should include Hailo TPU settings:

```json
{
    "recognition": {
        "use_hailo_tpu": true,
        "ocr_method": "hybrid",
        "ocr_config_path": "config/ocr_config.json"
    }
}
```

### 2. OCR Configuration (config/ocr_config.json)

The OCR configuration file should include Hailo-specific settings:

```json
{
    "ocr_method": "hybrid",
    "use_hailo_tpu": true,
    "deep_learning": {
        "hailo_ocr_model_path": "models/lprnet_vehicle_license_recognition.hef",
        "hailo_detector_model_path": "models/yolov5m_license_plates.hef",
        "char_map_path": "models/char_map.json"
    }
}
```

## Installation Steps

### 1. Install Hailo SDK

1. Install the Hailo SDK wheel file:
   ```bash
   pip install hailort-4.20.0-cp311-cp311-linux_aarch64.whl
   ```

2. Verify installation:
   ```bash
   python -c "import hailort; print('Hailo SDK version:', hailort.__version__)"
   ```

### 2. Install Model Files

1. Download the required Hailo model files:
   - LPRNet model for license plate recognition
   - YOLOv5 model for license plate detection

2. Place model files in the `models/` directory:
   ```
   models/
   ├── lprnet_vehicle_license_recognition.hef
   ├── yolov5m_license_plates.hef
   └── char_map.json
   ```

### 3. Configure Hardware

1. Connect the Hailo-8 module to your Raspberry Pi:
   - Follow the hardware installation guide
   - Ensure proper power supply

2. Verify device detection:
   ```bash
   ls /dev/hailo*
   ```
`

## Verification

### 1. Check System Status

1. Start the AMSLPR application
2. Check the logs for Hailo TPU detection:
   ```
   grep "Hailo TPU is AVAILABLE" data/logs/amslpr.log
   ```

3. Access the OCR settings page in the web interface
4. Verify that Hailo TPU is detected as available

### 2. Test Recognition Performance

1. Upload test images with license plates
2. Compare recognition results with and without Hailo acceleration
3. Monitor performance metrics in the web interface

## Troubleshooting

### Common Issues

1. **Hailo TPU not detected**
   - Check hardware connections
   - Verify SDK installation
   - Check device permissions

2. **Model loading errors**
   - Verify model file paths
   - Check model file integrity

3. **Performance issues**
   - Try different OCR methods (tesseract, deep learning, hybrid)
   - Adjust confidence thresholds
   - Check camera settings

### Getting Help

For additional support:
1. Check the application logs
2. Review the documentation
3. Contact support with detailed error information

## Performance Optimization

When using Hailo TPU:

1. **Hybrid OCR Mode**: Uses both Hailo TPU and Tesseract for best results
2. **Parallel Processing**: Enable parallel processing for multiple cameras
3. **Frame Skipping**: Configure appropriate frame skipping for high-resolution cameras
4. **Caching**: Enable result caching to avoid redundant processing

## Security Considerations

1. Keep Hailo SDK and model files secure
2. Regularly update to the latest versions
3. Monitor access logs for unauthorized usage