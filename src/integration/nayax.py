
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import logging
import time
import serial
import socket
import threading
from datetime import datetime

logger = logging.getLogger('AMSLPR.integration.nayax')

class NayaxIntegration:
    """
    Integration with Nayax Onyx payment terminal.
    
    This class provides methods for communicating with Nayax payment terminals
    via serial or TCP/IP connections. It supports payment processing, transaction
    status monitoring, and payment cancellation.
    """
    
    def __init__(self, config, db_manager):
        """
        Initialize Nayax integration.
        
        Args:
            config (dict): Configuration dictionary
            db_manager (DatabaseManager): Database manager instance
        """
        self.config = config
        self.db_manager = db_manager
        self.connection = None
        self.connection_type = None
        self.current_transaction = None
        self.transaction_lock = threading.Lock()
        
        # Get Nayax configuration
        nayax_config = config.get('nayax', {})
        self.enabled = nayax_config.get('enabled', False)
        self.merchant_id = nayax_config.get('merchant_id', '')
        self.terminal_id = nayax_config.get('terminal_id', '')
        
        if not self.enabled:
            logger.warning("Nayax integration is disabled")
            return
        
        # Initialize connection
        connection_type = nayax_config.get('connection_type', 'serial')
        self.connection_type = connection_type
        
        try:
            if connection_type == 'serial':
                # Initialize serial connection
                port = nayax_config.get('serial_port', '/dev/ttyUSB0')
                baud_rate = nayax_config.get('baud_rate', 9600)
                
                logger.info(f"Initializing serial connection to Nayax terminal on {port} at {baud_rate} baud")
                self.connection = serial.Serial(
                    port=port,
                    baudrate=baud_rate,
                    timeout=5
                )
            
            elif connection_type == 'tcp':
                # Initialize TCP connection
                host = nayax_config.get('tcp_host', '192.168.1.100')
                port = nayax_config.get('tcp_port', 5000)
                
                logger.info(f"Initializing TCP connection to Nayax terminal at {host}:{port}")
                self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connection.connect((host, port))
                self.connection.settimeout(5)
            
            else:
                logger.error(f"Unknown connection type: {connection_type}")
                return
            
            logger.info("Nayax integration initialized successfully")
        
        except Exception as e:
            logger.error(f"Error initializing Nayax integration: {e}")
            self.connection = None
    
    def request_payment(self, amount, session_id, plate_number, payment_location='exit'):
        """
        Request payment from Nayax terminal.
        
        Args:
            amount (float): Amount to charge
            session_id (int): Parking session ID
            plate_number (str): License plate number
            payment_location (str): Where payment is processed ('exit' or 'pay_station')
            
        Returns:
            dict: Payment result
        """
        if not self.enabled or not self.connection:
            logger.warning("Nayax integration is disabled or not connected")
            return {
                'status': 'failed',
                'message': 'Nayax integration is disabled or not connected'
            }
        
        with self.transaction_lock:
            # Check if there's already a transaction in progress
            if self.current_transaction and self.current_transaction.get('status') == 'pending':
                logger.warning("Another transaction is already in progress")
                return {
                    'status': 'failed',
                    'message': 'Another transaction is already in progress'
                }
            
            # Create new transaction
            self.current_transaction = {
                'session_id': session_id,
                'amount': amount,
                'plate_number': plate_number,
                'status': 'pending',
                'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        try:
            # Format payment request
            request = f"PAYMENT_REQUEST:{self.merchant_id}:{self.terminal_id}:{amount:.2f}:{session_id}:{plate_number}:{payment_location}\n"
            
            # Send request to terminal
            if self.connection_type == 'serial':
                self.connection.write(request.encode())
                response = self.connection.read_until(b'\n').decode().strip()
            
            elif self.connection_type == 'tcp':
                self.connection.sendall(request.encode())
                response = self.connection.recv(1024).decode().strip()
            
            else:
                logger.error(f"Unknown connection type: {self.connection_type}")
                return {
                    'status': 'failed',
                    'message': f"Unknown connection type: {self.connection_type}"
                }
            
            # Process response
            logger.info(f"Nayax payment response: {response}")
            parts = response.split(':')
            
            if parts[0] == 'PAYMENT_COMPLETED':
                # Payment completed successfully
                transaction_id = parts[1]
                payment_method = parts[2]
                response_message = ':'.join(parts[3:]) if len(parts) > 3 else ''
                
                # Record payment in database
                self.db_manager.record_payment(
                    session_id=session_id,
                    amount=amount,
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    status='completed',
                    response_message=response_message
                )
                
                # Update current transaction
                with self.transaction_lock:
                    self.current_transaction = None
                
                return {
                    'status': 'completed',
                    'transaction_id': transaction_id,
                    'payment_method': payment_method,
                    'message': response_message
                }
            
            elif parts[0] == 'PAYMENT_FAILED':
                # Payment failed
                error_code = parts[1]
                error_message = ':'.join(parts[2:]) if len(parts) > 2 else ''
                
                # Record payment failure in database
                self.db_manager.record_payment(
                    session_id=session_id,
                    amount=amount,
                    payment_method=None,
                    transaction_id=None,
                    status='failed',
                    response_message=f"{error_code}:{error_message}"
                )
                
                # Update current transaction
                with self.transaction_lock:
                    self.current_transaction = None
                
                return {
                    'status': 'failed',
                    'error_code': error_code,
                    'message': error_message
                }
            
            elif parts[0] == 'PAYMENT_PENDING':
                # Payment is being processed
                transaction_id = parts[1]
                status_message = ':'.join(parts[2:]) if len(parts) > 2 else ''
                
                # Update current transaction
                with self.transaction_lock:
                    if self.current_transaction:
                        self.current_transaction['transaction_id'] = transaction_id
                        self.current_transaction['status'] = 'processing'
                        self.current_transaction['message'] = status_message
                
                return {
                    'status': 'pending',
                    'transaction_id': transaction_id,
                    'message': status_message
                }
            
            else:
                # Unknown response
                logger.error(f"Unknown payment response: {response}")
                
                # Record payment error in database
                self.db_manager.record_payment(
                    session_id=session_id,
                    amount=amount,
                    payment_method=None,
                    transaction_id=None,
                    status='error',
                    response_message=f"Unknown response: {response}"
                )
                
                # Update current transaction
                with self.transaction_lock:
                    self.current_transaction = None
                
                return {
                    'status': 'error',
                    'message': f"Unknown response: {response}"
                }
        
        except Exception as e:
            logger.error(f"Error requesting payment: {e}")
            
            # Record payment error in database
            self.db_manager.record_payment(
                session_id=session_id,
                amount=amount,
                payment_method=None,
                transaction_id=None,
                status='error',
                response_message=f"Error: {str(e)}"
            )
            
            # Update current transaction
            with self.transaction_lock:
                self.current_transaction = None
            
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_current_transaction(self):
        """
        Get current transaction status.
        
        Returns:
            dict: Current transaction status
        """
        if not self.enabled or not self.connection:
            logger.warning("Nayax integration is disabled or not connected")
            return {
                'status': 'none',
                'message': 'Nayax integration is disabled or not connected'
            }
        
        with self.transaction_lock:
            if not self.current_transaction:
                return {
                    'status': 'none',
                    'message': 'No active transaction'
                }
            
            transaction = self.current_transaction.copy()
        
        try:
            # Format status request
            transaction_id = transaction.get('transaction_id')
            if not transaction_id:
                return transaction
            
            request = f"TRANSACTION_STATUS:{self.merchant_id}:{self.terminal_id}:{transaction_id}\n"
            
            # Send request to terminal
            if self.connection_type == 'serial':
                self.connection.write(request.encode())
                response = self.connection.read_until(b'\n').decode().strip()
            
            elif self.connection_type == 'tcp':
                self.connection.sendall(request.encode())
                response = self.connection.recv(1024).decode().strip()
            
            else:
                logger.error(f"Unknown connection type: {self.connection_type}")
                return transaction
            
            # Process response
            logger.info(f"Nayax status response: {response}")
            parts = response.split(':')
            
            if parts[0] == 'TRANSACTION_STATUS':
                # Update transaction status
                status = parts[1].lower()
                message = ':'.join(parts[2:]) if len(parts) > 2 else ''
                
                transaction['status'] = status
                transaction['message'] = message
                
                # Update current transaction
                with self.transaction_lock:
                    if self.current_transaction:
                        self.current_transaction['status'] = status
                        self.current_transaction['message'] = message
                
                # If transaction is completed or failed, record it in the database
                if status == 'completed' or status == 'failed':
                    session_id = transaction.get('session_id')
                    amount = transaction.get('amount')
                    
                    if status == 'completed':
                        # Record successful payment
                        self.db_manager.record_payment(
                            session_id=session_id,
                            amount=amount,
                            payment_method='CARD',  # Assuming card payment
                            transaction_id=transaction_id,
                            status='completed',
                            response_message=message
                        )
                    
                    else:
                        # Record failed payment
                        self.db_manager.record_payment(
                            session_id=session_id,
                            amount=amount,
                            payment_method=None,
                            transaction_id=transaction_id,
                            status='failed',
                            response_message=message
                        )
                    
                    # Clear current transaction
                    with self.transaction_lock:
                        self.current_transaction = None
            
            return transaction
        
        except Exception as e:
            logger.error(f"Error getting transaction status: {e}")
            return transaction
    
    def cancel_current_transaction(self):
        """
        Cancel current transaction.
        
        Returns:
            bool: True if transaction was cancelled, False otherwise
        """
        if not self.enabled or not self.connection:
            logger.warning("Nayax integration is disabled or not connected")
            return False
        
        with self.transaction_lock:
            if not self.current_transaction:
                logger.warning("No active transaction to cancel")
                return False
            
            transaction = self.current_transaction.copy()
        
        try:
            # Format cancel request
            transaction_id = transaction.get('transaction_id')
            if not transaction_id:
                # No transaction ID, just clear the current transaction
                with self.transaction_lock:
                    self.current_transaction = None
                return True
            
            request = f"CANCEL_TRANSACTION:{self.merchant_id}:{self.terminal_id}:{transaction_id}\n"
            
            # Send request to terminal
            if self.connection_type == 'serial':
                self.connection.write(request.encode())
                response = self.connection.read_until(b'\n').decode().strip()
            
            elif self.connection_type == 'tcp':
                self.connection.sendall(request.encode())
                response = self.connection.recv(1024).decode().strip()
            
            else:
                logger.error(f"Unknown connection type: {self.connection_type}")
                return False
            
            # Process response
            logger.info(f"Nayax cancel response: {response}")
            parts = response.split(':')
            
            if parts[0] == 'TRANSACTION_CANCELLED':
                # Transaction cancelled successfully
                status = parts[1]
                
                # Record cancellation in database
                session_id = transaction.get('session_id')
                amount = transaction.get('amount')
                
                self.db_manager.record_payment(
                    session_id=session_id,
                    amount=amount,
                    payment_method=None,
                    transaction_id=transaction_id,
                    status='cancelled',
                    response_message=f"Cancelled: {status}"
                )
                
                # Clear current transaction
                with self.transaction_lock:
                    self.current_transaction = None
                
                return True
            
            else:
                # Failed to cancel transaction
                logger.error(f"Failed to cancel transaction: {response}")
                return False
        
        except Exception as e:
            logger.error(f"Error cancelling transaction: {e}")
            return False
    
    def cleanup(self):
        """
        Clean up resources.
        """
        if self.connection:
            try:
                if self.connection_type == 'serial':
                    self.connection.close()
                elif self.connection_type == 'tcp':
                    self.connection.close()
                
                logger.info("Nayax connection closed")
            
            except Exception as e:
                logger.error(f"Error closing Nayax connection: {e}")
            
            self.connection = None
