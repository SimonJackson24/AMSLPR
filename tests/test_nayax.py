import unittest
import sys
import os
from unittest.mock import MagicMock, patch
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integration.nayax import NayaxIntegration
from src.database.db_manager import DatabaseManager

class TestNayaxIntegration(unittest.TestCase):
    
    def setUp(self):
        # Mock the database manager
        self.db_manager = MagicMock(spec=DatabaseManager)
        
        # Mock config
        self.config = {
            'nayax': {
                'enabled': True,
                'connection_type': 'serial',
                'serial_port': '/dev/ttyUSB0',
                'baud_rate': 9600,
                'tcp_host': '192.168.1.100',
                'tcp_port': 5000,
                'merchant_id': 'TEST123',
                'terminal_id': 'TERM456'
            }
        }
        
    @patch('src.integration.nayax.serial.Serial')
    def test_init_serial_connection(self, mock_serial):
        # Test initialization with serial connection
        nayax = NayaxIntegration(self.config, self.db_manager)
        
        # Check if serial connection was initialized correctly
        mock_serial.assert_called_once_with(
            port='/dev/ttyUSB0',
            baudrate=9600,
            timeout=5
        )
        
        # Check if connection type was set correctly
        self.assertEqual(nayax.connection_type, 'serial')
        
    @patch('src.integration.nayax.socket.socket')
    def test_init_tcp_connection(self, mock_socket):
        # Change connection type to TCP
        self.config['nayax']['connection_type'] = 'tcp'
        
        # Test initialization with TCP connection
        nayax = NayaxIntegration(self.config, self.db_manager)
        
        # Check if TCP connection was initialized correctly
        mock_socket.return_value.connect.assert_called_once_with(('192.168.1.100', 5000))
        
        # Check if connection type was set correctly
        self.assertEqual(nayax.connection_type, 'tcp')
    
    @patch('src.integration.nayax.serial.Serial')
    def test_request_payment(self, mock_serial):
        # Mock serial connection to return a successful payment response
        mock_serial.return_value.read_until.return_value = b'PAYMENT_COMPLETED:TRANS123:CARD:VISA:1234'
        
        # Initialize Nayax integration
        nayax = NayaxIntegration(self.config, self.db_manager)
        
        # Test request payment
        result = nayax.request_payment(10.50, 1, 'ABC123')
        
        # Check if payment request was sent correctly
        mock_serial.return_value.write.assert_called_once()
        
        # Check if payment result was processed correctly
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['transaction_id'], 'TRANS123')
        self.assertEqual(result['payment_method'], 'CARD')
        
        # Check if payment was recorded in the database
        self.db_manager.record_payment.assert_called_once_with(
            session_id=1,
            amount=10.50,
            payment_method='CARD',
            transaction_id='TRANS123',
            status='completed',
            response_message='VISA:1234'
        )
    
    @patch('src.integration.nayax.serial.Serial')
    def test_payment_failure(self, mock_serial):
        # Mock serial connection to return a failed payment response
        mock_serial.return_value.read_until.return_value = b'PAYMENT_FAILED:DECLINED:Insufficient funds'
        
        # Initialize Nayax integration
        nayax = NayaxIntegration(self.config, self.db_manager)
        
        # Test request payment
        result = nayax.request_payment(10.50, 1, 'ABC123')
        
        # Check if payment result was processed correctly
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], 'DECLINED')
        self.assertEqual(result['message'], 'Insufficient funds')
        
        # Check if payment failure was recorded in the database
        self.db_manager.record_payment.assert_called_once_with(
            session_id=1,
            amount=10.50,
            payment_method=None,
            transaction_id=None,
            status='failed',
            response_message='DECLINED:Insufficient funds'
        )
    
    @patch('src.integration.nayax.serial.Serial')
    def test_get_current_transaction(self, mock_serial):
        # Mock serial connection to return a transaction status
        mock_serial.return_value.read_until.return_value = b'TRANSACTION_STATUS:PROCESSING:Waiting for card'
        
        # Initialize Nayax integration
        nayax = NayaxIntegration(self.config, self.db_manager)
        
        # Set current transaction
        nayax.current_transaction = {
            'session_id': 1,
            'amount': 10.50,
            'plate_number': 'ABC123',
            'status': 'pending',
            'transaction_id': 'TRANS123'
        }
        
        # Test get current transaction
        result = nayax.get_current_transaction()
        
        # Check if status request was sent correctly
        mock_serial.return_value.write.assert_called_once()
        
        # Check if transaction status was processed correctly
        self.assertEqual(result['status'], 'processing')
        self.assertEqual(result['message'], 'Waiting for card')
        self.assertEqual(result['session_id'], 1)
        self.assertEqual(result['amount'], 10.50)
        self.assertEqual(result['plate_number'], 'ABC123')
    
    @patch('src.integration.nayax.serial.Serial')
    def test_cancel_current_transaction(self, mock_serial):
        # Mock serial connection to return a successful cancellation response
        mock_serial.return_value.read_until.return_value = b'TRANSACTION_CANCELLED:SUCCESS'
        
        # Initialize Nayax integration
        nayax = NayaxIntegration(self.config, self.db_manager)
        
        # Set current transaction
        nayax.current_transaction = {
            'session_id': 1,
            'amount': 10.50,
            'plate_number': 'ABC123',
            'status': 'pending',
            'transaction_id': 'TRANS123'
        }
        
        # Test cancel current transaction
        result = nayax.cancel_current_transaction()
        
        # Check if cancel request was sent correctly
        mock_serial.return_value.write.assert_called_once()
        
        # Check if cancellation was successful
        self.assertTrue(result)
        
        # Check if current transaction was cleared
        self.assertIsNone(nayax.current_transaction)
    
    @patch('src.integration.nayax.serial.Serial')
    def test_cleanup(self, mock_serial):
        # Initialize Nayax integration
        nayax = NayaxIntegration(self.config, self.db_manager)
        
        # Test cleanup
        nayax.cleanup()
        
        # Check if connection was closed
        mock_serial.return_value.close.assert_called_once()
    
    @patch('src.integration.nayax.serial.Serial')
    def test_request_payment_with_location(self, mock_serial):
        # Mock serial connection to return a successful payment response
        mock_serial.return_value.read_until.return_value = b'PAYMENT_COMPLETED:TRANS123:CARD:VISA:1234'
        
        # Initialize Nayax integration
        nayax = NayaxIntegration(self.config, self.db_manager)
        
        # Test request payment with payment location parameter
        result = nayax.request_payment(10.50, 1, 'ABC123', 'pay_station')
        
        # Check if payment request was sent correctly with payment location
        mock_serial.return_value.write.assert_called_once()
        write_args = mock_serial.return_value.write.call_args[0][0].decode()
        self.assertIn('pay_station', write_args)
        
        # Check if payment result was processed correctly
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['transaction_id'], 'TRANS123')
        self.assertEqual(result['payment_method'], 'CARD')
        
        # Check if payment was recorded in the database
        self.db_manager.record_payment.assert_called_once_with(
            session_id=1,
            amount=10.50,
            payment_method='CARD',
            transaction_id='TRANS123',
            status='completed',
            response_message='VISA:1234'
        )

if __name__ == '__main__':
    unittest.main()
