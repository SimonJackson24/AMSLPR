import os
import logging
import datetime
import cv2
import numpy as np
from pathlib import Path

# Configure logging
logger = logging.getLogger('AMSLPR.utils')

def setup_logging(config):
    """
    Set up logging configuration.
    
    Args:
        config (dict): Configuration dictionary
        
    Returns:
        logging.Logger: Logger instance
    """
    log_level = getattr(logging, config['logging']['level'].upper())
    log_format = config['logging']['format']
    log_file = config['logging']['file']
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('AMSLPR')

def save_image(image, plate_number, directory, prefix=''):
    """
    Save an image to the specified directory.
    
    Args:
        image (numpy.ndarray): Image to save
        plate_number (str): License plate number
        directory (str): Directory to save the image to
        prefix (str, optional): Prefix for the filename
        
    Returns:
        str: Path to the saved image
    """
    # Create directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Generate filename
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{prefix}_{plate_number}_{timestamp}.jpg"
    filepath = os.path.join(directory, filename)
    
    # Save image
    cv2.imwrite(filepath, image)
    logger.debug(f"Saved image to {filepath}")
    
    return filepath

def preprocess_image(image):
    """
    Preprocess an image for license plate detection.
    
    Args:
        image (numpy.ndarray): Image to preprocess
        
    Returns:
        numpy.ndarray: Preprocessed image
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    
    return thresh

def enhance_plate_image(plate_image, config=None):
    """
    Enhance a license plate image for better OCR.
    
    Args:
        plate_image (numpy.ndarray): License plate image
        config (dict, optional): Configuration for enhancement parameters
        
    Returns:
        numpy.ndarray: Enhanced license plate image
    """
    if config is None:
        config = {
            'resize_factor': 2.0,
            'apply_contrast_enhancement': True,
            'apply_noise_reduction': True,
            'apply_perspective_correction': False
        }
    
    # Convert to grayscale if not already
    if len(plate_image.shape) > 2:
        plate_image = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
    
    # Resize image to a larger size for better OCR
    height, width = plate_image.shape[:2]
    resize_factor = config.get('resize_factor', 2.0)
    new_width = int(width * resize_factor)
    new_height = int(height * resize_factor)
    plate_image = cv2.resize(plate_image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    # Apply contrast enhancement
    if config.get('apply_contrast_enhancement', True):
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        plate_image = clahe.apply(plate_image)
    
    # Apply noise reduction
    if config.get('apply_noise_reduction', True):
        # Apply bilateral filter to remove noise while preserving edges
        plate_image = cv2.bilateralFilter(plate_image, 11, 17, 17)
    
    # Apply perspective correction if needed
    if config.get('apply_perspective_correction', False):
        # This would require detecting the four corners of the plate
        # and applying a perspective transform
        pass
    
    # Apply adaptive thresholding for better text extraction
    plate_image = cv2.adaptiveThreshold(
        plate_image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )
    
    # Apply morphological operations to remove small noise
    kernel = np.ones((3, 3), np.uint8)
    plate_image = cv2.morphologyEx(plate_image, cv2.MORPH_OPEN, kernel)
    
    # Ensure the image has the right dimensions for the OCR model
    target_width = config.get('target_width', None)
    target_height = config.get('target_height', None)
    if target_width and target_height:
        plate_image = cv2.resize(plate_image, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
    
    return plate_image

def format_plate_number(text):
    """
    Format a license plate number by removing unwanted characters.
    
    Args:
        text (str): Raw license plate text
        
    Returns:
        str: Formatted license plate number
    """
    # Remove whitespace
    text = text.strip()
    
    # Remove common OCR errors and unwanted characters
    text = ''.join(c for c in text if c.isalnum())
    
    # Convert to uppercase
    text = text.upper()
    
    return text

def get_project_root():
    """
    Get the absolute path to the project root directory.
    
    Returns:
        pathlib.Path: Path to the project root directory
    """
    return Path(__file__).parent.parent.parent

def calculate_parking_duration(entry_time, exit_time):
    """
    Calculate the parking duration between entry and exit times.
    
    Args:
        entry_time (datetime.datetime): Entry time
        exit_time (datetime.datetime): Exit time
        
    Returns:
        datetime.timedelta: Parking duration
    """
    if not entry_time or not exit_time:
        return None
    
    return exit_time - entry_time
