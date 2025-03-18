#!/usr/bin/env python3

import argparse
import logging
import sys
import os
import time
import json
from datetime import datetime
import threading

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.settings import load_config

# Import detector with fallback for missing dependencies
try:
    from src.recognition.detector import LicensePlateDetector
    DETECTOR_AVAILABLE = True
    MOCK_DETECTOR = False
except ImportError as e:
    logging.warning(f"Could not import LicensePlateDetector: {e}")
    logging.warning("Using MockLicensePlateDetector instead")
    from src.recognition.mock_detector import MockLicensePlateDetector as LicensePlateDetector
    DETECTOR_AVAILABLE = True
    MOCK_DETECTOR = True

from src.barrier.controller import BarrierController
from src.database.db_manager import DatabaseManager
from src.web.app import create_app
from src.integration.paxton import PaxtonIntegration
from src.integration.nayax import NayaxIntegration

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('data', 'logs', 'amslpr.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AMSLPR')

def recognition_thread(config, db_manager, barrier_controller=None, paxton_integration=None, nayax_integration=None):
    """
    Thread for license plate recognition.
    
    Args:
        config (dict): Configuration dictionary
        db_manager (DatabaseManager): Database manager instance
        barrier_controller (BarrierController, optional): Barrier controller instance
        paxton_integration (PaxtonIntegration, optional): Paxton integration instance
        nayax_integration (NayaxIntegration, optional): Nayax integration instance
    """
    # Load OCR configuration
    ocr_config_path = config['recognition'].get('ocr_config_path', 'config/ocr_config.json')
    try:
        with open(ocr_config_path, 'r') as f:
            ocr_config = json.load(f)
            logger.info(f"Loaded OCR configuration from {ocr_config_path}")
    except Exception as e:
        logger.error(f"Failed to load OCR configuration from {ocr_config_path}: {e}")
        ocr_config = {}
    
    # Initialize plate recognizer
    recognizer = LicensePlateDetector(config['recognition'], ocr_config)
    
    # Get operating mode
    operating_mode = config.get('operating_mode', 'standalone')
    
    logger.info(f"Starting recognition thread in {operating_mode} mode")
    
    # Flag to indicate if OCR config should be reloaded
    reload_ocr_config = False
    last_config_check = time.time()
    config_check_interval = 10  # Check for config changes every 10 seconds
    
    # Main recognition loop
    while True:
        try:
            # Check if we need to reload OCR configuration
            current_time = time.time()
            if current_time - last_config_check > config_check_interval:
                last_config_check = current_time
                
                # Check if reload flag is set
                if reload_ocr_config:
                    logger.info("Reloading OCR configuration...")
                    if recognizer.reload_ocr_config():
                        logger.info("OCR configuration reloaded successfully")
                    else:
                        logger.error("Failed to reload OCR configuration")
                    reload_ocr_config = False
            
            # Capture and process frame
            plate_text = recognizer.process_frame()
            
            # Handle recognized plate
            if plate_text:
                logger.info(f"Detected license plate: {plate_text}")
                
                if operating_mode == 'standalone':
                    # In standalone mode, check our database
                    if db_manager.is_vehicle_authorized(plate_text):
                        logger.info(f"Authorized vehicle: {plate_text}")
                        if barrier_controller:
                            barrier_controller.open_barrier()
                        
                        # Log entry/exit
                        db_manager.log_vehicle_access(plate_text)
                    else:
                        logger.info(f"Unauthorized vehicle: {plate_text}")
                
                elif operating_mode == 'paxton':
                    # In Paxton mode, send all plates to Paxton without checking our database
                    logger.info(f"Sending license plate to Paxton: {plate_text}")
                    if paxton_integration:
                        paxton_integration.process_license_plate(plate_text)
                    else:
                        logger.warning("Paxton integration not available")
                    
                    # Still log the plate detection in our system
                    db_manager.log_vehicle_access(plate_text, authorized=None, notes="Sent to Paxton")
                
                elif operating_mode == 'nayax':
                    # In Nayax mode, handle entry/exit for parking payment system
                    # Get car park operating mode settings
                    entry_exit_mode = config['parking'].get('entry_exit_mode', 'single_camera')
                    payment_required = config['parking'].get('payment_required_for_exit', 'always')
                    
                    if entry_exit_mode == 'single_camera':
                        # Single camera mode - auto-detect entry/exit based on active sessions
                        # Check if there's an active session for this plate
                        active_session = db_manager.get_active_parking_session(plate_text)
                        
                        if active_session:
                            # This is an exit - end the session and calculate fee
                            logger.info(f"Vehicle exiting: {plate_text}")
                            session = db_manager.end_parking_session(plate_text)
                            
                            if session:
                                fee = session.get('calculated_fee', 0.0)
                                
                                # Check if payment is required
                                if payment_required == 'never' or (payment_required == 'grace_period' and fee == 0):
                                    # No payment required - open barrier
                                    logger.info(f"No payment required for {plate_text} (free exit)")
                                    if barrier_controller:
                                        barrier_controller.open_barrier()
                                    
                                    # Log exit
                                    db_manager.log_vehicle_access(plate_text, direction='exit', notes="Free exit")
                                elif fee > 0:
                                    # Request payment via Nayax
                                    logger.info(f"Requesting payment of {fee} for {plate_text}")
                                    
                                    if nayax_integration:
                                        # Get payment location setting
                                        payment_location = config['parking'].get('payment_location', 'exit')
                                        
                                        # Start payment request in a separate thread to avoid blocking
                                        payment_thread = threading.Thread(
                                            target=process_payment,
                                            args=(nayax_integration, fee, session['id'], plate_text, barrier_controller, payment_location)
                                        )
                                        payment_thread.daemon = True
                                        payment_thread.start()
                                    else:
                                        logger.warning("Nayax integration not available")
                                        # If no payment terminal, open barrier anyway
                                        if barrier_controller:
                                            barrier_controller.open_barrier()
                                else:
                                    # No fee (within grace period) - open barrier
                                    logger.info(f"No fee for {plate_text} (within grace period)")
                                    if barrier_controller:
                                        barrier_controller.open_barrier()
                        else:
                            # This is an entry - start a new session
                            logger.info(f"Vehicle entering: {plate_text}")
                            session_id = db_manager.start_parking_session(plate_text)
                            
                            # Open barrier for entry
                            if barrier_controller:
                                barrier_controller.open_barrier()
                            
                            # Log entry
                            db_manager.log_vehicle_access(plate_text, direction='entry', notes="Parking session started")
                    elif entry_exit_mode == 'dual_camera':
                        # Dual camera mode - entry/exit is determined by camera location
                        # This would be configured in a more complex setup with multiple cameras
                        # For now, we'll assume this is an entry camera
                        logger.info(f"Vehicle detected at entry camera: {plate_text}")
                        session_id = db_manager.start_parking_session(plate_text)
                        
                        # Open barrier for entry
                        if barrier_controller:
                            barrier_controller.open_barrier()
                        
                        # Log entry
                        db_manager.log_vehicle_access(plate_text, direction='entry', notes="Parking session started")
            
            # Sleep to control processing rate
            time.sleep(config['recognition']['processing_interval'])
        
        except Exception as e:
            logger.error(f"Error in recognition thread: {e}")
            time.sleep(1)

