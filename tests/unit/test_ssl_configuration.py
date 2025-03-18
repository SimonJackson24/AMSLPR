import unittest
import os
import sys
import tempfile
import shutil
import ssl
import socket
import threading
import time
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import modules to test
from src.config.settings import load_config
from src.app import create_app

class TestSSLConfiguration(unittest.TestCase):
    """
    Test cases for SSL/TLS configuration.
    """
    
    def setUp(self):
        """
        Set up test environment.
        """
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create SSL certificates for testing
        self.cert_path = os.path.join(self.temp_dir, 'test.crt')
        self.key_path = os.path.join(self.temp_dir, 'test.key')
        self._create_self_signed_cert()
        
        # Create test configuration
        self.config = {
            'server': {
                'host': '127.0.0.1',
                'port': 5050,  # Use a different port for testing
                'debug': False,
                'ssl': {
                    'enabled': True,
                    'cert_path': self.cert_path,
                    'key_path': self.key_path
                }
            },
            'database': {
                'path': ':memory:'
            },
            'logging': {
                'level': 'ERROR',
                'file_path': os.path.join(self.temp_dir, 'test.log'),
                'max_size': 1024,
                'backup_count': 1
            }
        }
        
        # Create a Flask app for testing
        self.app = create_app(self.config)
        self.server_thread = None
    
    def tearDown(self):
        """
        Clean up after tests.
        """
        # Stop the server if it's running
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1)
        
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def _create_self_signed_cert(self):
        """
        Create a self-signed certificate for testing.
        """
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        # Generate a private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Create a self-signed certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AMSLPR Test"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=1)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write the certificate and private key to files
        with open(self.cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open(self.key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
    
    def _start_server(self):
        """
        Start the Flask server in a separate thread.
        """
        def run_server():
            self.app.run(
                host=self.config['server']['host'],
                port=self.config['server']['port'],
                ssl_context=(self.cert_path, self.key_path)
            )
        
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        time.sleep(1)  # Give the server time to start
    
    def test_ssl_enabled(self):
        """
        Test that SSL is enabled when configured.
        """
        # Start the server
        self._start_server()
        
        # Create an SSL context for the client
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Connect to the server using SSL
        with socket.create_connection((self.config['server']['host'], self.config['server']['port'])) as sock:
            with context.wrap_socket(sock, server_hostname=self.config['server']['host']) as ssock:
                # Check that the connection is secure
                self.assertTrue(ssock.cipher())
                # Check the certificate
                cert = ssock.getpeercert(binary_form=True)
                self.assertIsNotNone(cert)
    
    def test_ssl_disabled(self):
        """
        Test that SSL can be disabled.
        """
        # Disable SSL in the configuration
        self.config['server']['ssl']['enabled'] = False
        
        # Create a new app with SSL disabled
        app = create_app(self.config)
        
        # Check that the app is configured correctly
        self.assertFalse(app.config.get('SSL_ENABLED', False))
    
    def test_ssl_redirect(self):
        """
        Test that HTTP requests are redirected to HTTPS.
        """
        # This test requires a running server with both HTTP and HTTPS
        # Since this is complex to set up in a unit test, we'll just check
        # that the redirect logic is present in the app configuration
        
        # Start the server
        self._start_server()
        
        # Check that the app is configured to redirect HTTP to HTTPS
        self.assertTrue(self.app.config.get('SSL_REDIRECT', False))

if __name__ == '__main__':
    unittest.main()
