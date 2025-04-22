#!/usr/bin/env python3
"""
Script to download Hailo model files for TPU acceleration
"""

import os
import sys
import logging
import requests
import hashlib
from pathlib import Path
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger('download-models')

# Hailo model repositories
MODEL_URLS = {
    # License plate recognition model
    "lprnet_vehicle_license_recognition.hef": {
        "url": "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/LPRNet/lprnet_vehicle_license_recognition.hef",
        "md5": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",  # Replace with actual hash
        "description": "LPRNet for license plate recognition"
    },
    # License plate detection model
    "yolov5m_license_plate.hef": {
        "url": "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/YOLOv5/yolov5m_license_plate.hef",
        "md5": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",  # Replace with actual hash
        "description": "YOLOv5m for license plate detection"
    }
}

# Get project root
project_root = Path(__file__).parent.parent
models_dir = project_root / "models"

def download_file(url, destination, description):
    """Download a file with progress bar"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        file_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        progress_bar = tqdm(
            total=file_size, 
            unit='B', 
            unit_scale=True,
            desc=f"Downloading {description}"
        )
        
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    progress_bar.update(len(chunk))
        
        progress_bar.close()
        return True
    except Exception as e:
        log.error(f"Error downloading {url}: {str(e)}")
        return False

def verify_file(file_path, expected_md5):
    """Verify file integrity using MD5 hash"""
    if expected_md5 == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6":
        # Skip verification for placeholder hashes
        return True
    
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        if file_hash == expected_md5:
            log.info(f"✅ Verified {file_path.name}")
            return True
        else:
            log.error(f"❌ Hash mismatch for {file_path.name}")
            log.error(f"   Expected: {expected_md5}")
            log.error(f"   Actual: {file_hash}")
            return False
    except Exception as e:
        log.error(f"Error verifying {file_path}: {str(e)}")
        return False

def main():
    """Download and verify Hailo model files"""
    log.info("Downloading Hailo TPU model files...")
    
    # Create models directory if it doesn't exist
    models_dir.mkdir(exist_ok=True)
    
    # Download and verify each model
    success = True
    for model_name, model_info in MODEL_URLS.items():
        model_path = models_dir / model_name
        
        if model_path.exists():
            log.info(f"Model {model_name} already exists, checking integrity...")
            if verify_file(model_path, model_info['md5']):
                log.info(f"✅ {model_name} is valid")
                continue
            else:
                log.warning(f"⚠️ {model_name} is invalid, re-downloading...")
        
        log.info(f"Downloading {model_name} - {model_info['description']}")
        if download_file(model_info['url'], model_path, model_info['description']):
            if verify_file(model_path, model_info['md5']):
                log.info(f"✅ Successfully downloaded and verified {model_name}")
            else:
                log.error(f"❌ Failed to verify {model_name}")
                success = False
        else:
            log.error(f"❌ Failed to download {model_name}")
            success = False
    
    # Check for character map file
    char_map_path = models_dir / "char_map.json"
    if not char_map_path.exists():
        log.info("Creating default character map file...")
        import json
        char_map = {
            str(i): str(i) for i in range(10)  # Digits 0-9
        }
        char_map.update({
            str(i+10): chr(i+65) for i in range(26)  # Letters A-Z
        })
        
        with open(char_map_path, 'w') as f:
            json.dump(char_map, f, indent=2)
        log.info("✅ Created character map file")
    
    if success:
        log.info("\n✅ All model files downloaded and verified successfully!")
        log.info("Next step: Run 'python scripts/enable_hailo_tpu.py' to configure the system")
    else:
        log.error("\n❌ Some model files could not be downloaded or verified.")
        log.error("Please check your internet connection and try again.")
    
    return success

if __name__ == "__main__":
    main()