def process_payment(nayax_integration, amount, session_id, plate_number, barrier_controller, payment_location='exit'):
    """
    Process payment via Nayax terminal.
    
    Args:
        nayax_integration (NayaxIntegration): Nayax integration instance
        amount (float): Amount to charge
        session_id (int): Parking session ID
        plate_number (str): License plate number
        barrier_controller (BarrierController): Barrier controller instance
        payment_location (str): Where payment is processed ('exit' or 'pay_station')
    """
    try:
        # Request payment
        result = nayax_integration.request_payment(amount, session_id, plate_number)
        
        if result['status'] == 'completed':
            logger.info(f"Payment completed for {plate_number}: {amount}")
            # Open barrier if payment is at exit
            if payment_location == 'exit' and barrier_controller:
                barrier_controller.open_barrier()
        else:
            logger.warning(f"Payment failed for {plate_number}: {result['message']}")
    
    except Exception as e:
        logger.error(f"Error processing payment: {e}")

def main():
    """Main entry point for the application."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='AMSLPR - Automated License Plate Recognition System')
    parser.add_argument('--config', help='Path to configuration file')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    logger.info(f"Starting AMSLPR with configuration from {args.config}")
    logger.info(f"Operating mode: {config['operating_mode']}")
    
    # Initialize database manager
    db_manager = DatabaseManager(config['database'])
    
    # Create a default API key if none exists
    try:
        # Check if there are any API keys
        api_keys = db_manager.get_api_keys()
        if not api_keys:
            # Create a default API key
            default_key = db_manager.generate_api_key("Default API Key", permissions="{\"admin\": true}")
            if default_key:
                logger.info(f"Created default API key: {default_key}")
                logger.info("Use this key for API access with header X-API-Key")
    except Exception as e:
        logger.error(f"Error creating default API key: {e}")
    
    # Initialize barrier controller
    try:
        barrier_controller = BarrierController(config['barrier'])
    except Exception as e:
        logging.warning(f"Could not initialize barrier controller: {e}")
        logging.warning("Running without barrier control")
        barrier_controller = None
    
    # Initialize Paxton integration
    paxton_integration = None
    if config.get('paxton', {}).get('enabled', False):
        try:
            paxton_integration = PaxtonIntegration(config['paxton'])
            logger.info("Paxton integration initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Paxton integration: {e}")
            logger.warning("Running without Paxton integration")
    
    # Initialize Nayax integration
    nayax_integration = None
    if config.get('nayax', {}).get('enabled', False):
        try:
            nayax_integration = NayaxIntegration(config['nayax'], db_manager)
            logger.info("Nayax integration initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Nayax integration: {e}")
            logger.warning("Running without Nayax integration")
    
    # Initialize license plate detector
    detector = None
    recognition_thread_obj = None
    if DETECTOR_AVAILABLE:
        try:
            # Load OCR configuration
            ocr_config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'ocr_config.json')
            if os.path.exists(ocr_config_path):
                with open(ocr_config_path, 'r') as f:
                    ocr_config = json.load(f)
            else:
                ocr_config = {}
            
            # Initialize detector
            detector = LicensePlateDetector(config['recognition'], ocr_config)
            
            # Define recognition thread function
            def recognition_thread():
                """Thread for license plate recognition."""
                logging.info("Starting recognition thread")
                
                while True:
                    # Check if detector is available
                    if detector is None:
                        logging.warning("Detector not available. Exiting recognition thread.")
                        break
                    
                    # Check if OCR config reload is requested
                    detector.check_reload_requested()
                    
                    # Sleep for a bit
                    time.sleep(1)
            
            # Start recognition thread
            recognition_thread_obj = threading.Thread(
                target=recognition_thread,
                daemon=True
            )
            recognition_thread_obj.start()
        except Exception as e:
            logging.error(f"Error initializing detector: {e}")
            logging.warning("Running without OCR functionality")
            detector = None
    
    # Create Flask app
    app = create_app(config, db_manager, detector, barrier_controller, paxton_integration, nayax_integration)
    
    # Run Flask app
    ssl_context = None
    if config['web']['ssl']['enabled']:
        ssl_context = (config['web']['ssl']['cert'], config['web']['ssl']['key'])
    
    app.run(
        host=config['web']['host'],
        port=config['web']['port'],
        debug=config['web']['debug'],
        ssl_context=ssl_context
    )

if __name__ == '__main__':
    main()
